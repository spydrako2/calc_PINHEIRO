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
        cpf = self._extract_cpf(texto)
        if not cpf:
            raise ValueError("CPF not found in holerite")

        # Extract Name (DDPE table layout: header "Nome" → valor na próxima linha)
        nome = self._extract_nome_ddpe(texto) or self._extract_field(texto, "nome")
        if not nome:
            raise ValueError("Nome not found in holerite")

        # Extract optional fields (DDPE table layout aware)
        cargo = self._extract_cargo_ddpe(texto) or self._extract_field(texto, "cargo")
        unidade = self._extract_unidade_ddpe(texto) or self._extract_field(texto, "unidade")
        competencia = self._extract_competencia_ddpe(texto) or self._extract_field(texto, "competencia")
        data_pagamento = self._extract_data_pagamento_ddpe(texto) or self._extract_field(texto, "data_pagamento")

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

        DDPE full format (single-line — pdfplumber):
        12.015  ADIC.LOCAL EXERC.CAR.POL/DELEG.  A  PERC.  01/09/2007 A 30/09/2007  329,65+
        70.006  IAMSPE                            A  2,00  PERC.  01/09/2007 A 30/09/2007  6,59-

        DDPE multi-line format (PyMuPDF — value on separate line above code):
        2.007,99+
        01.001 SALARIO BASE N VALOR 03/2013

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
        # Standalone value line (PyMuPDF multi-line: value on its own line)
        standalone_valor_re = re.compile(r'^([-]?\d[\d.,]*\d)\s*([+\-])\s*$')

        # Detect context for fallback natureza (section-based)
        is_atrasado_section = False
        is_reposicao_section = False

        for page in self.paginas:
            lines = page.texto.split('\n')
            pending_valor = None  # (valor_str, sinal) from standalone line above

            for line in lines:
                line_upper = line.upper()
                line_stripped = line.strip()

                # Section markers (fallback for simplified format)
                if 'ATRASADO' in line_upper and not re.match(r'^\d{2}\.?\d{3}', line_stripped):
                    is_atrasado_section = True
                    is_reposicao_section = False
                    pending_valor = None
                    continue
                elif ('REPOSIÇÃO' in line_upper or 'REPOSICAO' in line_upper) and not re.match(r'^\d{2}\.?\d{3}', line_stripped):
                    is_reposicao_section = True
                    is_atrasado_section = False
                    pending_valor = None
                    continue
                elif 'TOTAL' in line_upper or 'LÍQUIDO' in line_upper:
                    break

                if not line_stripped or 'CÓDIGO' in line_upper or 'DENOMINAÇÃO' in line_upper:
                    pending_valor = None
                    continue

                codigo_match = codigo_start.match(line_stripped)
                if not codigo_match:
                    # Check if this is a standalone value line (e.g. "2.007,99+")
                    sv_match = standalone_valor_re.match(line_stripped)
                    if sv_match:
                        pending_valor = (sv_match.group(1), sv_match.group(2))
                    else:
                        pending_valor = None
                    continue

                try:
                    codigo_raw = codigo_match.group(1)
                    rest = line_stripped[codigo_match.end():]

                    # Try full format first: value with +/- sign at end of same line
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
                        pending_valor = None
                    elif pending_valor:
                        # PyMuPDF multi-line: value was on standalone line above
                        valor_str, sinal = pending_valor
                        valor = self._parse_valor(valor_str)
                        if sinal == '-':
                            valor = -abs(valor)
                        else:
                            valor = abs(valor)
                        middle = rest.strip()
                        parsed = self._parse_ddpe_middle(middle)
                        pending_valor = None
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
        Extrai totais do holerite DDPE.

        O DDPE usa layout de tabela: cabeçalho 'Total Descontos Líquido a Receber'
        seguido de valores em 1-3 linhas, sem labels inline.

        Estratégia: coleta todos os números após o cabeçalho e busca a tripla
        (V, D, L) onde V - D ≈ L (tolerância 0.02).
        """
        if not self.paginas:
            return (0.0, 0.0, 0.0)

        for page in reversed(self.paginas):
            result = self._parse_totals_from_page(page.texto)
            if result:
                return result

        return (0.0, 0.0, 0.0)

    def _parse_totals_from_page(self, texto: str) -> Optional[tuple]:
        """
        Busca totais em uma página do DDPE.
        Encontra o cabeçalho de totais e coleta números das linhas seguintes.
        Retorna (vencimentos, descontos, liquido) ou None se não encontrado.
        """
        # Cabeçalho de totais contém essas palavras juntas
        header_match = re.search(
            r'(?:Total\s+)?Descontos.*?L[íi]quido',
            texto, re.IGNORECASE
        )
        if not header_match:
            return None

        # Pega as 3 linhas após o cabeçalho
        rest = texto[header_match.end():]
        lines_after = rest.split('\n')[:4]
        following_text = '\n'.join(lines_after)

        # Extrai todos os números válidos (formato brasileiro, > 0)
        raw_numbers = re.findall(r'\b(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\b', following_text)
        values = []
        for n in raw_numbers:
            v = self._parse_valor(n)
            if v > 0:
                values.append(v)

        if len(values) < 3:
            return None

        # Busca tripla (V, D, L) onde V - D ≈ L
        for i, v in enumerate(values):
            for j, d in enumerate(values):
                if j == i:
                    continue
                for k, l in enumerate(values):
                    if k == i or k == j:
                        continue
                    if v > d and abs(v - d - l) < 0.02:
                        return (v, d, l)

        return None

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

    def _extract_nome_ddpe(self, texto: str) -> Optional[str]:
        """Extrai nome do layout de tabela DDPE: 'Nome Reg. Sistema...' → linha seguinte."""
        m = re.search(r'Nome\s+Reg\..*[\r\n]+([^\r\n]+)', texto, re.IGNORECASE)
        if m:
            data_line = m.group(1)
            # Nome é o início da linha, antes do primeiro código numérico (ex: 09.918.851/01)
            nome_m = re.match(r'^([A-ZÁÉÍÓÚÂÃÕÊÔa-záéíóúâãõêô\s]+?)(?:\s{2,}|\s+\d{2}\.)', data_line)
            if nome_m:
                return nome_m.group(1).strip()
        return None

    def _extract_cargo_ddpe(self, texto: str) -> Optional[str]:
        """Extrai cargo do layout DDPE: 'PIS / PASEP Cargo / Função...' → linha seguinte."""
        m = re.search(r'PIS\s*/\s*PASEP.*?Cargo.*?[\r\n]+([^\r\n]+)', texto, re.IGNORECASE)
        if m:
            data_line = m.group(1)
            # Cargo é o texto após o PIS/PASEP (código numérico inicial)
            cargo_m = re.match(r'[\d\.\-]+\s+(.+?)(?:\s{3,}|\s+TITULAR|\s+COMISSIONADO|$)', data_line)
            if cargo_m:
                return cargo_m.group(1).strip()
        return None

    def _extract_unidade_ddpe(self, texto: str) -> Optional[str]:
        """Extrai unidade do layout DDPE: 'Municipio U.C.D. Unidade...' → linha seguinte."""
        m = re.search(r'Municipio.*?Unidade.*?[\r\n]+([^\r\n]+)', texto, re.IGNORECASE)
        if m:
            data_line = m.group(1)
            # Unidade é o texto após os códigos numéricos iniciais
            unidade_m = re.match(r'[\d\s]+(.+)', data_line)
            if unidade_m:
                return unidade_m.group(1).strip()
        return None

    def _extract_competencia_ddpe(self, texto: str) -> Optional[str]:
        """Extrai competência do layout DDPE: 'Tipo da Folha Data Pagamento' → linha seguinte."""
        m = re.search(r'Tipo da Folha.*?[\r\n]+([^\r\n]+)', texto, re.IGNORECASE)
        if m:
            data_line = m.group(1)
            comp_m = re.search(r'(\d{2}/\d{4})', data_line)
            if comp_m:
                return comp_m.group(1)
        return None

    def _extract_data_pagamento_ddpe(self, texto: str) -> Optional[str]:
        """Extrai data de pagamento do layout DDPE."""
        m = re.search(r'Tipo da Folha.*?[\r\n]+([^\r\n]+)', texto, re.IGNORECASE)
        if m:
            data_line = m.group(1)
            date_m = re.search(r'(\d{2}/\d{2}/\d{4})', data_line)
            if date_m:
                return date_m.group(1)
        return None

    def _extract_cpf(self, texto: str) -> Optional[str]:
        """
        Extrai CPF do texto do holerite DDPE.

        Suporta dois layouts:
        1. Mesmo linha:  CPF: 123.456.789-00
        2. Tabela DDPE:  cabeçalho "C.P.F" na linha acima, valor (147635888/50) no final da linha seguinte
        """
        # Layout 1: CPF na mesma linha com label
        m = re.search(r'C\.?P\.?F[:\s]+(\d{3}\.\d{3}\.\d{3}-\d{2})', texto, re.IGNORECASE)
        if m:
            return self._normalize_cpf(m.group(1))

        # Layout 2 (DDPE): header "C.P.F" → valor no final da próxima linha
        m = re.search(r'C\.P\.F\s*[\r\n]+[^\r\n]*?(\d{9}/\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})', texto, re.IGNORECASE)
        if m:
            return self._normalize_cpf(m.group(1))

        # Fallback: padrão numérico DDPE em qualquer lugar do texto
        m = re.search(r'\b(\d{9}/\d{2})\b', texto)
        if m:
            return self._normalize_cpf(m.group(1))

        return None

    def _normalize_cpf(self, cpf_raw: str) -> str:
        """Normaliza CPF para o formato padrão XXX.XXX.XXX-XX."""
        digits = re.sub(r'\D', '', cpf_raw)
        if len(digits) == 11:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        return cpf_raw.strip()

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
