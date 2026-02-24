"""Tests for SPPREV Aposentado parser verbas/proventos extraction"""

import pytest
from src.core.parsers.spprev_aposentado_parser import SpprevAposentadoParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import NaturezaVerba


class TestSpprevAposentadoParserProventos:
    """Test SPPREV Aposentado parser verbas extraction"""

    @pytest.fixture
    def parser(self):
        """Create SPPREV Aposentado parser"""
        return SpprevAposentadoParser()

    @pytest.fixture
    def holerite_with_verbas(self):
        """SPPREV holerite with multiple verbas"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES
        DEMONSTRATIVO DE PAGAMENTO

        NOME C.P.F
        Fernando Pedroso Rocha 111.528.728-18

        Código Denominação NAT QTD Unidade Período Vencimento Descontos
        001001 SALARIO BASE N 11/2025 2.685,68
        004001 RETP-REGIME ESPECIAL N 11/2025 2.685,68
        TRAB.POLICIAL
        008473 ADIC. S/INTEGRAIS - RES. CC 138/12- N 11/2025 196,42
        AJ.
        009001 ADICIONAL TEMPO DE SERVICO N 5 11/2025 1.342,84
        010001 SEXTA-PARTE N 11/2025 1.151,77
        010009 SEXTA-PARTE S/ADIC. N 11/2025 130,95
        INSALUBRIDADE
        012005 ADIC.INSALUBRIDADE INATIVO(40%)- N 60 11/2025 785,67
        EFP
        070012 IMPOSTO DE RENDA N 11/2025 1.393,52
        070113 CONTR.PREVID.RPPS-LC 1354/2020 N 11/2025 131,46
        097293 BANCO SANTANDER BRASIL S/A N 11/2025 1.270,53

        BASE IR BASE REDUTOR BASE CONTRIB PREV TOTAL VENCTOS TOTAL DE DESCONTOS TOTAL LÍQUIDO
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_extract_single_verba(self, parser, holerite_with_verbas):
        """Should extract single verba line"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()
        assert len(verbas) > 0

    def test_extract_multiple_verbas(self, parser, holerite_with_verbas):
        """Should extract all verbas from section"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()
        # Should extract at least the major verbas
        assert len(verbas) >= 8

    def test_verba_codigo_format_6digits(self, parser, holerite_with_verbas):
        """Should extract 6-digit código (SPPREV format)"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()

        # Find specific verba
        salario = [v for v in verbas if "SALARIO" in v.denominacao.upper()]
        assert len(salario) > 0
        assert salario[0].codigo == "001001"

    def test_verba_codigo_different_codes(self, parser, holerite_with_verbas):
        """Should correctly distinguish between different códigos"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()

        # Check we have different códigos
        codigos = set(v.codigo for v in verbas)
        assert "001001" in codigos
        assert "070012" in codigos
        assert "097293" in codigos

    def test_verba_denominacao_extraction(self, parser, holerite_with_verbas):
        """Should extract denominação correctly"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()

        salario = [v for v in verbas if v.codigo == "001001"]
        assert len(salario) > 0
        assert "SALARIO" in salario[0].denominacao.upper()

    def test_verba_natureza_normal(self, parser, holerite_with_verbas):
        """Should detect NORMAL natureza (N)"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()

        # Most verbas are NORMAL
        normal_verbas = [v for v in verbas if v.natureza == NaturezaVerba.NORMAL]
        assert len(normal_verbas) > 0

    def test_verba_valor_extraction_vencimento(self, parser, holerite_with_verbas):
        """Should extract vencimento (positive) values"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()

        salario = [v for v in verbas if v.codigo == "001001"]
        assert len(salario) > 0
        assert salario[0].valor == 2685.68

    def test_verba_valor_extraction_multiple(self, parser, holerite_with_verbas):
        """Should extract different valor amounts correctly"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()

        # Verify multiple different values are extracted
        valores = set(round(v.valor, 2) for v in verbas)
        assert len(valores) > 3  # Should have at least 4 different values

    def test_verba_no_descontos_column(self, parser):
        """Should handle verbas with only Vencimento (no Descontos column)"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES

        Código Denominação NAT Período Vencimento
        001001 SALARIO BASE N 11/2025 2.685,68
        002001 ADIANTAMENTO N 11/2025 500,00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        verbas = parser._extract_verbas()
        assert len(verbas) >= 2

    def test_multiline_denominacao(self, parser):
        """Should handle multi-line denominação"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES

        Código Denominação NAT Período Vencimento
        008473 ADIC. S/INTEGRAIS - RES. CC 138/12- N 11/2025 196,42
        AJ.
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [page]
        verbas = parser._extract_verbas()
        # Should still extract the verba
        assert any(v.codigo == "008473" for v in verbas)

    def test_verba_quantity_and_unit_not_required(self, parser, holerite_with_verbas):
        """Should handle missing QTD/Unidade gracefully"""
        parser.paginas = [holerite_with_verbas]
        verbas = parser._extract_verbas()

        # These fields may be None
        for v in verbas:
            # Should not crash - quantidade may be None
            assert v.quantidade is None or isinstance(v.quantidade, float)
