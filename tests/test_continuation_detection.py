"""Tests for continuation page detection"""

import pytest
from src.core.pdf_reader import PDFReader


class TestContinuationDetection:
    """Test detection of continuation pages (page 2+)"""

    def test_is_continuation_page_exists(self):
        """is_continuation_page method should exist"""
        assert hasattr(PDFReader, "is_continuation_page")
        assert callable(getattr(PDFReader, "is_continuation_page"))

    def test_not_continuation_with_cpf(self):
        """Page with CPF field is not continuation"""
        texto = """
        DEPARTAMENTO DE DESPESA
        NOME: LUCIANO BASTOS
        CPF: 123.456.789-00
        COMPETÊNCIA: 03/2021
        """
        assert PDFReader.is_continuation_page(texto) is False

    def test_not_continuation_with_competencia(self):
        """Page with COMPETÊNCIA field is not continuation"""
        texto = """
        HOLERITE DE PAGAMENTO
        NOME: JOÃO SILVA
        COMPETÊNCIA: 05/2021
        CÓDIGO    DENOMINAÇÃO    VALOR
        """
        assert PDFReader.is_continuation_page(texto) is False

    def test_not_continuation_empty_text(self):
        """Empty text is not continuation"""
        assert PDFReader.is_continuation_page("") is False
        assert PDFReader.is_continuation_page("   ") is False

    def test_not_continuation_too_short(self):
        """Too short text is not continuation"""
        assert PDFReader.is_continuation_page("abc") is False

    def test_continuation_with_verba_no_header(self):
        """Page with verba table but no header is continuation"""
        texto = """
        CÓDIGO    DENOMINAÇÃO         VALOR
        70.006    IAMSPE              1.000,00
        70.007    IAMSPE ADICIONAL      500,00
        01.001    SALÁRIO BASE        5.000,00
        """
        assert PDFReader.is_continuation_page(texto) is True

    def test_continuation_codigo_pattern(self):
        """Page with código field but no header is continuation"""
        texto = """
        Código    Denominação         Valor
        70.006    IAMSPE              1.000,00
        70.007    IAMSPE ADICIONAL      500,00
        """
        assert PDFReader.is_continuation_page(texto) is True

    def test_not_continuation_both_header_and_verba(self):
        """Page with both header and verba table is first page, not continuation"""
        texto = """
        CPF: 123.456.789-00
        COMPETÊNCIA: 03/2021

        CÓDIGO    DENOMINAÇÃO         VALOR
        70.006    IAMSPE              1.000,00
        """
        assert PDFReader.is_continuation_page(texto) is False

    def test_continuation_verba_without_header_fields(self):
        """Verba table without CPF/COMPETÊNCIA is continuation"""
        texto = """
        CÓDIGO        VALOR
        70.006        1.000,00
        70.007          500,00
        01.001        5.000,00
        """
        assert PDFReader.is_continuation_page(texto) is True

    def test_case_insensitive_detection(self):
        """Detection should be case insensitive"""
        texto_upper = "CÓDIGO DENOMINAÇÃO VERBA"
        texto_lower = "código denominação verba"

        assert PDFReader.is_continuation_page(texto_upper) is True
        assert PDFReader.is_continuation_page(texto_lower) is True

    def test_continuation_with_real_pattern(self):
        """Test with pattern similar to real holerite continuation"""
        texto = """
        VERBAS:
        CÓDIGO    DENOMINAÇÃO              NATUREZA    VALOR
        70.006    IAMSPE                        N      1.000,00
        70.007    IAMSPE - LEI 17.293        N        500,00
        70.119    INSS ATIVO                  N        250,00

        TOTAIS:
        TOTAL VENCIMENTOS:        1.750,00
        TOTAL DESCONTOS:            250,00
        """
        assert PDFReader.is_continuation_page(texto) is True

    def test_not_continuation_missing_verba_indicators(self):
        """Page without verba indicators is not continuation even if no header"""
        texto = """
        Some random text
        Without any earnings or header fields
        Just some generic content here
        """
        assert PDFReader.is_continuation_page(texto) is False
