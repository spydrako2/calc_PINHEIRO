"""
Testes da Tese Piso Salarial Docente + writer no layout modelo Pinheiro
(QUINQUÊNIO E SEXTA PARTE).

Cobre:
- Detecção de situação por período (DDPE=ativo, SPPREV=inativo).
- Fechamento anual: 13º sempre; 1/3 de férias só em anos ativos.
- Proteção da planilha com colunas de entrada editáveis.
"""

from pathlib import Path

import openpyxl
import pytest

from src.teses.tese_piso_docente import TesePisoDocente
from src.export.piso_writer import write_piso_xlsx


ELZA_PDF = Path(
    "docs/referencias/HOLERITES SPPREV APOSENTADORIA/"
    "06. HOLERITES APOSENTADA - 06-20 A 06-25 - ELZA NOGUEIRA GONÇALVES.pdf"
)
EDER_PDF = Path(
    "docs/referencias/06. HOLERITES - 02-21 A 02-26 - EDER ADRIANO PEREIRA.pdf"
)


def _fechamentos(ws):
    """Retorna (n_13_salario, n_um_terco_ferias) varrendo a coluna A."""
    n13 = n13f = 0
    for row in range(1, ws.max_row + 1):
        v = ws.cell(row=row, column=1).value
        if v == "13 SALARIO":
            n13 += 1
        elif v == "1/3 de férias":
            n13f += 1
    return n13, n13f


class TestTesePisoInativo:
    """Elza (SPPREV aposentada): tudo inativo → só 13º, sem 1/3 de férias."""

    @pytest.fixture(scope="class")
    def resultado(self):
        if not ELZA_PDF.exists():
            pytest.skip("PDF da ELZA não encontrado")
        return TesePisoDocente().processar(str(ELZA_PDF))

    def test_situacao_inativa(self, resultado):
        assert resultado['tese_tipo'] == 'piso'
        assert set(resultado['situacao_por_periodo'].values()) == {'inativo'}

    def test_sem_um_terco_ferias(self, resultado, tmp_path):
        out = tmp_path / "elza_piso.xlsx"
        write_piso_xlsx(resultado, str(out))
        ws = openpyxl.load_workbook(out).active
        n13, n13f = _fechamentos(ws)
        assert n13 >= 1           # há fechamentos de 13º
        assert n13f == 0          # inativo NÃO gera 1/3 de férias

    def test_planilha_totalmente_editavel(self, resultado, tmp_path):
        out = tmp_path / "elza_piso.xlsx"
        write_piso_xlsx(resultado, str(out))
        ws = openpyxl.load_workbook(out).active
        # Planilha sem proteção de folha: todas as células são editáveis.
        assert ws.protection.sheet is False


class TestTesePisoAtivo:
    """Eder (DDPE ativo): tudo ativo → 13º + 1/3 de férias por ano."""

    @pytest.fixture(scope="class")
    def resultado(self):
        if not EDER_PDF.exists():
            pytest.skip("PDF do EDER não encontrado")
        return TesePisoDocente().processar(str(EDER_PDF))

    def test_situacao_ativa(self, resultado):
        assert set(resultado['situacao_por_periodo'].values()) == {'ativo'}

    def test_gera_um_terco_ferias(self, resultado, tmp_path):
        out = tmp_path / "eder_piso.xlsx"
        write_piso_xlsx(resultado, str(out))
        ws = openpyxl.load_workbook(out).active
        n13, n13f = _fechamentos(ws)
        assert n13 >= 1
        assert n13f == n13        # todo ano ativo tem 13º E 1/3 de férias

    def test_total_bruto_presente(self, resultado, tmp_path):
        out = tmp_path / "eder_piso.xlsx"
        write_piso_xlsx(resultado, str(out))
        ws = openpyxl.load_workbook(out).active
        achou = any(
            ws.cell(row=r, column=6).value == "TOTAL BRUTO:"
            for r in range(1, ws.max_row + 1)
        )
        assert achou
