"""End-to-end tests for SPPREV Aposentado parser with real PDF data"""

import pytest
from src.core.parsers.spprev_aposentado_parser import SpprevAposentadoParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import TemplateType, TipoFolha


class TestSpprevAposentadoParserE2E:
    """End-to-end tests with realistic SPPREV Aposentado holerite data"""

    @pytest.fixture
    def parser(self):
        """Create SPPREV Aposentado parser"""
        return SpprevAposentadoParser()

    @pytest.fixture
    def realistic_spprev_holerite(self):
        """Realistic SPPREV Aposentado holerite (real structure from Fernando Pedroso)"""
        texto = """
        GOVERNO DO ESTADO DE SÃO PAULO
        SÃO PAULO PREVIDÊNCIA - SPPREV
        Data Pagamento Fls
        DIRETORIA DE BENEFÍCIOS SERVIDORES
        05/12/2025 1/1
        DEMONSTRATIVO DE PAGAMENTO
        NOME C.P.F
        Fernando Pedroso Rocha 111.528.728-18
        ENTIDADE BENEFÍCIO N° BENEFÍCIO
        SECRETARIA DE SEGURANÇA PÚBLICA APOSENTADORIA 80546077-01
        CARGO % APOSENTADORIA TIPO FOLHA
        CARCEREIRO DE 1A CLASSE 100,00 NORMAL
        COMPETÊNCIA BANCO AGÊNCIA N° CONTA
        11/2025 0001 0492 00-000107353-
        REG. RETRIB. ESC / TAB. REF / GR- NÍVEL
        14 11-001 48 0
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
        8.371,81 0,00 8.979,01 8.979,01 2.795,51 6.183,50
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_parse_complete_holerite(self, parser, realistic_spprev_holerite):
        """Should parse complete holerite successfully"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite is not None
        assert holerite.cabecalho is not None
        assert holerite.verbas is not None
        assert len(holerite.verbas) > 0

    def test_parse_extracts_correct_nome(self, parser, realistic_spprev_holerite):
        """Should extract correct nome"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.nome == "Fernando Pedroso Rocha"

    def test_parse_extracts_correct_cpf(self, parser, realistic_spprev_holerite):
        """Should extract correct CPF"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.cpf == "111.528.728-18"

    def test_parse_extracts_header_competencia(self, parser, realistic_spprev_holerite):
        """Should extract competencia"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.competencia == "2025-11"

    def test_parse_extracts_header_template_type(self, parser, realistic_spprev_holerite):
        """Should set correct template type"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.template_type == TemplateType.SPPREV_APOSENTADO

    def test_parse_extracts_header_tipo_folha(self, parser, realistic_spprev_holerite):
        """Should extract tipo de folha"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.tipo_folha == TipoFolha.NORMAL

    def test_parse_extracts_verbas(self, parser, realistic_spprev_holerite):
        """Should extract all verbas"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        # Should have extracted at least 8 verbas
        assert len(holerite.verbas) >= 8

    def test_parse_extracts_specific_verba_salario(self, parser, realistic_spprev_holerite):
        """Should find specific verba - SALARIO"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        salario = [v for v in holerite.verbas if "SALARIO" in v.denominacao.upper()]
        assert len(salario) > 0
        assert salario[0].valor == 2685.68

    def test_parse_extracts_totals_vencimentos(self, parser, realistic_spprev_holerite):
        """Should extract TOTAL VENCIMENTOS"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.total_vencimentos == 8979.01

    def test_parse_extracts_totals_descontos(self, parser, realistic_spprev_holerite):
        """Should extract TOTAL DESCONTOS"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.total_descontos == 2795.51

    def test_parse_extracts_totals_liquido(self, parser, realistic_spprev_holerite):
        """Should extract TOTAL LÍQUIDO"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.liquido == 6183.50

    def test_parse_multipage_holerite(self, parser):
        """Should handle multipage SPPREV holerites"""
        page1 = PaginaExtraida(numero=1, texto="""
        GOVERNO DO ESTADO DE SÃO PAULO
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES
        DEMONSTRATIVO DE PAGAMENTO
        NOME C.P.F
        Fernando Pedroso Rocha 111.528.728-18
        ENTIDADE BENEFÍCIO N° BENEFÍCIO
        SECRETARIA DE SEGURANÇA PÚBLICA APOSENTADORIA 80546077-01
        CARGO % APOSENTADORIA TIPO FOLHA
        CARCEREIRO DE 1A CLASSE 100,00 NORMAL
        COMPETÊNCIA BANCO AGÊNCIA N° CONTA
        11/2025 0001 0492 00-000107353-

        Código Denominação NAT Período Vencimento
        001001 SALARIO BASE N 11/2025 2.685,68
        004001 RETP-REGIME ESPECIAL N 11/2025 2.685,68
        """, metodo="TEXTO", confianca=0.95)

        page2 = PaginaExtraida(numero=2, texto="""
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES

        008473 ADIC. S/INTEGRAIS N 11/2025 196,42
        009001 ADICIONAL TEMPO N 11/2025 1.342,84
        070012 IMPOSTO DE RENDA N 11/2025 1.393,52

        BASE IR BASE REDUTOR BASE CONTRIB PREV TOTAL VENCTOS TOTAL DE DESCONTOS TOTAL LÍQUIDO
        8.371,81 0,00 8.979,01 8.979,01 2.795,51 6.183,50
        """, metodo="TEXTO", confianca=0.95)

        pages = [page1, page2]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.nome == "Fernando Pedroso Rocha"
        assert holerite.total_vencimentos == 8979.01
        assert holerite.liquido == 6183.50

    def test_parse_validates_holerite(self, parser, realistic_spprev_holerite):
        """Should validate extracted holerite data"""
        pages = [realistic_spprev_holerite]
        # Should not raise validation error
        holerite = parser.parse(pages)
        assert holerite is not None

    def test_parse_with_minimal_holerite(self, parser):
        """Should parse minimal valid SPPREV holerite"""
        texto = """
        SÃO PAULO PREVIDÊNCIA - SPPREV
        DIRETORIA DE BENEFÍCIOS SERVIDORES
        DEMONSTRATIVO DE PAGAMENTO

        NOME C.P.F
        João Silva 123.456.789-00

        Código Denominação NAT Período Vencimento
        001001 SALARIO N 01/2026 1.000,00

        TOTAL VENCIMENTOS 1.000,00
        TOTAL DESCONTOS 0,00
        TOTAL LÍQUIDO 1.000,00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)
        holerite = parser.parse([page])

        assert holerite.cabecalho.nome == "João Silva"
        assert holerite.cabecalho.cpf == "123.456.789-00"
        assert holerite.total_vencimentos == 1000.00
        assert holerite.liquido == 1000.00

    def test_parse_invokes_template_detection(self, parser, realistic_spprev_holerite):
        """Should correctly detect SPPREV template"""
        pages = [realistic_spprev_holerite]
        assert parser.detect_template(realistic_spprev_holerite.texto) is True

    def test_parse_metodo_extracao_preserved(self, parser, realistic_spprev_holerite):
        """Should preserve extraction method from page metadata"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.metodo_extracao == "TEXTO"

    def test_parse_confianca_preserved(self, parser, realistic_spprev_holerite):
        """Should preserve confidence from page metadata"""
        pages = [realistic_spprev_holerite]
        holerite = parser.parse(pages)

        assert holerite.confianca == 0.95
