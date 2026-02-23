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
        Extract earnings/deductions (verbas) from first and continuation pages

        Returns:
            List of Verba objects
        """
        if not self.paginas:
            return []

        verbas = []

        # Regex pattern: CÓDIGO at start, then DENOMINAÇÃO, then VALOR at end
        # This is more robust than trying to capture intermediate whitespace
        codigo_start_pattern = r'^(\d{2}\.?\d{3})'
        valor_end_pattern = r'([-]?\d+[.,]\d{2})\s*$'

        # Extract from all pages (header on page 1, continuation on subsequent pages)
        for page in self.paginas:
            texto = page.texto
            lines = texto.split('\n')

            # Detect context for natureza detection
            is_atrasado_section = False
            is_reposicao_section = False

            for i, line in enumerate(lines):
                line_upper = line.upper()
                line_stripped = line.strip()

                # Check for section markers
                if 'ATRASADO' in line_upper:
                    is_atrasado_section = True
                    is_reposicao_section = False
                    continue
                elif 'REPOSIÇÃO' in line_upper or 'REPOSICAO' in line_upper:
                    is_reposicao_section = True
                    is_atrasado_section = False
                    continue
                elif 'TOTAL' in line_upper or 'LÍQUIDO' in line_upper:
                    break

                # Skip empty lines and headers
                if not line_stripped or 'CÓDIGO' in line_upper or 'DENOMINAÇÃO' in line_upper:
                    continue

                # Try to extract codigo at start of line
                codigo_match = re.match(codigo_start_pattern, line_stripped)
                if not codigo_match:
                    continue

                # Try to extract valor at end of line
                valor_match = re.search(valor_end_pattern, line_stripped)
                if not valor_match:
                    continue

                # Extract denominacao from middle
                codigo_raw = codigo_match.group(1)
                valor_str = valor_match.group(1)

                # Denominacao is everything between codigo and valor
                codigo_end = codigo_match.end()
                valor_start = valor_match.start()
                denominacao = line_stripped[codigo_end:valor_start].strip()

                try:
                    # Normalize valor (handle both Brazilian 1.000,00 and American 1000.00 formats)
                    # If there's a comma, it's Brazilian format: 1.000,00
                    # If there's only dot and looks like American: 1000.00
                    if ',' in valor_str:
                        # Brazilian format: remove dots (thousands), replace comma with dot
                        valor_normalized = valor_str.replace('.', '').replace(',', '.')
                    elif valor_str.count('.') == 1 and valor_str.endswith(('.00', '.50', '.25', '.75')):
                        # American format (ends with .00, .50, etc.)
                        valor_normalized = valor_str
                    else:
                        # Default: assume Brazilian format
                        valor_normalized = valor_str.replace('.', '').replace(',', '.')

                    valor = float(valor_normalized)

                    # Normalize código
                    from src.core.normalizer import CodigoVerbaNotmalizer
                    codigo = CodigoVerbaNotmalizer.normalize(codigo_raw)

                    # Determine natureza
                    natureza = NaturezaVerba.NORMAL
                    if is_atrasado_section:
                        natureza = NaturezaVerba.ATRASADO
                    elif is_reposicao_section:
                        natureza = NaturezaVerba.REPOSICAO
                    elif 'ATRASADO' in line_upper:
                        natureza = NaturezaVerba.ATRASADO
                    elif 'REPOSIÇÃO' in line_upper or 'REPOSICAO' in line_upper:
                        natureza = NaturezaVerba.REPOSICAO

                    # Create Verba object
                    verba = Verba(
                        codigo=codigo,
                        denominacao=denominacao.strip(),
                        natureza=natureza,
                        quantidade=None,
                        unidade=None,
                        valor=valor,
                        qualificadores_detectados=[],
                    )

                    verbas.append(verba)

                except (ValueError, AttributeError, IndexError):
                    # Skip lines that don't parse correctly
                    continue

        return verbas

    def _extract_totals(self) -> tuple:
        """
        Extract totals (vencimentos, descontos, líquido)

        Returns:
            Tuple of (vencimentos, descontos, liquido)
        """
        if not self.paginas:
            return (0.0, 0.0, 0.0)

        vencimentos = 0.0
        descontos = 0.0
        liquido = 0.0

        # Patterns to find total lines
        # Matches: 5000.00, 5.000,00, 100,00, etc.
        valor_regex = r'[-]?[\d.,]+'
        vencimentos_pattern = rf'(?:TOTAL\s+)?VENCIMENTOS\s+({valor_regex})'
        descontos_pattern = rf'(?:TOTAL\s+)?DESCONTOS\s+({valor_regex})'
        liquido_pattern = rf'(?:LÍQUIDO|LIQUIDO)\s+({valor_regex})'

        # For multipage holerites, totals are usually on the last page
        # Search from last page backwards
        for page in reversed(self.paginas):
            texto = page.texto
            texto_upper = texto.upper()

            # Extract vencimentos
            if vencimentos == 0.0:
                match = re.search(vencimentos_pattern, texto_upper)
                if match:
                    valor_str = match.group(1)
                    vencimentos = self._parse_valor(valor_str)

            # Extract descontos
            if descontos == 0.0:
                match = re.search(descontos_pattern, texto_upper)
                if match:
                    valor_str = match.group(1)
                    descontos = self._parse_valor(valor_str)

            # Extract liquido
            if liquido == 0.0:
                match = re.search(liquido_pattern, texto_upper)
                if match:
                    valor_str = match.group(1)
                    liquido = self._parse_valor(valor_str)

            # If all three found, stop searching
            if vencimentos > 0 and descontos >= 0 and liquido > 0:
                break

        return (vencimentos, descontos, liquido)

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

    def _parse_valor(self, valor_str: str) -> float:
        """
        Parse monetary value handling both Brazilian and American formats

        Args:
            valor_str: Value string in format like "5000.00", "5.000,00", or ".50"

        Returns:
            Float value
        """
        if not valor_str:
            return 0.0

        valor_str = valor_str.strip()

        try:
            # Determine format and parse accordingly
            if ',' in valor_str:
                # Brazilian format: 1.000,00
                valor_normalized = valor_str.replace('.', '').replace(',', '.')
            elif valor_str.count('.') == 1 and any(valor_str.endswith(x) for x in ['.00', '.50', '.25', '.75']):
                # American format: 1000.00
                valor_normalized = valor_str
            else:
                # Default: assume Brazilian format
                valor_normalized = valor_str.replace('.', '').replace(',', '.')

            return float(valor_normalized)
        except (ValueError, AttributeError):
            return 0.0

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
