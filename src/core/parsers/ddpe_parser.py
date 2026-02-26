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

    # Valid DDPE units
    VALID_UNITS = {"PERC.", "VALOR", "DIAS", "QTDE", "AULAS", "HORAS"}

    # NAT letter to NaturezaVerba mapping
    NAT_MAP = {
        "N": NaturezaVerba.NORMAL,
        "A": NaturezaVerba.ATRASADO,
        "R": NaturezaVerba.REPOSICAO,
        "D": NaturezaVerba.DEVOLUCAO,
        "E": NaturezaVerba.ESTORNO,
    }

    def _extract_verbas(self) -> List[Verba]:
        """
        Extract earnings/deductions (verbas) from all pages.

        DDPE full format:
        12.015  ADIC.LOCAL EXERC.CAR.POL/DELEG.  A  PERC.  01/09/2007 A 30/09/2007  329,65+
        70.006  IAMSPE                            A  2,00  PERC.  01/09/2007 A 30/09/2007  6,59-
        01.001  SALÁRIO                           N         01/02/2026 A 28/02/2026  5.000,00+

        Also supports simplified format (legacy mocks):
        01.001  SALÁRIO  5.000,00

        Returns:
            List of Verba objects
        """
        if not self.paginas:
            return []

        verbas = []
        from src.core.normalizer import CodigoVerbaNormalizer

        # Full DDPE line pattern:
        # CODIGO  DENOM  [NAT]  [QTD]  [UNID]  [PERIODO]  VALOR[+/-]
        # Simplified fallback: CODIGO  DENOM  VALOR
        codigo_start = re.compile(r'^(\d{2}\.?\d{3})\s+')
        # Value at end with optional +/- sign
        valor_end_full = re.compile(r'([-]?\d[\d.,]*\d)\s*([+\-])\s*$')
        valor_end_simple = re.compile(r'([-]?\d[\d.,]*\d)\s*$')

        # Detect context for fallback natureza (section-based)
        is_atrasado_section = False
        is_reposicao_section = False

        for page in self.paginas:
            lines = page.texto.split('\n')

            for line in lines:
                line_upper = line.upper()
                line_stripped = line.strip()

                # Section markers (fallback for simplified format)
                if 'ATRASADO' in line_upper and not re.match(r'^\d{2}\.?\d{3}', line_stripped):
                    is_atrasado_section = True
                    is_reposicao_section = False
                    continue
                elif ('REPOSIÇÃO' in line_upper or 'REPOSICAO' in line_upper) and not re.match(r'^\d{2}\.?\d{3}', line_stripped):
                    is_reposicao_section = True
                    is_atrasado_section = False
                    continue
                elif 'TOTAL' in line_upper or 'LÍQUIDO' in line_upper:
                    break

                if not line_stripped or 'CÓDIGO' in line_upper or 'DENOMINAÇÃO' in line_upper:
                    continue

                codigo_match = codigo_start.match(line_stripped)
                if not codigo_match:
                    continue

                try:
                    codigo_raw = codigo_match.group(1)
                    rest = line_stripped[codigo_match.end():]

                    # Try full format first: value with +/- sign at end
                    valor_match = valor_end_full.search(rest)
                    if valor_match:
                        valor_str = valor_match.group(1)
                        sinal = valor_match.group(2)
                        valor = self._parse_valor(valor_str)
                        if sinal == '-':
                            valor = -abs(valor)
                        else:
                            valor = abs(valor)
                        middle = rest[:valor_match.start()].strip()
                        parsed = self._parse_ddpe_middle(middle)
                    else:
                        # Simplified format: no +/- sign
                        valor_match = valor_end_simple.search(rest)
                        if not valor_match:
                            continue
                        valor_str = valor_match.group(1)
                        valor = self._parse_valor(valor_str)
                        middle = rest[:valor_match.start()].strip()
                        parsed = self._parse_ddpe_middle(middle)

                    # Determine natureza: prefer NAT column, fallback to section
                    if parsed['nat']:
                        natureza = self.NAT_MAP.get(parsed['nat'], NaturezaVerba.NORMAL)
                    elif is_atrasado_section:
                        natureza = NaturezaVerba.ATRASADO
                    elif is_reposicao_section:
                        natureza = NaturezaVerba.REPOSICAO
                    else:
                        natureza = NaturezaVerba.NORMAL

                    # Parse periodo
                    periodo_inicio, periodo_fim = None, None
                    if parsed['periodo']:
                        periodo_inicio, periodo_fim = self._normalize_periodo_range(parsed['periodo'])

                    codigo = CodigoVerbaNormalizer.normalize(codigo_raw)

                    verba = Verba(
                        codigo=codigo,
                        denominacao=parsed['denominacao'].strip() or "UNKNOWN",
                        natureza=natureza,
                        quantidade=parsed['quantidade'],
                        unidade=parsed['unidade'],
                        periodo_inicio=periodo_inicio,
                        periodo_fim=periodo_fim,
                        valor=valor,
                        qualificadores_detectados=[],
                    )
                    verbas.append(verba)

                except (ValueError, AttributeError, IndexError):
                    continue

        return verbas

    def _parse_ddpe_middle(self, middle: str) -> dict:
        """
        Parse the middle section of a DDPE verba line (between codigo and valor).

        Expected order: DENOMINACAO [NAT] [QTD] [UNIDADE] [PERIODO]

        Returns dict with keys: denominacao, nat, quantidade, unidade, periodo
        """
        result = {
            'denominacao': middle,
            'nat': None,
            'quantidade': None,
            'unidade': None,
            'periodo': None,
        }

        if not middle:
            return result

        # Extract periodo range at end: DD/MM/YYYY A DD/MM/YYYY or MM/YYYY
        periodo_match = re.search(
            r'(\d{2}/\d{2}/\d{4}\s+[Aa]\s+\d{2}/\d{2}/\d{4}|\d{1,2}/\d{4}|\d{4})\s*$',
            middle
        )
        if periodo_match:
            result['periodo'] = periodo_match.group(1).strip()
            middle = middle[:periodo_match.start()].strip()

        # Extract unidade (PERC., VALOR, DIAS, QTDE, AULAS, HORAS)
        for unit in self.VALID_UNITS:
            unit_pattern = re.escape(unit)
            unit_match = re.search(rf'\b{unit_pattern}\b', middle, re.IGNORECASE)
            if unit_match:
                result['unidade'] = unit.upper()
                middle = (middle[:unit_match.start()] + middle[unit_match.end():]).strip()
                break

        # Extract NAT letter (single letter N/A/R/D/E surrounded by spaces or at boundary)
        # Must be after denominacao text — search from end toward start
        tokens = middle.split()
        if len(tokens) >= 2:
            # Check if last token is a NAT letter
            last = tokens[-1].upper()
            if last in self.NAT_MAP and len(tokens[-1]) == 1:
                result['nat'] = last
                tokens = tokens[:-1]
                middle = ' '.join(tokens)
            else:
                # Check second-to-last or embedded NAT
                for idx in range(len(tokens) - 1, 0, -1):
                    t = tokens[idx].upper()
                    if t in self.NAT_MAP and len(tokens[idx]) == 1:
                        result['nat'] = t
                        tokens.pop(idx)
                        middle = ' '.join(tokens)
                        break

        # Extract quantidade (number that's not part of denominacao)
        # Look for standalone number at the end of remaining middle
        tokens = middle.split()
        if tokens:
            last_token = tokens[-1]
            qty_match = re.match(r'^(\d+[.,]?\d*)$', last_token)
            if qty_match and len(tokens) > 1:
                try:
                    qty_str = last_token.replace(',', '.')
                    result['quantidade'] = float(qty_str)
                    tokens = tokens[:-1]
                    middle = ' '.join(tokens)
                except ValueError:
                    pass

        result['denominacao'] = middle.strip()
        return result

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
