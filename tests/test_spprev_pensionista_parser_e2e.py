"""End-to-end tests for SPPREV Pensionista parser with real PDF data"""

import pytest
from src.core.parsers.spprev_pensionista_parser import SpprevPensionistaParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import TemplateType, TipoFolha


class TestSpprevPensionistaParserE2E:
    """End-to-end tests with realistic SPPREV Pensionista holerite data"""

    @pytest.fixture
    def parser(self):
        """Create SPPREV Pensionista parser"""
        return SpprevPensionistaParser()

    @pytest.fixture
    def realistic_pensionista_holerite(self):
        """Realistic SPPREV Pensionista holerite (Maria Ines - real data)"""
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

    def test_parse_complete_holerite(self, parser, realistic_pensionista_holerite):
        """Should parse complete holerite successfully"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite is not None
        assert holerite.cabecalho is not None
        assert holerite.verbas is not None
        assert len(holerite.verbas) > 0

    def test_parse_extracts_correct_nome(self, parser, realistic_pensionista_holerite):
        """Should extract correct nome"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert "MARIA" in holerite.cabecalho.nome.upper()
        assert "INES" in holerite.cabecalho.nome.upper()

    def test_parse_extracts_correct_cpf(self, parser, realistic_pensionista_holerite):
        """Should extract correct CPF"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.cpf == "026.188.918-48"

    def test_parse_extracts_competencia(self, parser, realistic_pensionista_holerite):
        """Should extract competencia"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.competencia == "2024-12"

    def test_parse_extracts_template_type(self, parser, realistic_pensionista_holerite):
        """Should set correct template type"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.template_type == TemplateType.SPPREV_PENSIONISTA

    def test_parse_extracts_tipo_folha(self, parser, realistic_pensionista_holerite):
        """Should extract tipo de folha"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.tipo_folha == TipoFolha.NORMAL

    def test_parse_extracts_verbas_from_both_sections(self, parser, realistic_pensionista_holerite):
        """Should extract verbas from both sections"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        # Should have at least 3 verbas (1 from BASE + 2 from DEMONSTRATIVO)
        assert len(holerite.verbas) >= 3

    def test_parse_extracts_totals_vencimentos(self, parser, realistic_pensionista_holerite):
        """Should extract TOTAL VENCIMENTOS from DEMONSTRATIVO"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.total_vencimentos == 5604.34

    def test_parse_extracts_totals_descontos(self, parser, realistic_pensionista_holerite):
        """Should extract TOTAL DESCONTOS from DEMONSTRATIVO"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.total_descontos == 173.61

    def test_parse_extracts_totals_liquido(self, parser, realistic_pensionista_holerite):
        """Should extract TOTAL LÍQUIDO from DEMONSTRATIVO"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.liquido == 5430.73

    def test_parse_multipage_pensionista(self, parser):
        """Should handle multipage SPPREV Pensionista holerites"""
        page1 = PaginaExtraida(numero=1, texto="""
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DEMONSTRATIVO DE PAGAMENTO
        PENSÃO POR MORTE

        Nome CPF
        MARIA INES MARQUES DE ALMEIDA 026.188.918-48

        BASE DE CÁLCULO DO BENEFÍCIO
        Código Denominação Vencimentos Descontos
        001031 BENEFÍCIO PREVIDENCIÁRIO 5.604,34
        """, metodo="TEXTO", confianca=0.95)

        page2 = PaginaExtraida(numero=2, texto="""
        SÃO PAULO PREVIDÊNCIA - SPPREV

        DEMONSTRATIVO DO PAGAMENTO DO BENEFÍCIO
        Código Denominação Período Vencimentos Descontos
        018601 PENSAO MENSAL-C 12/2024 5.604,34
        070012 IMPOSTO DE RENDA-D 12/2024 173,61
        Total Vencimentos Total Descontos Líquido a Receber
        5.604,34 173,61 5.430,73
        """, metodo="TEXTO", confianca=0.95)

        pages = [page1, page2]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.nome is not None
        assert holerite.total_vencimentos == 5604.34
        assert holerite.total_descontos == 173.61
        assert holerite.liquido == 5430.73

    def test_parse_validates_holerite(self, parser, realistic_pensionista_holerite):
        """Should validate extracted holerite data"""
        pages = [realistic_pensionista_holerite]
        # Should not raise validation error
        holerite = parser.parse(pages)
        assert holerite is not None

    def test_parse_metodo_extracao_preserved(self, parser, realistic_pensionista_holerite):
        """Should preserve extraction method"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.metodo_extracao == "TEXTO"

    def test_parse_confianca_preserved(self, parser, realistic_pensionista_holerite):
        """Should preserve confidence value"""
        pages = [realistic_pensionista_holerite]
        holerite = parser.parse(pages)

        assert holerite.confianca == 0.95
