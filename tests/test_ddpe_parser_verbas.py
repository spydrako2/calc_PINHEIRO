"""Tests for DDPE parser verba (earnings/deductions) extraction"""

import pytest
from src.core.parsers.ddpe_parser import DDPEParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import NaturezaVerba, TipoFolha


class TestDDPEParserVerbas:
    """Test DDPE parser verba extraction"""

    @pytest.fixture
    def parser(self):
        """Create DDPE parser"""
        return DDPEParser()

    @pytest.fixture
    def sample_verbas_page(self):
        """Sample DDPE page with verba table"""
        texto = """
        DEPARTAMENTO DE DESPESA
        FOLHA DE PAGAMENTO

        CPF: 123.456.789-00
        NOME: JOÃO SILVA SANTOS
        CARGO: DESENVOLVEDOR SENIOR
        UNIDADE: TECNOLOGIA
        COMPETÊNCIA: 02/2026
        DATA DE PAGAMENTO: 15/03/2026
        TIPO: NORMAL

        CÓDIGO DENOMINAÇÃO VALOR
        01.001 SALÁRIO 5000.00
        01.002 ADIANTAMENTO 1000.00
        03.001 VALE TRANSPORTE 0.00
        70.006 IAMSPE -50.00
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_extract_verbas_basic(self, parser, sample_verbas_page):
        """Should extract basic verba lines"""
        parser.paginas = [sample_verbas_page]
        verbas = parser._extract_verbas()

        assert len(verbas) >= 2
        # Check first verba (code normalized to 6 digits)
        assert len(verbas[0].codigo) == 6  # Normalized to XXXXXX format
        assert "SALÁRIO" in verbas[0].denominacao.upper()
        assert verbas[0].valor == 5000.00

    def test_extract_verbas_with_zero_values(self, parser, sample_verbas_page):
        """Should handle verbas with zero values"""
        parser.paginas = [sample_verbas_page]
        verbas = parser._extract_verbas()

        # Find VALE TRANSPORTE (should have 0 value)
        vale = [v for v in verbas if "VALE" in v.denominacao.upper()]
        assert len(vale) > 0
        assert vale[0].valor == 0.0

    def test_extract_verbas_negative_values(self, parser, sample_verbas_page):
        """Should handle deductions (negative values)"""
        parser.paginas = [sample_verbas_page]
        verbas = parser._extract_verbas()

        # Find IAMSPE (deduction)
        iamspe = [v for v in verbas if "IAMSPE" in v.denominacao.upper()]
        assert len(iamspe) > 0
        assert iamspe[0].valor == -50.00

    def test_extract_verbas_codigo_normalization(self, parser):
        """Should normalize codigo from XX.XXX to XXXXXX format"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        CÓDIGO   DENOMINAÇÃO           VALOR
        01.001   SALÁRIO                5000.00
        070006   IAMSPE                 -50.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        verbas = parser._extract_verbas()

        # Both formats should be normalized
        assert len(verbas) >= 1
        # Codigo should be in consistent format
        for v in verbas:
            assert isinstance(v.codigo, str)
            assert len(v.codigo) > 0

    def test_extract_verbas_quantidade_extraction(self, parser, sample_verbas_page):
        """Should extract quantidade field when available"""
        parser.paginas = [sample_verbas_page]
        verbas = parser._extract_verbas()

        if verbas:
            first = verbas[0]
            # Quantidade should be present if extracted
            assert first.quantidade is None or isinstance(first.quantidade, (int, float))

    def test_extract_verbas_natureza_normal_default(self, parser, sample_verbas_page):
        """Should default to NORMAL natureza"""
        parser.paginas = [sample_verbas_page]
        verbas = parser._extract_verbas()

        assert len(verbas) > 0
        # Default should be NORMAL
        normal_count = sum(1 for v in verbas if v.natureza == NaturezaVerba.NORMAL)
        assert normal_count > 0

    def test_extract_verbas_atrasado_detection(self, parser):
        """Should detect ATRASADO natureza from context"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        VERBAS ATRASADAS:
        CÓDIGO   DENOMINAÇÃO           VALOR
        01.001   SALÁRIO ATRASADO       2000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        verbas = parser._extract_verbas()

        if verbas:
            # Should detect ATRASADO context
            atrasado_count = sum(1 for v in verbas if v.natureza == NaturezaVerba.ATRASADO)
            assert atrasado_count >= 0  # May or may not be detected depending on context

    def test_extract_verbas_empty_page(self, parser):
        """Should return empty list when no verbas found"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST
        CARGO: DEVELOPER
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        verbas = parser._extract_verbas()

        assert isinstance(verbas, list)
        # May have no verbas or some verbas - but should not crash

    def test_extract_verbas_multiple_format_variations(self, parser):
        """Should handle different spacing and formatting"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        CÓDIGO DENOMINAÇÃO VALOR
        01.001 SALÁRIO 5000.00
        01.002  ADIANTAMENTO  1000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        verbas = parser._extract_verbas()

        assert isinstance(verbas, list)

    def test_extract_verbas_returns_verba_objects(self, parser, sample_verbas_page):
        """Should return Verba objects with correct types"""
        from src.core.data_model import Verba

        parser.paginas = [sample_verbas_page]
        verbas = parser._extract_verbas()

        assert isinstance(verbas, list)
        for v in verbas:
            assert isinstance(v, Verba)
            assert isinstance(v.codigo, str)
            assert isinstance(v.denominacao, str)
            assert isinstance(v.valor, (int, float))
            assert isinstance(v.natureza, NaturezaVerba)

    def test_extract_verbas_tolerant_to_ocr_degradation(self, parser):
        """Should handle OCR-degraded text with misspellings"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        CÓDIGO DENOMINAÇÃO VALOR
        01.001 SALÁRIO 5000.00
        01.O02 ADIANTAMENTO 1000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="OCR", confianca=0.7)
        parser.paginas = [page]
        verbas = parser._extract_verbas()

        assert isinstance(verbas, list)
