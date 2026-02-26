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
        totals = self._extract_totals()
        vencimentos, descontos, liquido = totals[0], totals[1], totals[2]

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

        # Set base totals if available (from two-line format)
        if len(totals) > 3:
            holerite.base_ir = totals[3]
            holerite.base_redutor = totals[4]
            holerite.base_contrib_prev = totals[5]

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
            unidade=entidade.strip() if entidade else None,
            competencia=competencia or "",
            tipo_folha=tipo_folha,
            template_type=TemplateType.SPPREV_APOSENTADO,
            entidade=entidade.strip() if entidade else None,
            numero_beneficio=beneficio,
            percentual_aposentadoria=percentual,
            banco=banco,
            agencia=agencia,
            conta=conta,
            nivel=nivel,
        )

        self.extracted_cabecalho = cabecalho
        return cabecalho

    # NAT letter to NaturezaVerba mapping for SPPREV
    NAT_MAP = {
        "N": NaturezaVerba.NORMAL,
        "A": NaturezaVerba.ATRASADO,
        "R": NaturezaVerba.REPOSICAO,
        "C": NaturezaVerba.CREDITO,
        "D": NaturezaVerba.DEBITO,
    }

    def _extract_verbas(self) -> List[Verba]:
        """
        Extract earnings/deductions (verbas) from all pages.

        SPPREV Aposentado format:
        Código  Denominação  NAT  QTD  Unidade  Período  Vencimento  Descontos

        Example lines:
        001001 SALARIO BASE N 11/2025 2.685,68
        009001 ADIC TEMPO SERVICO N 5 11/2025 1.342,84
        070012 IMPOSTO DE RENDA N 11/2025                   1.393,52

        Descontos are detected by position (two-value lines) and stored as negative.

        Returns:
            List of Verba objects
        """
        if not self.paginas:
            return []

        verbas = []
        codigo_pattern = re.compile(r"^(\d{6})\s+")

        for page in self.paginas:
            lines = page.texto.split("\n")

            for line in lines:
                line_upper = line.upper()
                line_stripped = line.strip()

                if not line_stripped or "CÓDIGO" in line_upper or "DENOMINAÇ" in line_upper:
                    continue
                if "TOTAL" in line_upper or "LÍQUIDO" in line_upper or "BASE IR" in line_upper:
                    continue

                codigo_match = codigo_pattern.match(line_stripped)
                if not codigo_match:
                    continue

                try:
                    codigo_raw = codigo_match.group(1)
                    rest = line_stripped[codigo_match.end():].strip()

                    # Extract all monetary values from the line
                    # Brazilian format: 2.685,68 or 1.393,52
                    monetary_values = re.findall(r'(\d[\d.]*,\d{2})', rest)

                    if not monetary_values:
                        # Try simple number format
                        monetary_values = re.findall(r'(\d+\.\d{2})', rest)
                    if not monetary_values:
                        continue

                    # Determine if this is a desconto line (two values = vencimento + desconto)
                    # or single value line
                    is_desconto = False
                    if len(monetary_values) >= 2:
                        # Two values: first is vencimento (may be empty), second is desconto
                        # If first value appears early and second late, second is desconto
                        # Simplified: use the LAST value; if the position is far right, it's desconto
                        val_str = monetary_values[-1]
                        # Check if last value position is in the "descontos" column area
                        last_val_pos = rest.rfind(val_str)
                        first_val_pos = rest.find(monetary_values[0])
                        if last_val_pos > first_val_pos + len(monetary_values[0]) + 3:
                            is_desconto = True
                            val_str = monetary_values[-1]
                        else:
                            val_str = monetary_values[0]
                    else:
                        val_str = monetary_values[0]
                        # Single value: check position to determine vencimento vs desconto
                        # If the value starts past midpoint of original line, likely desconto
                        val_pos = line.rfind(val_str)
                        line_len = len(line)
                        if line_len > 0 and val_pos > line_len * 0.65:
                            is_desconto = True

                    valor = self._parse_valor(val_str)
                    if is_desconto:
                        valor = -abs(valor)

                    # Strip monetary values from rest to parse middle fields
                    middle = rest
                    for mv in monetary_values:
                        middle = middle.replace(mv, '', 1)
                    middle = middle.strip()

                    # Parse middle: DENOM [NAT] [QTD] [PERIODO]
                    parsed = self._parse_spprev_middle(middle)

                    verba = Verba(
                        codigo=codigo_raw,
                        denominacao=parsed['denominacao'] or "UNKNOWN",
                        natureza=parsed['natureza'],
                        quantidade=parsed['quantidade'],
                        unidade=parsed['unidade'],
                        periodo_inicio=parsed['periodo_inicio'],
                        periodo_fim=parsed['periodo_fim'],
                        valor=valor,
                        qualificadores_detectados=[],
                    )
                    verbas.append(verba)

                except (ValueError, AttributeError, IndexError):
                    continue

        return verbas

    def _parse_spprev_middle(self, middle: str) -> dict:
        """
        Parse middle section of SPPREV Aposentado verba line.

        Expected: DENOMINACAO [NAT] [QTD] [UNIDADE] [PERIODO]
        """
        result = {
            'denominacao': middle,
            'natureza': NaturezaVerba.NORMAL,
            'quantidade': None,
            'unidade': None,
            'periodo_inicio': None,
            'periodo_fim': None,
        }

        if not middle:
            return result

        # Extract periodo at end: MM/YYYY
        periodo_match = re.search(r'(\d{1,2}/\d{4})\s*$', middle)
        if periodo_match:
            periodo_str = periodo_match.group(1)
            pi, pf = self._normalize_periodo_range(periodo_str)
            result['periodo_inicio'] = pi
            result['periodo_fim'] = pf
            middle = middle[:periodo_match.start()].strip()

        # Extract NAT letter and QTD from remaining tokens
        tokens = middle.split()
        if not tokens:
            return result

        # Scan from end for NAT letter and quantity
        new_tokens = list(tokens)
        for idx in range(len(tokens) - 1, 0, -1):
            t = tokens[idx].upper()
            # Single letter NAT
            if t in self.NAT_MAP and len(tokens[idx]) == 1:
                result['natureza'] = self.NAT_MAP[t]
                new_tokens.pop(idx)
                break

        # Look for quantity (number) at end of remaining non-denom tokens
        if len(new_tokens) > 1:
            last = new_tokens[-1]
            qty_match = re.match(r'^(\d+[.,]?\d*)$', last)
            if qty_match:
                try:
                    result['quantidade'] = float(last.replace(',', '.'))
                    new_tokens.pop()
                except ValueError:
                    pass

        result['denominacao'] = ' '.join(new_tokens).strip()
        return result

    @staticmethod
    def _normalize_periodo_range(periodo_str: str):
        """Delegate to BaseParser's static method."""
        from src.core.parsers.base_parser import BaseParser
        return BaseParser._normalize_periodo_range(periodo_str)

    def _extract_totals(self) -> tuple:
        """
        Extract totals (vencimentos, descontos, líquido) and optionally base totals.

        Two-line format:
           BASE IR BASE REDUTOR BASE CONTRIB PREV TOTAL VENCTOS TOTAL DE DESCONTOS TOTAL LÍQUIDO
           8.371,81 0,00 8.979,01 8.979,01 2.795,51 6.183,50
           6 values = base_ir, base_redutor, base_contrib_prev, vencimentos, descontos, líquido

        Returns:
            Tuple of (vencimentos, descontos, liquido) or
            (vencimentos, descontos, liquido, base_ir, base_redutor, base_contrib_prev)
        """
        if not self.paginas:
            return (0.0, 0.0, 0.0)

        for page in reversed(self.paginas):
            texto = page.texto
            lines = texto.split("\n")

            for i, line in enumerate(lines):
                line_upper = line.upper().strip()

                if ("VENCTO" in line_upper and "DESCONTO" in line_upper
                        and ("QUIDO" in line_upper or "LIQUIDO" in line_upper)):
                    for j in range(i + 1, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        valores = re.findall(r"[-]?[\d.,]+", next_line)
                        if len(valores) >= 6:
                            base_ir = self._parse_valor(valores[-6])
                            base_redutor = self._parse_valor(valores[-5])
                            base_contrib_prev = self._parse_valor(valores[-4])
                            vencimentos = self._parse_valor(valores[-3])
                            descontos = self._parse_valor(valores[-2])
                            liquido = self._parse_valor(valores[-1])
                            return (vencimentos, descontos, liquido,
                                    base_ir, base_redutor, base_contrib_prev)
                        elif len(valores) >= 3:
                            vencimentos = self._parse_valor(valores[-3])
                            descontos = self._parse_valor(valores[-2])
                            liquido = self._parse_valor(valores[-1])
                            return (vencimentos, descontos, liquido)
                        break

            # Fallback: single-line format
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
