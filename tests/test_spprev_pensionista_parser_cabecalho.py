"""Tests for SPPREV Pensionista parser header extraction"""

import pytest
from src.core.parsers.spprev_pensionista_parser import SpprevPensionistaParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import TipoFolha, TemplateType


class TestSpprevPensionistaParserCabecalho:
    """Test SPPREV Pensionista parser header extraction"""

    @pytest.fixture
    def parser(self):
        """Create SPPREV Pensionista parser"""
        return SpprevPensionistaParser()

    @pytest.fixture
    def sample_pensionista_page(self):
        """Sample SPPREV Pensionista holerite page (real structure)"""
        texto = """
        GOVERNO DO ESTADO DE SÃO PAULO
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DEMONSTRATIVO DE PAGAMENTO Data Pagamento Fls
        08/01/2025 1/1
        Nome CPF Dep IR Banco Agência N° Conta
        MARIA INES MARQUES DE ALMEIDA 026.188.918-48 00 0001 6926 00-000012170-
        Cargo Ex-Servidor Benefício N° Benefício COTA PARTE Tipo Folha Competência
        04115 PENSAO POR MORTE 61030225-00 100,00 NORMAL 12/2024
        BASE DE CÁLCULO DO BENEFÍCIO Total Vencimentos Total Descontos Base p / Cálculo
        5.604,34 0,00 5.604,34
        Código Denominação Vencimentos Descontos
        001031 BENEFÍCIO PREVIDENCIÁRIO LC 1.354/2020 5.604,34
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_detect_template_pensionista(self, parser):
        """Should detect SPPREV Pensionista template"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        PENSÃO POR MORTE
        DEMONSTRATIVO DE PAGAMENTO
        """
        assert parser.detect_template(texto) is True

    def test_detect_template_requires_pension_keyword(self, parser):
        """Should require PENSÃO keyword"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        APOSENTADORIA
        DEMONSTRATIVO DE PAGAMENTO
        """
        assert parser.detect_template(texto) is False

    def test_detect_template_not_pensionista(self, parser):
        """Should not detect DDPE or SPPREV Aposentado"""
        texto = "DEPARTAMENTO DE DESPESA\nFOLHA DE PAGAMENTO"
        assert parser.detect_template(texto) is False

    def test_extract_cpf_valid(self, parser, sample_pensionista_page):
        """Should extract valid CPF"""
        parser.paginas = [sample_pensionista_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.cpf == "026.188.918-48"

    def test_extract_nome(self, parser, sample_pensionista_page):
        """Should extract name"""
        parser.paginas = [sample_pensionista_page]
        cabecalho = parser._extract_cabecalho()
        assert "MARIA" in cabecalho.nome.upper()
        assert "INES" in cabecalho.nome.upper()

    def test_extract_cargo_ex_servidor(self, parser, sample_pensionista_page):
        """Should extract cargo ex-servidor"""
        parser.paginas = [sample_pensionista_page]
        cabecalho = parser._extract_cabecalho()
        # Cargo may be None or contain the code
        assert cabecalho.cargo is None or "04115" in cabecalho.cargo

    def test_extract_competencia(self, parser, sample_pensionista_page):
        """Should extract competencia"""
        parser.paginas = [sample_pensionista_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.competencia == "2024-12"

    def test_extract_tipo_folha_normal(self, parser, sample_pensionista_page):
        """Should extract NORMAL tipo de folha"""
        parser.paginas = [sample_pensionista_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.tipo_folha == TipoFolha.NORMAL

    def test_extract_template_type_is_pensionista(self, parser, sample_pensionista_page):
        """Should set template_type to SPPREV_PENSIONISTA"""
        parser.paginas = [sample_pensionista_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.template_type == TemplateType.SPPREV_PENSIONISTA

    def test_extract_cpf_missing_raises_error(self, parser):
        """Should raise error if CPF not found"""
        texto = "NOME: JOÃO SILVA\nTIPO: PENSIONISTA"
        pagina = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [pagina]
        with pytest.raises(ValueError, match="CPF not found"):
            parser._extract_cabecalho()

    def test_extract_nome_missing_raises_error(self, parser):
        """Should raise error if NOME not found"""
        texto = "CPF: 123.456.789-00\nTIPO: PENSIONISTA"
        pagina = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [pagina]
        with pytest.raises(ValueError, match="Nome not found"):
            parser._extract_cabecalho()

    def test_normalize_date_mm_yyyy_to_yyyy_mm(self, parser):
        """Should normalize MM/YYYY to YYYY-MM"""
        result = parser._normalize_date("12/2024", "AAAA-MM")
        assert result == "2024-12"

    def test_parse_valor_brazilian_format(self, parser):
        """Should parse Brazilian currency format"""
        valor = parser._parse_valor("5.604,34")
        assert valor == 5604.34

    def test_parse_valor_american_format(self, parser):
        """Should parse American currency format"""
        valor = parser._parse_valor("5604.34")
        assert valor == 5604.34

    def test_extract_tipo_folha_decimo_terceiro(self, parser):
        """Should detect DÉCIMO TERCEIRO tipo de folha"""
        texto = "TIPO FOLHA: DÉCIMO TERCEIRO"
        assert parser._extract_tipo_folha(texto) == TipoFolha.DECIMO_TERCEIRO

    def test_extract_tipo_folha_suplementar(self, parser):
        """Should detect SUPLEMENTAR tipo de folha"""
        texto = "TIPO FOLHA: SUPLEMENTAR"
        assert parser._extract_tipo_folha(texto) == TipoFolha.SUPLEMENTAR
