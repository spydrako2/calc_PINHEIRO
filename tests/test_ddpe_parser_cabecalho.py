"""Tests for DDPE parser header extraction"""

import pytest
from src.core.parsers.ddpe_parser import DDPEParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import TipoFolha


class TestDDPEParserCabecalho:
    """Test DDPE parser header extraction"""

    @pytest.fixture
    def parser(self):
        """Create DDPE parser"""
        return DDPEParser()

    @pytest.fixture
    def sample_ddpe_page(self):
        """Sample DDPE holerite page"""
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
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_detect_template_ddpe(self, parser):
        """Should detect DDPE template"""
        texto = "DEPARTAMENTO DE DESPESA\nFOLHA DE PAGAMENTO"
        assert parser.detect_template(texto) is True

    def test_detect_template_ddpe_keyword(self, parser):
        """Should detect DDPE by keyword"""
        texto = "DDPE - SISTEMA DE FOLHA"
        assert parser.detect_template(texto) is True

    def test_detect_template_not_ddpe(self, parser):
        """Should not detect non-DDPE templates"""
        texto = "SPPREV - APOSENTADO\nCOMPETÊNCIA: 02/2026"
        assert parser.detect_template(texto) is False

    def test_extract_cpf_valid(self, parser, sample_ddpe_page):
        """Should extract valid CPF"""
        parser.paginas = [sample_ddpe_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.cpf == "123.456.789-00"

    def test_extract_nome(self, parser, sample_ddpe_page):
        """Should extract name"""
        parser.paginas = [sample_ddpe_page]
        cabecalho = parser._extract_cabecalho()
        assert "JOÃO" in cabecalho.nome.upper()
        assert "SILVA" in cabecalho.nome.upper()

    def test_extract_cargo(self, parser, sample_ddpe_page):
        """Should extract cargo"""
        parser.paginas = [sample_ddpe_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.cargo is not None
        assert "DESENVOLVEDOR" in cabecalho.cargo.upper()

    def test_extract_unidade(self, parser, sample_ddpe_page):
        """Should extract unidade"""
        parser.paginas = [sample_ddpe_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.unidade is not None
        assert "TECNOLOGIA" in cabecalho.unidade.upper()

    def test_extract_competencia_normal_format(self, parser, sample_ddpe_page):
        """Should extract and normalize competencia"""
        parser.paginas = [sample_ddpe_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.competencia == "2026-02"

    def test_extract_data_pagamento(self, parser, sample_ddpe_page):
        """Should extract data de pagamento"""
        parser.paginas = [sample_ddpe_page]
        cabecalho = parser._extract_cabecalho()
        assert cabecalho.data_pagamento is not None
        assert "15" in cabecalho.data_pagamento
        assert "03" in cabecalho.data_pagamento

    def test_extract_tipo_folha_normal(self, parser):
        """Should detect NORMAL tipo de folha"""
        texto = "NORMAL FOLHA"
        assert parser._extract_tipo_folha(texto) == TipoFolha.NORMAL

    def test_extract_tipo_folha_decimo_terceiro(self, parser):
        """Should detect DÉCIMO TERCEIRO tipo de folha"""
        texto = "DÉCIMO TERCEIRO 13º SALÁRIO"
        assert parser._extract_tipo_folha(texto) == TipoFolha.DECIMO_TERCEIRO

    def test_extract_tipo_folha_suplementar(self, parser):
        """Should detect SUPLEMENTAR tipo de folha"""
        texto = "FOLHA SUPLEMENTAR"
        assert parser._extract_tipo_folha(texto) == TipoFolha.SUPLEMENTAR

    def test_normalize_date_mm_aaaa_to_aaaa_mm(self, parser):
        """Should normalize MM/AAAA to AAAA-MM"""
        result = parser._normalize_date("02/2026", "AAAA-MM")
        assert result == "2026-02"

    def test_normalize_date_already_normalized(self, parser):
        """Should recognize already normalized dates"""
        result = parser._normalize_date("2026-02", "AAAA-MM")
        assert result == "2026-02"

    def test_extract_cpf_missing_raises_error(self, parser):
        """Should raise error if CPF not found"""
        texto = "NOME: JOÃO SILVA\nCARGO: DEV"
        pagina = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [pagina]

        with pytest.raises(ValueError, match="CPF not found"):
            parser._extract_cabecalho()

    def test_extract_nome_missing_raises_error(self, parser):
        """Should raise error if NOME not found"""
        texto = "CPF: 123.456.789-00\nCARGO: DEV"
        pagina = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        parser.paginas = [pagina]

        with pytest.raises(ValueError, match="Nome not found"):
            parser._extract_cabecalho()
