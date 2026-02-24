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

        Requires at least 2 keywords including PENSÃO indicator

        Args:
            texto: Extracted text from page

        Returns:
            True if SPPREV Pensionista template detected, False otherwise
        """
        texto_upper = texto.upper()

        # Check for SPPREV keywords
        matches = 0
        for pattern in self.SPPREV_PENSIONISTA_KEYWORDS:
            if re.search(pattern, texto_upper, re.IGNORECASE):
                matches += 1

        # SPPREV Pensionista requires at least 2 keywords (SPPREV + PENSÃO)
        return matches >= 2

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

        # Competência
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

        # Banco/Agência/Conta
        banco_match = re.search(r"Banco\s+(\d{4})", texto, re.IGNORECASE)
        banco = banco_match.group(1) if banco_match else None

        agencia_match = re.search(r"AG.*NCIA\s+(\d{4})", texto, re.IGNORECASE)
        agencia = agencia_match.group(1) if agencia_match else None

        conta_match = re.search(r"N\s*°?\s*CONTA\s+([\d-]+)", texto, re.IGNORECASE)
        conta = conta_match.group(1) if conta_match else None

        # Determine Tipo de Folha
        tipo_folha = self._extract_tipo_folha(texto, tipo_folha_str)

        # Create header object
        cabecalho = CabecalhoHolerite(
            nome=nome,
            cpf=cpf,
            cargo=cargo,
            unidade=entidade,
            competencia=competencia,
            tipo_folha=tipo_folha,
            template_type=TemplateType.SPPREV_PENSIONISTA,
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

        The -C suffix means Crédito (CREDITO), -D means Débito (DEBITO)

        Returns:
            List of Verba objects from both sections
        """
        if not self.paginas:
            return []

        verbas = []

        # Regex pattern for 6-digit código
        codigo_pattern = r"^(\d{6})"

        # Extract from all pages
        for page in self.paginas:
            texto = page.texto
            lines = texto.split("\n")

            # Track which section we're in
            in_base_calculo = False
            in_demonstrativo = False

            for i, line in enumerate(lines):
                line_upper = line.upper()
                line_stripped = line.strip()

                # Detect section start
                if "BASE" in line_upper and "CALCULO" in line_upper:
                    in_base_calculo = True
                    in_demonstrativo = False
                    continue
                elif "DEMONSTRATIVO" in line_upper and "PAGAMENTO" in line_upper:
                    in_base_calculo = False
                    in_demonstrativo = True
                    continue

                # End of document
                if "MENSAGEM" in line_upper or "ATEN" in line_upper.upper():
                    in_base_calculo = False
                    in_demonstrativo = False
                    continue

                # Skip if not in a section
                if not in_base_calculo and not in_demonstrativo:
                    continue

                # Skip empty lines or headers
                if not line_stripped or "CÓDIGO" in line_upper:
                    continue

                # Skip total lines
                if "TOTAL" in line_upper or "LÍQUIDO" in line_upper:
                    continue

                # Try to extract código
                codigo_match = re.match(codigo_pattern, line_stripped)
                if not codigo_match:
                    continue

                try:
                    codigo_raw = codigo_match.group(1)

                    # Get rest of line after código
                    rest_of_line = line_stripped[codigo_match.end() :].strip()

                    # Extract monetary value at end
                    valor_pattern = r"([-]?\d+[.,]\d{2})\s*$"
                    valor_match = re.search(valor_pattern, rest_of_line)

                    if not valor_match:
                        continue

                    valor_str = valor_match.group(1)

                    # Get denominação
                    denominacao_section = rest_of_line[: valor_match.start()].strip()

                    # Check for -C (Crédito) or -D (Débito) marker in denominação (Demonstrativo only)
                    natureza = NaturezaVerba.NORMAL
                    if in_demonstrativo:
                        if denominacao_section.endswith("-C"):
                            natureza = NaturezaVerba.CREDITO
                            denominacao = denominacao_section[:-2].strip()
                        elif denominacao_section.endswith("-D"):
                            natureza = NaturezaVerba.DEBITO
                            denominacao = denominacao_section[:-2].strip()
                        else:
                            denominacao = denominacao_section.strip()
                    else:
                        denominacao = denominacao_section.strip()

                    # Parse valor
                    valor = self._parse_valor(valor_str)

                    # Create Verba object
                    verba = Verba(
                        codigo=codigo_raw,
                        denominacao=denominacao if denominacao else "UNKNOWN",
                        natureza=natureza,
                        quantidade=None,
                        unidade=None,
                        valor=valor,
                        qualificadores_detectados=[],
                    )

                    verbas.append(verba)

                except (ValueError, AttributeError, IndexError):
                    continue

        return verbas

    def _extract_totals(self) -> tuple:
        """
        Extract totals from both sections

        SPPREV Pensionista has multiple total lines:
        - BASE DE CÁLCULO: Total Vencimentos, Total Descontos, Base p/ Cálculo
        - DEMONSTRATIVO: Total Vencimentos, Total Descontos, Líquido a Receber

        We return the values from the DEMONSTRATIVO section (payment statement)
        as those are the final amounts for the employee.

        Returns:
            Tuple of (vencimentos, descontos, liquido) from DEMONSTRATIVO section
        """
        if not self.paginas:
            return (0.0, 0.0, 0.0)

        vencimentos = 0.0
        descontos = 0.0
        liquido = 0.0

        # Pattern to find total lines
        # Look for DEMONSTRATIVO section totals specifically
        valor_regex = r"[-]?[\d.,]+"

        for page in reversed(self.paginas):
            texto = page.texto
            texto_upper = texto.upper()

            # Find DEMONSTRATIVO section
            if "DEMONSTRATIVO" in texto_upper:
                # Extract totals after DEMONSTRATIVO marker
                demonst_section = texto_upper[texto_upper.find("DEMONSTRATIVO") :]

                # Total Vencimentos
                vencimentos_pattern = rf"(?:TOTAL\s+)?VENCIMENTOS?\s*({valor_regex})"
                vencimentos_match = re.search(vencimentos_pattern, demonst_section)
                if vencimentos_match and vencimentos == 0.0:
                    valor_str = vencimentos_match.group(1)
                    vencimentos = self._parse_valor(valor_str)

                # Total Descontos
                descontos_pattern = rf"(?:TOTAL\s+)?(?:DE\s+)?DESCONTOS?\s*({valor_regex})"
                descontos_match = re.search(descontos_pattern, demonst_section)
                if descontos_match and descontos == 0.0:
                    valor_str = descontos_match.group(1)
                    descontos = self._parse_valor(valor_str)

                # Líquido (L[ÍI]QUIDO or "Líquido a Receber")
                liquido_pattern = rf"(?:L[ÍI]QUIDO|L[ÍI]QUIDO\s+[A-Z]+\s+[A-Z]+)\s*({valor_regex})"
                liquido_match = re.search(liquido_pattern, demonst_section)
                if liquido_match and liquido == 0.0:
                    valor_str = liquido_match.group(1)
                    liquido = self._parse_valor(valor_str)

                # If all three found, we're done
                if vencimentos > 0 and descontos >= 0 and liquido > 0:
                    break

        return (vencimentos, descontos, liquido)

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

        Args:
            valor_str: Value string like "5000.00", "5.000,00", etc.

        Returns:
            Float value
        """
        if not valor_str:
            return 0.0

        valor_str = valor_str.strip()

        try:
            if "," in valor_str:
                # Brazilian format: 1.000,00
                valor_normalized = valor_str.replace(".", "").replace(",", ".")
            elif valor_str.count(".") == 1 and any(
                valor_str.endswith(x) for x in [".00", ".50", ".25", ".75"]
            ):
                # American format: 1000.00
                valor_normalized = valor_str
            else:
                # Default: Brazilian format
                valor_normalized = valor_str.replace(".", "").replace(",", ".")

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
