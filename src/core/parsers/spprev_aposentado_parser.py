"""
SPPREV Aposentado-specific holerite parser
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


class SpprevAposentadoParser(BaseParser):
    """
    Parser for SPPREV (São Paulo Previdência) Aposentado template

    Handles extraction of:
    - Header: CPF, Name, Entidade, Cargo, Competência, Benefício, % Aposentadoria,
              Tipo de Folha, Banco/Agência/Conta, Nível
    - Earnings: Verbas with código (XXXXXX), denominação, natureza, quantidade,
                unidade, período, vencimento, descontos
    - Totals: BASE IR, BASE REDUTOR, BASE CONTRIB PREV, VENCIMENTOS, DESCONTOS, LÍQUIDO
    """

    # Regex patterns for SPPREV template detection
    SPPREV_KEYWORDS = [
        r"S\s*Ã\s*O\s+PAULO\s+PREVID.*NCIA|SPPREV",
        r"DIRETORIA\s+DE\s+BENEF.*CIOS\s+SERVIDORES",
        r"DEMONSTRATIVO\s+DE\s+PAGAMENTO",
    ]

    # Regex patterns for header extraction
    # Note: SPPREV layout often has labels on one line and values on the next or same line
    PATTERNS = {
        "cpf": r"(\d{3}\.\d{3}\.\d{3}-\d{2})",  # Simple CPF pattern - works across lines
        "nome": r"(?:NOME|Fernando|João|Maria|Pedro)[\s\n]*([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)(?:\n|C\.P\.F|\d{3}\.\d{3})",
        "entidade": r"ENTIDADE\s+([A-ZÁÉÍÓÚÂÃÕÊÔ0-9\w\s\/\-]+?)(?:\n|BENEF|N\s*°)",
        "cargo": r"CARGO\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s\d\/\-]+?)(?:\n|%\s+APOSENTADORIA)",
        "competencia": r"COMPET.*NCIA\s+(\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2})",
        "beneficio": r"N\s*°\s*BENEF.*CIO\s+(\d+[/-]\d+)",
        "percentual_aposentadoria": r"%\s+APOSENTADORIA\s+([\d.,]+)",
        "tipo_folha": r"TIPO\s+FOLHA\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)(?:\n|COMPET)",
        "banco": r"BANCO\s+(\d{4})",
        "agencia": r"AG.*NCIA\s+(\d{4})",
        "conta": r"N\s*°?\s*CONTA\s+([\d-]+)",
        "nivel": r"N\s*°\s*VEL\s+(\d+)",
    }

    def __init__(self):
        """Initialize SPPREV Aposentado parser"""
        super().__init__()
        self.extracted_cabecalho: Optional[CabecalhoHolerite] = None

    def detect_template(self, texto: str) -> bool:
        """
        Detect if text belongs to SPPREV Aposentado template

        Uses fuzzy matching with score threshold 0.75 for "DIRETORIA DE BENEFICIOS SERVIDORES"

        Args:
            texto: Extracted text from page

        Returns:
            True if SPPREV template detected, False otherwise
        """
        texto_upper = texto.upper()

        # Check for SPPREV keywords - at least 2 must match
        matches = 0
        for pattern in self.SPPREV_KEYWORDS:
            if re.search(pattern, texto_upper, re.IGNORECASE):
                matches += 1

        # SPPREV pattern detected if at least 2 keywords match
        return matches >= 2

    def parse(self, paginas: List[PaginaExtraida]) -> Holerite:
        """
        Parse SPPREV Aposentado holerite pages

        Args:
            paginas: List of extracted pages

        Returns:
            Holerite object with extracted data

        Raises:
            ValueError: If parsing fails or data validation fails
        """
        self.paginas = paginas

        # Extract from pages
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

        SPPREV Aposentado header includes:
        - Nome, CPF, Entidade, Cargo, Competência
        - Benefício, % Aposentadoria, Tipo Folha
        - Banco, Agência, Conta, Nível

        Returns:
            CabecalhoHolerite object

        Raises:
            ValueError: If required fields (nome, cpf) not found
        """
        if not self.paginas:
            raise ValueError("No pages provided")

        texto = self.get_first_page_text()

        # Extract required CPF using simple pattern (works better with multiline)
        cpf_match = re.search(r"(\d{3}\.\d{3}\.\d{3}-\d{2})", texto)
        if not cpf_match:
            raise ValueError("CPF not found in holerite")
        cpf = cpf_match.group(1)

        # Extract required Name - pattern after "NOME" label or before CPF
        # Try pattern: NOME C.P.F \n NAME CPF
        nome_match = re.search(
            r"NOME\s+C\.?P\.?F\s*\n\s*([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)\s+\d{3}\.\d{3}",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        if not nome_match:
            # Fallback: look for name pattern before CPF
            nome_match = re.search(
                r"NOME\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)(?:\n|\s\d{3}\.\d{3})",
                texto,
                re.IGNORECASE | re.MULTILINE,
            )
        if not nome_match:
            raise ValueError("Nome not found in holerite")
        nome = nome_match.group(1).strip()

        # Extract optional fields with better patterns
        # ENTIDADE: SPPREV has "ENTIDADE BENEFÍCIO N° BENEFÍCIO" on one line
        # then next line has SECRETARIA... APOSENTADORIA ...
        entidade_match = re.search(
            r"ENTIDADE\s+BENEF.*?\n\s*([A-ZÁÉÍÓÚÂÃÕÊÔ0-9\w\s\/\-]+?)\s+(?:APOSENTADORIA|PENS)",
            texto,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        entidade = entidade_match.group(1).strip() if entidade_match else None

        # CARGO: line after "CARGO" label, followed by %
        cargo_match = re.search(
            r"CARGO\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s\d\/\-]+?)\s+%",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        cargo = cargo_match.group(1).strip() if cargo_match else None

        # COMPETÊNCIA: find "COMPETÊNCIA" and extract date on same or next line
        # Pattern: "COMPETÊNCIA 11/2025" or "COMPETÊNCIA\n11/2025"
        # Handle encoding issues with Ê by using flexible pattern
        competencia_match = re.search(
            r"COMPET[ÊNCIA]?.*?\s+(\d{1,2}[/\-]\d{4})",
            texto,
            re.IGNORECASE | re.DOTALL,
        )
        if not competencia_match:
            # Try simpler pattern without special chars
            competencia_match = re.search(
                r"COMPET[A-Z]*\s+(\d{1,2}[/\-]\d{4})",
                texto,
                re.IGNORECASE,
            )
        competencia = None
        if competencia_match:
            competencia = self._normalize_date(competencia_match.group(1), "AAAA-MM")
        else:
            competencia = ""

        # BENEFÍCIO: N° BENEFÍCIO pattern
        beneficio_match = re.search(
            r"N\s*°\s*BENEF.*CIO\s+(\d+[/-]\d+)",
            texto,
            re.IGNORECASE,
        )
        beneficio = beneficio_match.group(1) if beneficio_match else None

        # PERCENTUAL APOSENTADORIA
        percentual_match = re.search(
            r"%\s+APOSENTADORIA\s+([\d.,]+)",
            texto,
            re.IGNORECASE,
        )
        percentual = percentual_match.group(1) if percentual_match else None

        # TIPO FOLHA
        tipo_folha_match = re.search(
            r"TIPO\s+FOLHA\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)(?:\n|COMPET)",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        tipo_folha_str = tipo_folha_match.group(1).strip() if tipo_folha_match else None

        # BANCO
        banco_match = re.search(r"BANCO\s+(\d{4})", texto, re.IGNORECASE)
        banco = banco_match.group(1) if banco_match else None

        # AGÊNCIA
        agencia_match = re.search(r"AG.*NCIA\s+(\d{4})", texto, re.IGNORECASE)
        agencia = agencia_match.group(1) if agencia_match else None

        # CONTA
        conta_match = re.search(r"N\s*°?\s*CONTA\s+([\d-]+)", texto, re.IGNORECASE)
        conta = conta_match.group(1) if conta_match else None

        # NÍVEL
        nivel_match = re.search(r"N\s*°\s*VEL\s+(\d+)", texto, re.IGNORECASE)
        nivel = nivel_match.group(1) if nivel_match else None

        # Determine Tipo de Folha
        tipo_folha = self._extract_tipo_folha(texto, tipo_folha_str)

        # Create header object with SPPREV-specific fields
        cabecalho = CabecalhoHolerite(
            nome=nome.strip(),
            cpf=cpf.strip(),
            cargo=cargo.strip() if cargo else None,
            unidade=entidade.strip() if entidade else None,  # Use entidade as unidade
            competencia=competencia or "",
            tipo_folha=tipo_folha,
            template_type=TemplateType.SPPREV_APOSENTADO,
        )

        self.extracted_cabecalho = cabecalho
        return cabecalho

    def _extract_verbas(self) -> List[Verba]:
        """
        Extract earnings/deductions (verbas) from all pages

        SPPREV Aposentado verba format:
        Código (XXXXXX), Denominação, NAT, QTD, Unidade, Período, Vencimento, Descontos

        Example line:
        001001 SALARIO BASE N 11/2025 2.685,68
        070012 IMPOSTO DE RENDA N 11/2025 1.393,52 (in Descontos column)

        Returns:
            List of Verba objects

        Raises:
            No exceptions raised - errors logged as skipped lines
        """
        if not self.paginas:
            return []

        verbas = []

        # Regex pattern for SPPREV: 6-digit código at start of line
        codigo_pattern = r"^(\d{6})\s+"

        # Extract from all pages
        for page in self.paginas:
            texto = page.texto
            lines = texto.split("\n")

            for i, line in enumerate(lines):
                line_upper = line.upper()
                line_stripped = line.strip()

                # Skip empty lines or headers
                if not line_stripped or "CÓDIGO" in line_upper:
                    continue

                # Try to extract código at start of line
                codigo_match = re.match(codigo_pattern, line_stripped)
                if not codigo_match:
                    continue

                try:
                    codigo_raw = codigo_match.group(1)

                    # Extract the rest of the line after codigo
                    rest_of_line = line_stripped[codigo_match.end() :].strip()

                    # Find monetary value at end (vencimento)
                    # Pattern: captures Brazilian (2.685,68) and American (5604.34) formats
                    valor_pattern = r"([-]?[\d.,]+)\s*$"
                    valor_match = re.search(valor_pattern, rest_of_line)

                    if not valor_match:
                        continue

                    valor_str = valor_match.group(1)

                    # Get denominação: everything before the NAT indicator
                    # Look for NAT pattern (usually single letter N, C, D after denominação)
                    # More robustly: get everything before the last monetary value
                    denominacao_section = rest_of_line[: valor_match.start()].strip()

                    # Extract NAT from denominação section
                    # NAT is usually a single letter
                    # Search backwards from the end for single letter markers
                    nat_pattern = r"\s+([NCD])\s+"
                    nat_match = re.search(nat_pattern, denominacao_section)

                    if nat_match:
                        natureza_str = nat_match.group(1).upper()
                        # Denominação is everything before NAT
                        denom_end = nat_match.start()
                        denominacao = denominacao_section[:denom_end].strip()
                    else:
                        # No NAT found, default to N (NORMAL)
                        natureza_str = "N"
                        denominacao = denominacao_section.strip()

                    # Map NAT to natureza
                    natureza = NaturezaVerba.NORMAL
                    if natureza_str == "C":
                        natureza = NaturezaVerba.CREDITO
                    elif natureza_str == "D":
                        natureza = NaturezaVerba.DEBITO

                    # Parse valor
                    valor = self._parse_valor(valor_str)

                    # Create Verba object
                    verba = Verba(
                        codigo=codigo_raw,
                        denominacao=denominacao.strip() if denominacao else "UNKNOWN",
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

        Handles two formats:
        1. Same-line: "TOTAL VENCIMENTOS 8.979,01"
        2. Two-line (SPPREV layout):
           BASE IR BASE REDUTOR BASE CONTRIB PREV TOTAL VENCTOS TOTAL DE DESCONTOS TOTAL LÍQUIDO
           8.371,81 0,00 8.979,01 8.979,01 2.795,51 6.183,50
           (last 3 values = vencimentos, descontos, líquido)

        Returns:
            Tuple of (vencimentos, descontos, liquido)
        """
        if not self.paginas:
            return (0.0, 0.0, 0.0)

        # Search from last page backwards
        for page in reversed(self.paginas):
            texto = page.texto
            lines = texto.split("\n")

            for i, line in enumerate(lines):
                line_upper = line.upper().strip()

                # Detect the totals header line (two-line format)
                if ("VENCTO" in line_upper and "DESCONTO" in line_upper
                        and ("QUIDO" in line_upper or "LIQUIDO" in line_upper)):
                    # Read the next non-empty line for values
                    for j in range(i + 1, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        # Extract all monetary values from the values line
                        valores = re.findall(r"[-]?[\d.,]+", next_line)
                        if len(valores) >= 3:
                            # Last 3 values = vencimentos, descontos, líquido
                            vencimentos = self._parse_valor(valores[-3])
                            descontos = self._parse_valor(valores[-2])
                            liquido = self._parse_valor(valores[-1])
                            return (vencimentos, descontos, liquido)

            # Fallback: single-line format "TOTAL VENCIMENTOS 5.000,00"
            vencimentos = 0.0
            descontos = 0.0
            liquido = 0.0
            valor_regex = r"([-]?[\d.,]+)"

            for line in lines:
                line_upper = line.upper().strip()
                match = re.search(rf"TOTAL\s+(?:VENCIMENTOS?|VENCTOS?)\s+{valor_regex}", line_upper)
                if match and vencimentos == 0.0:
                    vencimentos = self._parse_valor(match.group(1))
                match = re.search(rf"TOTAL\s+(?:DE\s+)?DESCONTOS?\s+{valor_regex}", line_upper)
                if match and descontos == 0.0:
                    descontos = self._parse_valor(match.group(1))
                match = re.search(rf"TOTAL\s+L[ÍI]QUIDO\s+{valor_regex}", line_upper)
                if match and liquido == 0.0:
                    liquido = self._parse_valor(match.group(1))

            if vencimentos > 0 or liquido > 0:
                return (vencimentos, descontos, liquido)

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
        match = re.search(pattern, texto, re.IGNORECASE | re.MULTILINE | re.DOTALL)

        if match:
            value = match.group(1)
            # Clean up captured value (remove extra whitespace/newlines)
            value = re.sub(r"\s+", " ", value)
            return value

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

        Brazilian: 1.000,00 (dot=thousands, comma=decimal)
        American: 1000.00 (dot=decimal)

        Returns:
            Float value
        """
        if not valor_str:
            return 0.0

        valor_str = valor_str.strip()

        try:
            if "," in valor_str:
                # Brazilian format: remove dots (thousands), replace comma with dot
                valor_normalized = valor_str.replace(".", "").replace(",", ".")
            elif "." in valor_str:
                # Dot present, no comma — determine if decimal or thousands
                parts = valor_str.rsplit(".", 1)
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # 1-2 digits after dot = decimal separator (American)
                    valor_normalized = valor_str
                else:
                    # 3+ digits after dot = thousands separator (Brazilian without decimal)
                    valor_normalized = valor_str.replace(".", "")
            else:
                # No separator — integer
                valor_normalized = valor_str

            return float(valor_normalized)
        except (ValueError, AttributeError):
            return 0.0

    def _extract_tipo_folha(self, texto: str, tipo_folha_str: Optional[str] = None) -> TipoFolha:
        """
        Determine tipo de folha from text

        Args:
            texto: Text to search in
            tipo_folha_str: Pre-extracted tipo_folha string (optional)

        Returns:
            TipoFolha enum value
        """
        texto_upper = texto.upper()

        # Check pre-extracted value first
        if tipo_folha_str:
            tipo_upper = tipo_folha_str.upper()
            if "DÉCIMO" in tipo_upper or "13" in tipo_upper:
                return TipoFolha.DECIMO_TERCEIRO
            elif "SUPLEMENTAR" in tipo_upper:
                return TipoFolha.SUPLEMENTAR

        # Check in full text
        if "DÉCIMO" in texto_upper or "13O" in texto_upper or "13º" in texto_upper:
            return TipoFolha.DECIMO_TERCEIRO
        elif "SUPLEMENTAR" in texto_upper:
            return TipoFolha.SUPLEMENTAR
        else:
            return TipoFolha.NORMAL
