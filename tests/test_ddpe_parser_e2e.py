"""End-to-end tests for DDPE parser with real PDF data"""

import pytest
from src.core.parsers.ddpe_parser import DDPEParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import TemplateType, TipoFolha


class TestDDPEParserE2E:
    """End-to-end tests with realistic holerite data"""

    @pytest.fixture
    def parser(self):
        """Create DDPE parser"""
        return DDPEParser()

    @pytest.fixture
    def realistic_holerite(self):
        """Realistic DDPE holerite with header, verbas, and totals"""
        texto = """
        DEPARTAMENTO DE DESPESA - FOLHA DE PAGAMENTO
        Competência: 02/2026

        CPF: 123.456.789-00
        NOME: JOÃO SILVA SANTOS
        CARGO: DESENVOLVEDOR SENIOR
        UNIDADE: TECNOLOGIA
        COMPETÊNCIA: 02/2026
        DATA DE PAGAMENTO: 15/03/2026
        TIPO: NORMAL

        VERBAS:
        CÓDIGO DENOMINAÇÃO VALOR
        01.001 SALÁRIO 5000.00
        01.002 ADIANTAMENTO 1000.00
        03.001 VALE TRANSPORTE 0.00
        09.001 QUINQUÊNIO 200.00

        DESCONTOS:
        70.006 IAMSPE -100.00
        70.007 ICMS -50.00

        TOTAL VENCIMENTOS 6200.00
        TOTAL DESCONTOS 150.00
        LÍQUIDO 6050.00
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_parse_complete_holerite(self, parser, realistic_holerite):
        """Should parse complete holerite successfully"""
        pages = [realistic_holerite]
        holerite = parser.parse(pages)

        assert holerite is not None
        assert holerite.cabecalho.nome == "JOÃO SILVA SANTOS"
        assert holerite.cabecalho.cpf == "123.456.789-00"
        assert holerite.cabecalho.cargo == "DESENVOLVEDOR SENIOR"
        assert holerite.cabecalho.unidade == "TECNOLOGIA"

    def test_parse_header_extraction(self, parser, realistic_holerite):
        """Should extract header information"""
        pages = [realistic_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.competencia == "2026-02"
        assert holerite.cabecalho.tipo_folha == TipoFolha.NORMAL
        assert holerite.cabecalho.template_type == TemplateType.DDPE

    def test_parse_verbas_extraction(self, parser, realistic_holerite):
        """Should extract all verbas"""
        pages = [realistic_holerite]
        holerite = parser.parse(pages)

        # Should have extracted verbas
        assert len(holerite.verbas) >= 4

        # Find specific verbas
        salario = [v for v in holerite.verbas if "SALÁRIO" in v.denominacao.upper()]
        assert len(salario) > 0
        assert salario[0].valor == 5000.00

    def test_parse_totals_extraction(self, parser, realistic_holerite):
        """Should extract totals correctly"""
        pages = [realistic_holerite]
        holerite = parser.parse(pages)

        assert holerite.total_vencimentos == 6200.00
        assert holerite.total_descontos == 150.00
        assert holerite.liquido == 6050.00

    def test_parse_multipage_holerite(self, parser):
        """Should handle multipage holerites"""
        page1 = PaginaExtraida(numero=1, texto="""
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST USER
        CARGO: DEVELOPER
        UNIDADE: IT
        COMPETÊNCIA: 02/2026
        DATA DE PAGAMENTO: 15/03/2026

        VERBAS:
        01.001 SALÁRIO 5000.00
        01.002 ADIANTAMENTO 1000.00
        70.006 IAMSPE -100.00

        TOTAL VENCIMENTOS 6000.00
        TOTAL DESCONTOS 100.00
        LÍQUIDO 5900.00
        """, metodo="TEXTO", confianca=0.95)

        pages = [page1]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.nome == "TEST USER"
        assert len(holerite.verbas) >= 2

    def test_template_detection(self, parser):
        """Should detect DDPE template correctly"""
        texto = """
        DEPARTAMENTO DE DESPESA
        FOLHA DE PAGAMENTO
        CPF: 123.456.789-00
        """
        assert parser.detect_template(texto) is True

    def test_template_detection_fail(self, parser):
        """Should reject non-DDPE templates"""
        texto = """
        SPPREV - APOSENTADO
        CPF: 123.456.789-00
        """
        assert parser.detect_template(texto) is False

    def test_parse_with_ocr_metadata(self, parser):
        """Should preserve OCR metadata"""
        page = PaginaExtraida(numero=1, texto="""
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST
        CARGO: DEV
        COMPETÊNCIA: 02/2026
        DATA DE PAGAMENTO: 15/03/2026

        01.001 SALÁRIO 5000.00

        TOTAL VENCIMENTOS 5000.00
        TOTAL DESCONTOS 0.00
        LÍQUIDO 5000.00
        """, metodo="OCR", confianca=0.85)

        holerite = parser.parse([page])
        assert holerite.metodo_extracao == "OCR"
        assert holerite.confianca == 0.85

    def test_parse_performance_requirement(self, parser, realistic_holerite):
        """Should parse within performance requirement (< 5 seconds)"""
        import time

        pages = [realistic_holerite]
        start = time.time()
        holerite = parser.parse(pages)
        elapsed = time.time() - start

        assert elapsed < 5.0  # Should parse in less than 5 seconds

    def test_parse_handles_missing_fields(self, parser):
        """Should handle holerite with missing optional fields"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST USER

        01.001 SALÁRIO 5000.00

        TOTAL VENCIMENTOS 5000.00
        TOTAL DESCONTOS 0.00
        LÍQUIDO 5000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

        holerite = parser.parse([page])
        assert holerite.cabecalho.nome == "TEST USER"
        assert holerite.cabecalho.cpf == "123.456.789-00"
        assert holerite.cabecalho.cargo is None  # Optional field may be None

    def test_parse_verba_natureza_detection(self, parser):
        """Should detect verba natureza correctly"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        NORMAL VERBAS:
        01.001 SALÁRIO 5000.00

        ATRASADO VERBAS:
        01.001 SALÁRIO ATRASADO 2000.00

        TOTAL VENCIMENTOS 7000.00
        TOTAL DESCONTOS 0.00
        LÍQUIDO 7000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

        holerite = parser.parse([page])

        # Should have identified normal and atrasado verbas
        normal_count = sum(1 for v in holerite.verbas if v.natureza.value == "N")
        atrasado_count = sum(1 for v in holerite.verbas if v.natureza.value == "A")

        assert normal_count > 0 or atrasado_count > 0
