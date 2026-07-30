"""
Testes de robustez contra páginas escaneadas (OCR) e layouts atípicos.

Regressões cobertas aqui (todas encontradas com PDFs reais de clientes):

1. Valor sem centavos vindo de OCR — o período "01/01/2026 A 31/01/2026" foi
   lido como "0101/2026A 31012026" e o parser aceitou "31012026" como valor,
   lançando R$ 31.012.026,00 num holerite cujo total de vencimentos era
   R$ 6.055,50 (tese IAMSPE somou R$ 31 milhões).

2. Unidade "PERC." nunca era reconhecida (o '\\b' final não casa depois de um
   ponto), então a quantidade ficava grudada na denominação.

3. Quantidade em percentual lida como contagem de quinquênios: "10,00 PERC."
   são 10% = 2 quinquênios, não 10 (inflaria o cálculo em 5x).

4. Nome do cliente em holerite juntado a processo, onde o carimbo
   ("protocolado em ... sob", "fls. NNN") se intercala entre o cabeçalho
   "Nome ... C.P.F" e a linha de dados.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.core.pdf_reader import PaginaExtraida, PDFReader
from src.core.parsers.ddpe_parser import DDPEParser
from src.teses.base_tese import BaseTese


def _pagina(texto: str) -> PaginaExtraida:
    return PaginaExtraida(numero=1, texto=texto, metodo="OCR", confianca=0.70)


def _parse(texto: str):
    parser = DDPEParser()
    parser.paginas = [_pagina(texto)]
    return parser._extract_verbas()


class TestValorPrecisaTerCentavos:
    """Valor monetário de holerite sempre tem 2 casas decimais."""

    def test_lixo_de_ocr_sem_centavos_e_descartado(self):
        # Linha real da pág. 76 de um holerite escaneado: o período virou
        # "0101/2026A 31012026" e "31012026" não pode virar R$ 31 milhões.
        texto = (
            "Código Denominação Nat. Qtde. Unid. Período Valor\n"
            "70179 [IAMSPE BENEFICIARIOS-LE! 17 293/20 | nN] 200 | PERG [ 0101/2026A 31012026\n"
        )
        assert _parse(texto) == []

    def test_pedaco_de_data_nao_vira_valor(self):
        # "01/2026" no fim da linha não é valor (sem centavos).
        texto = "70125 [IAMSPE - LEI 17 293/2020 01/2026\n"
        assert _parse(texto) == []

    def test_valor_brasileiro_com_centavos_continua_valendo(self):
        verbas = _parse("01.035 PISO SAL.DOCENTE N VALOR 12/2025 1.938,75+\n")
        assert len(verbas) == 1
        assert verbas[0].valor == 1938.75

    def test_valor_com_ponto_decimal_continua_valendo(self):
        verbas = _parse("01.001 SALARIO BASE 5000.00\n")
        assert len(verbas) == 1
        assert verbas[0].valor == 5000.00


class TestUnidadePerc:
    """'PERC.' termina em ponto — o padrão precisa casar mesmo assim."""

    def test_perc_reconhecida_e_quantidade_extraida(self):
        verbas = _parse("70.006 IAMSPE N 2,00 PERC. 12/1999 23,24-\n")
        assert len(verbas) == 1
        v = verbas[0]
        assert v.unidade == "PERC."
        assert v.quantidade == 2.00
        # A quantidade sai da denominação em vez de ficar grudada nela.
        assert v.denominacao == "IAMSPE"

    def test_unidades_sem_ponto_seguem_funcionando(self):
        verbas = _parse("02.044 CARGA HOR/SUPL - 5 A 8 SERIE N 145 AULAS 12/1999 773,93+\n")
        assert verbas[0].unidade == "AULAS"
        assert verbas[0].quantidade == 145.0


class TestQuinquenioPercentualVsContagem:
    """A unidade decide se a quantidade é contagem ou percentual."""

    @staticmethod
    def _verba(quantidade, unidade, denominacao=""):
        return SimpleNamespace(
            quantidade=quantidade, unidade=unidade, denominacao=denominacao
        )

    def test_percentual_e_convertido_em_quinquenios(self):
        # 10,00 PERC. = 10% = 2 quinquênios (cada quinquênio vale 5%)
        v = self._verba(10.0, "PERC.", "ADICIONAL TEMPO DE SERVICO")
        assert BaseTese._extract_quinquenios(v) == 2

    def test_quantidade_sem_perc_e_contagem_direta(self):
        v = self._verba(5.0, "QUINQ", "ADICIONAL TEMPO DE SERVICO")
        assert BaseTese._extract_quinquenios(v) == 5

    def test_fallback_pela_denominacao_sem_quantidade(self):
        v = self._verba(None, None, "ADICIONAL TEMPO DE SERVICO 003 QUINQ")
        assert BaseTese._extract_quinquenios(v) == 3


class TestPaginaGirada:
    """
    Página digitalizada de lado (foto/print girado) é perda total sem correção:
    o OCR devolve texto ilegível, nenhum parser reconhece o template e o
    holerite some do cálculo sem aviso. O OSD do tesseract detecta e corrige.
    """

    def setup_method(self):
        PDFReader._osd_disponivel = None

    def teardown_method(self):
        PDFReader._osd_disponivel = None

    def test_parece_holerite_reconhece_ddpe(self):
        assert PDFReader._parece_holerite(
            "GOVERNO DO ESTADO\nDepartamento de Despesa de Pessoal do Estado")

    def test_parece_holerite_rejeita_lixo_e_vazio(self):
        assert not PDFReader._parece_holerite("~~ ]|[ x' ,, ...")
        assert not PDFReader._parece_holerite("")
        assert not PDFReader._parece_holerite(None)

    def test_gira_quando_osd_indica_rotacao(self):
        img = MagicMock()
        girada = MagicMock()
        img.rotate.return_value = girada
        osd = "Page number: 0\nRotate: 90\nOrientation confidence: 12.5\n"
        with patch("pytesseract.image_to_osd", return_value=osd):
            assert PDFReader._corrigir_orientacao(img) is girada
        # rotate(-90) desfaz um giro de 90°
        img.rotate.assert_called_once()
        assert img.rotate.call_args.args[0] == -90

    def test_nao_gira_pagina_ja_correta(self):
        img = MagicMock()
        osd = "Page number: 0\nRotate: 0\nOrientation confidence: 15.0\n"
        with patch("pytesseract.image_to_osd", return_value=osd):
            assert PDFReader._corrigir_orientacao(img) is img
        img.rotate.assert_not_called()

    def test_nao_gira_com_confianca_baixa(self):
        # Confiança baixa é chute: girar página certa seria pior que não fazer nada.
        img = MagicMock()
        osd = "Page number: 0\nRotate: 180\nOrientation confidence: 0.2\n"
        with patch("pytesseract.image_to_osd", return_value=osd):
            assert PDFReader._corrigir_orientacao(img) is img
        img.rotate.assert_not_called()

    def test_desativa_sozinho_sem_osd_traineddata(self):
        # Ambiente sem osd.traineddata (ex.: Streamlit Cloud): degrada em silêncio
        # e não tenta de novo nas páginas seguintes.
        img = MagicMock()
        with patch("pytesseract.image_to_osd", side_effect=Exception("no osd")) as m:
            assert PDFReader._corrigir_orientacao(img) is img
            assert PDFReader._osd_disponivel is False
            assert PDFReader._corrigir_orientacao(img) is img
        assert m.call_count == 1


class TestNomeComCarimboDeProcesso:
    """Holerite juntado a processo tem carimbo intercalado no cabeçalho."""

    def test_nome_encontrado_apesar_do_carimbo(self):
        texto = (
            "Nome Reg. Sistema (RS) / PV Reg. Geral DC C.P.F\n"
            "sob\n"
            "DILCEIA ANDRE DE SOUZA 06.502.994/01 00016632470 077943538/90\n"
        )
        assert BaseTese._extract_nome(texto) == "DILCEIA ANDRE DE SOUZA"

    def test_layout_limpo_continua_funcionando(self):
        texto = (
            "Nome Reg. Sistema (RS) / PV Reg. Geral DC C.P.F\n"
            "AILTON TURATO 02.166.604/01 00005044111 653941518/49\n"
        )
        assert BaseTese._extract_nome(texto) == "AILTON TURATO"

    def test_sem_cabecalho_devolve_unknown(self):
        assert BaseTese._extract_nome("linha qualquer\noutra linha\n") == "UNKNOWN"
