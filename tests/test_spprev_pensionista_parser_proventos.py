"""Tests for SPPREV Pensionista parser verbas extraction (2 sections)"""

import pytest
from src.core.parsers.spprev_pensionista_parser import SpprevPensionistaParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import NaturezaVerba


class TestSpprevPensionistaParserProventos:
    """Test SPPREV Pensionista parser verbas extraction"""

    @pytest.fixture
    def parser(self):
        """Create SPPREV Pensionista parser"""
        return SpprevPensionistaParser()

    @pytest.fixture
    def pensionista_with_verbas(self):
        """SPPREV Pensionista with both sections"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DEMONSTRATIVO DE PAGAMENTO

        MARIA INES MARQUES DE ALMEIDA 026.188.918-48

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

    def test_extract_verbas_from_both_sections(self, parser, pensionista_with_verbas):
        """Should extract verbas from both BASE and DEMONSTRATIVO sections"""
        parser.paginas = [pensionista_with_verbas]
        verbas = parser._extract_verbas()
        # Should have at least 3 verbas (1 from BASE + 2 from DEMONSTRATIVO)
        assert len(verbas) >= 3

    def test_extract_verba_from_base_calculo(self, parser, pensionista_with_verbas):
        """Should extract verba from BASE DE CÁLCULO section"""
        parser.paginas = [pensionista_with_verbas]
        verbas = parser._extract_verbas()

        # Find verba from base section
        beneficio_verb = [v for v in verbas if "PREVIDENCI" in v.denominacao.upper()]
        assert len(beneficio_verb) > 0
        assert beneficio_verb[0].valor == 5604.34

    def test_extract_verba_from_demonstrativo(self, parser, pensionista_with_verbas):
        """Should extract verba from DEMONSTRATIVO section"""
        parser.paginas = [pensionista_with_verbas]
        verbas = parser._extract_verbas()

        # Find verba from demonstrativo section
        pensao_verb = [v for v in verbas if "PENSAO" in v.denominacao.upper()]
        assert len(pensao_verb) > 0

    def test_detect_credito_marker(self, parser, pensionista_with_verbas):
        """Should detect -C (Crédito) marker in denominação"""
        parser.paginas = [pensionista_with_verbas]
        verbas = parser._extract_verbas()

        # Find verba with -C marker
        credito_verb = [v for v in verbas if v.natureza == NaturezaVerba.CREDITO]
        assert len(credito_verb) > 0

    def test_detect_debito_marker(self, parser, pensionista_with_verbas):
        """Should detect -D (Débito) marker in denominação"""
        parser.paginas = [pensionista_with_verbas]
        verbas = parser._extract_verbas()

        # Find verba with -D marker
        debito_verb = [v for v in verbas if v.natureza == NaturezaVerba.DEBITO]
        assert len(debito_verb) > 0

    def test_verba_denominacao_without_marker(self, parser, pensionista_with_verbas):
        """Should remove -C or -D marker from denominação"""
        parser.paginas = [pensionista_with_verbas]
        verbas = parser._extract_verbas()

        # Check that denominação doesn't contain markers
        for v in verbas:
            assert not v.denominacao.endswith("-C")
            assert not v.denominacao.endswith("-D")

    def test_verba_valor_extraction(self, parser, pensionista_with_verbas):
        """Should extract monetary values correctly"""
        parser.paginas = [pensionista_with_verbas]
        verbas = parser._extract_verbas()

        # Check values are extracted
        # Vencimentos (001xxx) are positive; descontos (070xxx+) are negative
        assert any(v.valor == 5604.34 for v in verbas)
        assert any(v.valor == -173.61 for v in verbas)

    def test_verba_codigo_extraction(self, parser, pensionista_with_verbas):
        """Should extract 6-digit codigo"""
        parser.paginas = [pensionista_with_verbas]
        verbas = parser._extract_verbas()

        # Check all verbas have 6-digit código
        for v in verbas:
            assert len(v.codigo) == 6
            assert v.codigo.isdigit()

    def test_section_separation(self, parser):
        """Should correctly separate BASE and DEMONSTRATIVO sections"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV

        BASE DE CÁLCULO DO BENEFÍCIO
        Código Denominação Vencimentos Descontos
        001001 SALARIO 1000.00

        DEMONSTRATIVO DO PAGAMENTO DO BENEFÍCIO
        Código Denominação Período Vencimentos Descontos
        018601 PENSAO-C 01/2025 1000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        verbas = parser._extract_verbas()

        # Should have 2 verbas (one from each section)
        assert len(verbas) == 2
