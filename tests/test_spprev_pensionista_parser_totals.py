"""Tests for SPPREV Pensionista parser totals extraction"""

import pytest
from src.core.parsers.spprev_pensionista_parser import SpprevPensionistaParser
from src.core.pdf_reader import PaginaExtraida


class TestSpprevPensionistaParserTotals:
    """Test SPPREV Pensionista parser totals extraction"""

    @pytest.fixture
    def parser(self):
        """Create SPPREV Pensionista parser"""
        return SpprevPensionistaParser()

    @pytest.fixture
    def pensionista_with_totals(self):
        """SPPREV Pensionista with totals"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DEMONSTRATIVO DE PAGAMENTO

        BASE DE CÁLCULO DO BENEFÍCIO Total Vencimentos Total Descontos Base p / Cálculo
        5.604,34 0,00 5.604,34
        Código Denominação Vencimentos Descontos
        001031 BENEFÍCIO PREVIDENCIÁRIO LC 1.354/2020 5.604,34
        Total Vencimentos Total Descontos Líquido a Receber
        5.604,34 0,00 5.604,34

        DEMONSTRATIVO DO PAGAMENTO DO BENEFÍCIO
        Código Denominação Período Vencimentos Descontos
        018601 PENSAO MENSAL-C 12/2024 5.604,34
        070012 IMPOSTO DE RENDA-D 12/2024 173,61
        Total Vencimentos Total Descontos Líquido a Receber
        5.604,34 173,61 5.430,73
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_extract_vencimentos_from_demonstrativo(self, parser, pensionista_with_totals):
        """Should extract Total Vencimentos from DEMONSTRATIVO section"""
        parser.paginas = [pensionista_with_totals]
        vencimentos, descontos, liquido = parser._extract_totals()
        assert vencimentos == 5604.34

    def test_extract_descontos_from_demonstrativo(self, parser, pensionista_with_totals):
        """Should extract Total Descontos from DEMONSTRATIVO section"""
        parser.paginas = [pensionista_with_totals]
        vencimentos, descontos, liquido = parser._extract_totals()
        assert descontos == 173.61

    def test_extract_liquido_from_demonstrativo(self, parser, pensionista_with_totals):
        """Should extract Líquido from DEMONSTRATIVO section"""
        parser.paginas = [pensionista_with_totals]
        vencimentos, descontos, liquido = parser._extract_totals()
        assert liquido == 5430.73

    def test_extract_totals_validates_formula(self, parser, pensionista_with_totals):
        """Should validate liquido = vencimentos - descontos"""
        parser.paginas = [pensionista_with_totals]
        vencimentos, descontos, liquido = parser._extract_totals()

        expected_liquido = vencimentos - descontos
        assert abs(liquido - expected_liquido) < 0.01

    def test_extract_totals_with_zero_descontos(self, parser):
        """Should handle zero descontos"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV

        DEMONSTRATIVO DO PAGAMENTO DO BENEFÍCIO
        Total Vencimentos Total Descontos Líquido a Receber
        5.000,00 0,00 5.000,00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 5000.00
        assert descontos == 0.00
        assert liquido == 5000.00

    def test_extract_totals_multipage(self, parser):
        """Should extract totals from last page in multipage"""
        page1 = PaginaExtraida(numero=1, texto="""
        SÃO PAULO PREVIDÊNCIA - SPPREV
        PENSÃO POR MORTE

        BASE DE CÁLCULO DO BENEFÍCIO
        001031 BENEFÍCIO 5.000,00
        """, metodo="TEXTO", confianca=0.95)

        page2 = PaginaExtraida(numero=2, texto="""
        SÃO PAULO PREVIDÊNCIA - SPPREV

        DEMONSTRATIVO DO PAGAMENTO DO BENEFÍCIO
        Total Vencimentos Total Descontos Líquido a Receber
        5.000,00 500,00 4.500,00
        """, metodo="TEXTO", confianca=0.95)

        parser.paginas = [page1, page2]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 5000.00
        assert descontos == 500.00
        assert liquido == 4500.00

    def test_parse_valor_in_totals(self, parser):
        """Should parse monetary values in totals"""
        valor1 = parser._parse_valor("5.604,34")
        assert valor1 == 5604.34

        valor2 = parser._parse_valor("173,61")
        assert valor2 == 173.61

        valor3 = parser._parse_valor("5.430,73")
        assert valor3 == 5430.73
