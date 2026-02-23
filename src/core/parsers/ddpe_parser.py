"""
DDPE-specific holerite parser (Departamento de Despesa)
"""

import re
from typing import List, Optional
from src.core.parsers.base_parser import BaseParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import (
    Holerite,
    CabecalhoHolerite,
    Verba,
    NaturezaVerba,
    TipoFolha,
    TemplateType,
)


class DDPEParser(BaseParser):
    """
    Parser for DDPE (Departamento de Despesa) holerite template

    Handles extraction of:
    - Header: CPF, Name, Cargo, Unidade, Competência, Tipo de Folha, Data de Pagamento
    - Earnings: Verbas with código, denominação, natureza, quantidade, valor
    - Totals: Vencimentos, Descontos, Líquido
    """

    # Regex patterns for DDPE template detection
    DDPE_KEYWORDS = [
        r"DEPARTAMENTO\s+DE\s+DESPESA",
        r"DDPE",
        r"SECRETARIA\s+DE\s+ESTADO",
    ]

    # Regex patterns for header extraction
    PATTERNS = {
        "cpf": r"CPF[:\s]+(\d{3}\.\d{3}\.\d{3}-\d{2})",
        "nome": r"(?:NOME|NAME)[:\s]+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)(?:\n|$)",
        "cargo": r"CARGO[:\s]+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s\d\/\-]+?)(?:\n|$)",
        "unidade": r"UNIDADE[:\s]+([A-ZÁÉÍÓÚÂÃÕÊÔ0-9\w\s\/\-]+?)(?:\n|$)",
        "competencia": r"(?:COMPETÊNCIA|COMPETENCIA)[:\s]+(\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2})",
        "data_pagamento": r"(?:DATA\s+DE\s+PAGAMENTO|DATA\s+PAGTO)[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})",
    }

    def __init__(self):
        """Initialize DDPE parser"""
        super().__init__()
        self.extracted_cabecalho: Optional[CabecalhoHolerite] = None

    def detect_template(self, texto: str) -> bool:
        """
        Detect if text belongs to DDPE template

        Args:
            texto: Extracted text from page

        Returns:
            True if DDPE template detected, False otherwise
        """
        texto_upper = texto.upper()

        # Check for DDPE keywords
        for pattern in self.DDPE_KEYWORDS:
            if re.search(pattern, texto_upper, re.IGNORECASE):
                return True

        return False

    def parse(self, paginas: List[PaginaExtraida]) -> Holerite:
        """
        Parse DDPE holerite pages

        Args:
            paginas: List of extracted pages

        Returns:
            Holerite object with extracted data
        """
        self.paginas = paginas

        # Extract from all pages
        cabecalho = self._extract_cabecalho()
        verbas = self._extract_verbas()
        vencimentos, descontos, liquido = self._extract_totals()

        # Create holerite
        holerite = Holerite(
            cabecalho=cabecalho,
            verbas=verbas,
            total_vencimentos=vencimentos,
            total_descontos=descontos,
            liquido=liquido,
            pagina_numero=paginas[0].numero if paginas else 0,
            metodo_extracao=paginas[0].metodo if paginas else "TEXTO",
            confianca=paginas[0].confianca if paginas else 0.95,
        )

        # Validate extracted data
        self._validate_holerite(holerite)
        self.holerite = holerite

        return holerite

    def _extract_cabecalho(self) -> CabecalhoHolerite:
        """
        Extract header information from first page

        Returns:
            CabecalhoHolerite object
        """
        if not self.paginas:
            raise ValueError("No pages provided")

        texto = self.get_first_page_text()

        # Extract CPF
        cpf = self._extract_field(texto, "cpf")
        if not cpf:
            raise ValueError("CPF not found in holerite")

        # Extract Name
        nome = self._extract_field(texto, "nome")
        if not nome:
            raise ValueError("Nome not found in holerite")

        # Extract optional fields
        cargo = self._extract_field(texto, "cargo")
        unidade = self._extract_field(texto, "unidade")
        competencia = self._extract_field(texto, "competencia")
        data_pagamento = self._extract_field(texto, "data_pagamento")

        # Normalize competencia format (AAAA-MM)
        if competencia:
            competencia = self._normalize_date(competencia, "AAAA-MM")

        # Determine Tipo de Folha
        tipo_folha = self._extract_tipo_folha(texto)

        # Create header object
        cabecalho = CabecalhoHolerite(
            nome=nome.strip(),
            cpf=cpf.strip(),
            cargo=cargo.strip() if cargo else None,
            unidade=unidade.strip() if unidade else None,
            competencia=competencia or "",
            tipo_folha=tipo_folha,
            data_pagamento=data_pagamento.strip() if data_pagamento else None,
            template_type=TemplateType.DDPE,
        )

        self.extracted_cabecalho = cabecalho
        return cabecalho

    def _extract_verbas(self) -> List[Verba]:
        """
        Extract earnings/deductions (verbas)

        Returns:
            List of Verba objects
        """
        # TODO: Implemented in Task 3
        return []

    def _extract_totals(self) -> tuple:
        """
        Extract totals (vencimentos, descontos, líquido)

        Returns:
            Tuple of (vencimentos, descontos, liquido)
        """
        # TODO: Implemented in Task 4
        return (0.0, 0.0, 0.0)

    def _extract_field(self, texto: str, field_name: str) -> Optional[str]:
        """
        Extract a field using regex pattern

        Args:
            texto: Text to search in
            field_name: Name of field to extract

        Returns:
            Extracted field value or None
        """
        if field_name not in self.PATTERNS:
            return None

        pattern = self.PATTERNS[field_name]
        match = re.search(pattern, texto, re.IGNORECASE | re.MULTILINE)

        if match:
            return match.group(1)

        return None

    def _normalize_date(self, date_str: str, target_format: str) -> str:
        """
        Normalize date format

        Args:
            date_str: Date string (various formats)
            target_format: Target format (AAAA-MM or DD/MM/YYYY)

        Returns:
            Normalized date string
        """
        # Replace common separators
        date_clean = date_str.replace("/", "-").replace(".", "-").strip()

        # Handle MM-AAAA or AAAA-MM formats
        if target_format == "AAAA-MM":
            # Check if format is MM-AAAA
            if re.match(r"^\d{2}-\d{4}$", date_clean):
                parts = date_clean.split("-")
                return f"{parts[1]}-{parts[0]}"
            # Already AAAA-MM
            elif re.match(r"^\d{4}-\d{2}$", date_clean):
                return date_clean

        return date_clean

    def _extract_tipo_folha(self, texto: str) -> TipoFolha:
        """
        Determine tipo de folha from text

        Args:
            texto: Text to search in

        Returns:
            TipoFolha enum value
        """
        texto_upper = texto.upper()

        if "DÉCIMO" in texto_upper or "13O" in texto_upper or "13º" in texto_upper:
            return TipoFolha.DECIMO_TERCEIRO
        elif "SUPLEMENTAR" in texto_upper:
            return TipoFolha.SUPLEMENTAR
        else:
            return TipoFolha.NORMAL
