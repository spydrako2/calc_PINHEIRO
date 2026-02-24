"""Tests for SPPREV Aposentado parser totals extraction"""

import pytest
from src.core.parsers.spprev_aposentado_parser import SpprevAposentadoParser
from src.core.pdf_reader import PaginaExtraida


class TestSpprevAposentadoParserTotals:
    """Test SPPREV Aposentado parser totals extraction"""

    @pytest.fixture
    def parser(self):
        """Create SPPREV Aposentado parser"""
        return SpprevAposentadoParser()

    @pytest.fixture
    def holerite_with_totals(self):
        """SPPREV holerite with totals section"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES
        DEMONSTRATIVO DE PAGAMENTO

        NOME C.P.F
        Fernando Pedroso Rocha 111.528.728-18

        Código Denominação NAT Período Vencimento Descontos
        001001 SALARIO BASE N 11/2025 2.685,68
        070012 IMPOSTO DE RENDA N 11/2025 1.393,52

        BASE IR BASE REDUTOR BASE CONTRIB PREV TOTAL VENCTOS TOTAL DE DESCONTOS TOTAL LÍQUIDO
        8.371,81 0,00 8.979,01 8.979,01 2.795,51 6.183,50
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_extract_vencimentos_normal(self, parser, holerite_with_totals):
        """Should extract TOTAL VENCIMENTOS"""
        parser.paginas = [holerite_with_totals]
        vencimentos, descontos, liquido = parser._extract_totals()
        assert vencimentos == 8979.01

    def test_extract_descontos_normal(self, parser, holerite_with_totals):
        """Should extract TOTAL DESCONTOS"""
        parser.paginas = [holerite_with_totals]
        vencimentos, descontos, liquido = parser._extract_totals()
        assert descontos == 2795.51

    def test_extract_liquido_normal(self, parser, holerite_with_totals):
        """Should extract TOTAL LÍQUIDO"""
        parser.paginas = [holerite_with_totals]
        vencimentos, descontos, liquido = parser._extract_totals()
        assert liquido == 6183.50

    def test_extract_totals_validates_formula(self, parser, holerite_with_totals):
        """Should validate that liquido = vencimentos - descontos"""
        parser.paginas = [holerite_with_totals]
        vencimentos, descontos, liquido = parser._extract_totals()

        expected_liquido = vencimentos - descontos
        assert abs(liquido - expected_liquido) < 0.01

    def test_extract_totals_with_zero_descontos(self, parser):
        """Should handle zero descontos"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES

        TOTAL VENCIMENTOS 5.000,00
        TOTAL DESCONTOS 0,00
        TOTAL LÍQUIDO 5.000,00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 5000.00
        assert descontos == 0.00
        assert liquido == 5000.00

    def test_extract_totals_multipage_last_page(self, parser):
        """Should extract totals from last page in multipage holerite"""
        page1 = PaginaExtraida(numero=1, texto="""
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES

        Código Denominação NAT Período Vencimento
        001001 SALARIO BASE N 11/2025 2.685,68
        """, metodo="TEXTO", confianca=0.95)

        page2 = PaginaExtraida(numero=2, texto="""
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES

        TOTAL VENCIMENTOS 5.000,00
        TOTAL DESCONTOS 1.000,00
        TOTAL LÍQUIDO 4.000,00
        """, metodo="TEXTO", confianca=0.95)

        parser.paginas = [page1, page2]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 5000.00
        assert descontos == 1000.00
        assert liquido == 4000.00

    def test_extract_totals_not_found(self, parser):
        """Should return zeros if totals not found"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES

        Código Denominação NAT Período Vencimento
        001001 SALARIO BASE N 11/2025 2.685,68
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 0.0
        assert descontos == 0.0
        assert liquido == 0.0

    def test_parse_valor_in_totals_context(self, parser):
        """Should parse monetary values in totals section correctly"""
        valor1 = parser._parse_valor("8.979,01")  # Brazilian format
        assert valor1 == 8979.01

        valor2 = parser._parse_valor("2.795,51")  # Brazilian format
        assert valor2 == 2795.51

        valor3 = parser._parse_valor("6.183,50")  # Brazilian format
        assert valor3 == 6183.50

    def test_extract_totals_case_insensitive(self, parser):
        """Should handle case variations in TOTAL labels"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV

        total venctos 5.000,00
        total de descontos 1.000,00
        total líquido 4.000,00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        vencimentos, descontos, liquido = parser._extract_totals()

        assert vencimentos == 5000.00
        assert descontos == 1000.00
        assert liquido == 4000.00
