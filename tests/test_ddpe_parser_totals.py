"""Tests for DDPE parser totals extraction"""

import pytest
from src.core.parsers.ddpe_parser import DDPEParser
from src.core.pdf_reader import PaginaExtraida


class TestDDPEParserTotals:
    """Test DDPE parser totals extraction"""

    @pytest.fixture
    def parser(self):
        """Create DDPE parser"""
        return DDPEParser()

    @pytest.fixture
    def sample_totals_page(self):
        """Sample DDPE page with totals section"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: JOÃO SILVA SANTOS

        CÓDIGO DENOMINAÇÃO VALOR
        01.001 SALÁRIO 5000.00
        01.002 ADIANTAMENTO 1000.00
        70.006 IAMSPE -100.00

        TOTAL VENCIMENTOS 6000.00
        TOTAL DESCONTOS 100.00
        LÍQUIDO 5900.00
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_extract_totals_basic(self, parser, sample_totals_page):
        """Should extract total vencimentos, descontos, and liquido"""
        parser.paginas = [sample_totals_page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert isinstance(vencimentos, (int, float))
        assert isinstance(descontos, (int, float))
        assert isinstance(liquido, (int, float))
        assert vencimentos > 0
        assert descontos >= 0

    def test_extract_totals_values(self, parser, sample_totals_page):
        """Should extract correct total values"""
        parser.paginas = [sample_totals_page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 6000.00
        assert descontos == 100.00
        assert liquido == 5900.00

    def test_extract_totals_reconciliation(self, parser, sample_totals_page):
        """Should validate Líquido = Vencimentos - Descontos"""
        parser.paginas = [sample_totals_page]
        vencimentos, descontos, liquido = parser._extract_totals()

        expected_liquido = vencimentos - descontos
        assert abs(liquido - expected_liquido) < 0.01  # Allow tolerance of 0.01

    def test_extract_totals_brazilian_format(self, parser):
        """Should handle Brazilian monetary format (1.000,00)"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        TOTAL VENCIMENTOS 6.000,00
        TOTAL DESCONTOS 100,00
        LÍQUIDO 5.900,00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 6000.00
        assert descontos == 100.00
        assert liquido == 5900.00

    def test_extract_totals_zero_descontos(self, parser):
        """Should handle zero descontos"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        TOTAL VENCIMENTOS 5000.00
        TOTAL DESCONTOS 0.00
        LÍQUIDO 5000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert descontos == 0.00
        assert liquido == vencimentos

    def test_extract_totals_missing_section(self, parser):
        """Should return zeros if no totals found"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert isinstance(vencimentos, (int, float))
        assert isinstance(descontos, (int, float))
        assert isinstance(liquido, (int, float))

    def test_extract_totals_case_insensitive(self, parser):
        """Should be case insensitive"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        total vencimentos 5000.00
        TOTAL DESCONTOS 100.00
        líquido 4900.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 5000.00
        assert descontos == 100.00
        assert liquido == 4900.00
