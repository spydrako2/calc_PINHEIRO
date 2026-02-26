"""
SPPREV Pensionista-specific holerite parser
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


class SpprevPensionistaParser(BaseParser):
    """
    Parser for SPPREV (São Paulo Previdência) Pensionista template

    Unique 2-section structure:
    1. BASE DE CÁLCULO DO BENEFÍCIO (calculation base)
    2. DEMONSTRATIVO DO PAGAMENTO DO BENEFÍCIO (payment statement)

    Handles extraction of:
    - Header: CPF, Name, Ex-Servidor Cargo, Entidade, Tipo Folha, Competência,
              Benefício, % Cota Parte, Banco/Agência/Conta
    - Base Cálculo: Verbas with código, denominação, vencimentos, descontos
    - Demonstrativo: Verbas with código, denominação, período, vencimentos, descontos (with -C/-D markers)
    - Totals: Multiple totals sections (base calc + demonstrative)
    """

    # Regex patterns for SPPREV template detection
    SPPREV_PENSIONISTA_KEYWORDS = [
        r"S\s*Ã\s*O\s+PAULO\s+PREVID.*NCIA|SPPREV",
        r"PENS.*O",  # PENSÃO or variations
        r"DEMONSTRATIVO\s+DE\s+PAGAMENTO",
    ]

    def __init__(self):
        """Initialize SPPREV Pensionista parser"""
        super().__init__()
        self.extracted_cabecalho: Optional[CabecalhoHolerite] = None

    def detect_template(self, texto: str) -> bool:
        """
        Detect if text belongs to SPPREV Pensionista template

        PENSÃO keyword is MANDATORY to differentiate from SPPREV Aposentado.
        Also requires at least one SPPREV identifier (SPPREV or DEMONSTRATIVO).

        Args:
            texto: Extracted text from page

        Returns:
            True if SPPREV Pensionista template detected, False otherwise
        """
        texto_upper = texto.upper()

        # PENSÃO is mandatory — without it, this is NOT a Pensionista document
        has_pensao = bool(re.search(r"PENS[ÃA]O", texto_upper))
        if not has_pensao:
            return False

        # Also need at least one SPPREV indicator
        has_spprev = bool(re.search(
            r"S\s*[ÃA]\s*O\s+PAULO\s+PREVID|SPPREV", texto_upper
        ))
        has_demonstrativo = bool(re.search(
            r"DEMONSTRATIVO\s+DE\s+PAGAMENTO", texto_upper
        ))

        return has_spprev or has_demonstrativo

    def parse(self, paginas: List[PaginaExtraida]) -> Holerite:
        """
        Parse SPPREV Pensionista holerite pages

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

        SPPREV Pensionista header includes:
        - Nome, CPF, Cargo Ex-Servidor, Entidade, Tipo Folha, Competência
        - Benefício, % Cota Parte, Banco, Agência, Conta

        Layout is more compact than Aposentado - multiple fields per line

        Returns:
            CabecalhoHolerite object

        Raises:
            ValueError: If required fields (nome, cpf) not found
        """
        if not self.paginas:
            raise ValueError("No pages provided")

        texto = self.get_first_page_text()

        # Extract required CPF using simple pattern
        cpf_match = re.search(r"(\d{3}\.\d{3}\.\d{3}-\d{2})", texto)
        if not cpf_match:
            raise ValueError("CPF not found in holerite")
        cpf = cpf_match.group(1)

        # Extract required Name
        # Pattern: "Nome CPF ... \n NAME CPF"
        nome_match = re.search(
            r"Nome\s+CPF.*?\n\s*([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)\s+\d{3}\.\d{3}",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        if not nome_match:
            # Fallback: look for uppercase name before CPF
            nome_match = re.search(
                r"(?:NOME|Nome)\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)(?:\n|\s\d{3}\.\d{3})",
                texto,
                re.IGNORECASE | re.MULTILINE,
            )
        if not nome_match:
            raise ValueError("Nome not found in holerite")
        nome = nome_match.group(1).strip()

        # Extract optional fields
        # Cargo Ex-Servidor
        cargo_match = re.search(
            r"Cargo\s+Ex-Servidor\s+([A-ZÁÉÍÓÚÂÃÕÊÔ0-9\w\s\/\-]+?)(?:\n|BENEF)",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        cargo = cargo_match.group(1).strip() if cargo_match else None

        # Entidade (extracted from context)
        entidade_match = re.search(
            r"Cargo\s+Ex-Servidor\s+([A-ZÁÉÍÓÚÂÃÕÊÔ0-9\w\s\/\-]+?)\s+BENEF",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        entidade = entidade_match.group(1).strip() if entidade_match else cargo

        # Benefício
        beneficio_match = re.search(
            r"BENEF.*CIO\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\s\/]+?)(?:\s+N\s*°|$)",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        beneficio = beneficio_match.group(1).strip() if beneficio_match else None

        # Benefício number (N° BENEFÍCIO)
        beneficio_num_match = re.search(
            r"N\s*°\s*BENEF.*CIO\s+(\d+[/-]\d+)",
            texto,
            re.IGNORECASE,
        )
        beneficio_num = beneficio_num_match.group(1) if beneficio_num_match else None

        # Cota Parte
        cota_match = re.search(r"COTA\s+PARTE\s+([\d.,]+)", texto, re.IGNORECASE)
        cota_parte = cota_match.group(1) if cota_match else None

        # Tipo Folha
        tipo_folha_match = re.search(
            r"TIPO\s+FOLHA\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s]+?)(?:\n|COMPET)",
            texto,
            re.IGNORECASE | re.MULTILINE,
        )
        tipo_folha_str = tipo_folha_match.group(1).strip() if tipo_folha_match else None

        # Competência — may be on same line or next line after label
        competencia_match = re.search(
            r"Compet[^\n]*?\s+(\d{1,2}[/\-]\d{4})",
            texto,
            re.IGNORECASE,
        )
        if not competencia_match:
            # Cross-line: "Competência\n... 12/2024"
            competencia_match = re.search(
                r"Compet[^\n]*\n[^\n]*?(\d{1,2}[/\-]\d{4})",
                texto,
                re.IGNORECASE,
            )
        competencia = None
        if competencia_match:
            competencia = self._normalize_date(competencia_match.group(1), "AAAA-MM")
        else:
            competencia = ""

        # Banco/Agência/Conta
        banco_match = re.search(r"Banco\s+(\d{4})", texto, re.IGNORECASE)
        banco = banco_match.group(1) if banco_match else None

        agencia_match = re.search(r"AG.*NCIA\s+(\d{4})", texto, re.IGNORECASE)
        agencia = agencia_match.group(1) if agencia_match else None

        conta_match = re.search(r"N\s*°?\s*CONTA\s+([\d-]+)", texto, re.IGNORECASE)
        conta = conta_match.group(1) if conta_match else None

        # Determine Tipo de Folha
        tipo_folha = self._extract_tipo_folha(texto, tipo_folha_str)

        # Create header object with Pensionista-specific fields
        cabecalho = CabecalhoHolerite(
            nome=nome,
            cpf=cpf,
            cargo=cargo,
            unidade=entidade,
            competencia=competencia,
            tipo_folha=tipo_folha,
            template_type=TemplateType.SPPREV_PENSIONISTA,
            entidade=entidade,
            beneficio=beneficio,
            numero_beneficio=beneficio_num,
            cota_parte=cota_parte,
            banco=banco,
            agencia=agencia,
            conta=conta,
        )

        self.extracted_cabecalho = cabecalho
        return cabecalho

    def _extract_verbas(self) -> List[Verba]:
        """
        Extract earnings/deductions from both sections:
        1. BASE DE CÁLCULO DO BENEFÍCIO
        2. DEMONSTRATIVO DO PAGAMENTO DO BENEFÍCIO

        Verbas format:
        - Base Cálculo: Código DENOMINAÇÃO Vencimentos Descontos
        - Demonstrativo: Código DENOMINAÇÃO-C/D PERÍODO Vencimentos Descontos

        -C = Crédito (vencimento), -D = Débito (desconto, stored as negative)
        Descontos detected by column position and stored as negative values.

        Returns:
            List of Verba objects from both sections
        """
        if not self.paginas:
            return []

        verbas = []
        codigo_pattern = re.compile(r"^(\d{6})")

        for page in self.paginas:
            lines = page.texto.split("\n")

            in_base_calculo = False
            in_demonstrativo = False

            for line in lines:
                line_upper = line.upper()
                line_stripped = line.strip()

                # Detect section start
                if "BASE" in line_upper and ("CALCULO" in line_upper or "CÁLCULO" in line_upper):
                    in_base_calculo = True
                    in_demonstrativo = False
                    continue
                elif "DEMONSTRATIVO" in line_upper and ("PAGAMENTO" in line_upper or "BENEFÍCIO" in line_upper or "BENEFICIO" in line_upper):
                    in_base_calculo = False
                    in_demonstrativo = True
                    continue

                if "MENSAGEM" in line_upper or "ATEN" in line_upper:
                    in_base_calculo = False
                    in_demonstrativo = False
                    continue

                if not in_base_calculo and not in_demonstrativo:
                    continue

                if not line_stripped or "CÓDIGO" in line_upper:
                    continue
                if "TOTAL" in line_upper or "LÍQUIDO" in line_upper:
                    continue

                codigo_match = codigo_pattern.match(line_stripped)
                if not codigo_match:
                    continue

                try:
                    codigo_raw = codigo_match.group(1)
                    rest = line_stripped[codigo_match.end():].strip()

                    # Extract all monetary values
                    monetary_values = re.findall(r'(\d[\d.]*,\d{2})', rest)
                    if not monetary_values:
                        monetary_values = re.findall(r'(\d+\.\d{2})', rest)
                    if not monetary_values:
                        continue

                    # Determine vencimento vs desconto by position
                    is_desconto = False
                    if len(monetary_values) >= 2:
                        last_val_pos = rest.rfind(monetary_values[-1])
                        first_val_pos = rest.find(monetary_values[0])
                        if last_val_pos > first_val_pos + len(monetary_values[0]) + 3:
                            is_desconto = True
                            val_str = monetary_values[-1]
                        else:
                            val_str = monetary_values[0]
                    else:
                        val_str = monetary_values[0]
                        val_pos = line.rfind(val_str)
                        line_len = len(line)
                        if line_len > 0 and val_pos > line_len * 0.65:
                            is_desconto = True

                    valor = self._parse_valor(val_str)
                    if is_desconto:
                        valor = -abs(valor)

                    # Strip monetary values from rest to get middle
                    middle = rest
                    for mv in monetary_values:
                        middle = middle.replace(mv, '', 1)
                    middle = middle.strip()

                    # Parse -C/-D marker and periodo
                    natureza = NaturezaVerba.NORMAL
                    denominacao = middle
                    periodo_inicio = None
                    periodo_fim = None

                    # Check for -C/-D marker
                    marker_match = re.search(r'(.+?)-([CD])\b', middle)
                    if marker_match and in_demonstrativo:
                        denominacao = marker_match.group(1).strip()
                        marker = marker_match.group(2)
                        if marker == "C":
                            natureza = NaturezaVerba.CREDITO
                        elif marker == "D":
                            natureza = NaturezaVerba.DEBITO
                        # Remaining after marker for periodo
                        after_marker = middle[marker_match.end():].strip()
                        periodo_match = re.search(r'(\d{1,2}/\d{4})', after_marker)
                        if periodo_match:
                            from src.core.parsers.base_parser import BaseParser
                            periodo_inicio, periodo_fim = BaseParser._normalize_periodo_range(
                                periodo_match.group(1)
                            )
                    elif in_demonstrativo:
                        # No marker but in demonstrativo — extract periodo
                        periodo_match = re.search(r'(\d{1,2}/\d{4})\s*$', denominacao)
                        if periodo_match:
                            from src.core.parsers.base_parser import BaseParser
                            periodo_inicio, periodo_fim = BaseParser._normalize_periodo_range(
                                periodo_match.group(1)
                            )
                            denominacao = denominacao[:periodo_match.start()].strip()

                    verba = Verba(
                        codigo=codigo_raw,
                        denominacao=denominacao if denominacao else "UNKNOWN",
                        natureza=natureza,
                        quantidade=None,
                        unidade=None,
                        periodo_inicio=periodo_inicio,
                        periodo_fim=periodo_fim,
                        valor=valor,
                        qualificadores_detectados=[],
                    )
                    verbas.append(verba)

                except (ValueError, AttributeError, IndexError):
                    continue

        return verbas

    def _extract_totals(self) -> tuple:
        """
        Extract totals from the DEMONSTRATIVO section (payment statement).

        Handles two formats:
        1. Same-line: "Total Vencimentos 5.604,34"
        2. Two-line (header + values):
           Total Vencimentos Total Descontos Líquido a Receber
           5.604,34 173,61 5.430,73

        Returns the LAST matching totals line (from DEMONSTRATIVO, not BASE DE CÁLCULO).

        Returns:
            Tuple of (vencimentos, descontos, liquido)
        """
        if not self.paginas:
            return (0.0, 0.0, 0.0)

        # Collect all totals-header matches; use the last one (DEMONSTRATIVO section)
        last_totals = None

        for page in reversed(self.paginas):
            texto = page.texto
            lines = texto.split("\n")

            for i, line in enumerate(lines):
                line_upper = line.upper().strip()

                # Find totals header line: "Total Vencimentos Total Descontos Líquido..."
                if ("VENCIMENTO" in line_upper and "DESCONTO" in line_upper
                        and ("QUIDO" in line_upper or "LIQUIDO" in line_upper)):
                    # Read next non-empty line for values
                    for j in range(i + 1, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        valores = re.findall(r"[-]?[\d.,]+", next_line)
                        if len(valores) >= 3:
                            vencimentos = self._parse_valor(valores[-3])
                            descontos = self._parse_valor(valores[-2])
                            liquido = self._parse_valor(valores[-1])
                            last_totals = (vencimentos, descontos, liquido)
                        break

            if last_totals:
                return last_totals

        # Fallback: single-line pattern search
        for page in reversed(self.paginas):
            texto = page.texto
            lines = texto.split("\n")
            vencimentos = 0.0
            descontos = 0.0
            liquido = 0.0
            valor_regex = r"([-]?[\d.,]+)"

            for line in lines:
                line_upper = line.upper().strip()
                match = re.search(rf"(?:TOTAL\s+)?(?:VENCIMENTOS?|VENCTOS?)\s+{valor_regex}", line_upper)
                if match and vencimentos == 0.0:
                    vencimentos = self._parse_valor(match.group(1))
                match = re.search(rf"(?:TOTAL\s+)?(?:DE\s+)?DESCONTOS?\s+{valor_regex}", line_upper)
                if match and descontos == 0.0:
                    descontos = self._parse_valor(match.group(1))
                match = re.search(rf"L[ÍI]QUIDO[^\d]*{valor_regex}", line_upper)
                if match and liquido == 0.0:
                    liquido = self._parse_valor(match.group(1))

            if vencimentos > 0 or liquido > 0:
                return (vencimentos, descontos, liquido)

        return (0.0, 0.0, 0.0)

    def _normalize_date(self, date_str: str, target_format: str) -> str:
        """
        Normalize date format

        Args:
            date_str: Date string (various formats)
            target_format: Target format (AAAA-MM or DD/MM/YYYY)

        Returns:
            Normalized date string
        """
        date_clean = date_str.replace("/", "-").replace(".", "-").strip()

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
