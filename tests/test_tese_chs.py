"""
Testes da Tese CHS (Carga Horária Suplementar sobre Piso Docente).

Cobre principalmente a consolidação de verbas atrasadas (piso/CHS/salário
base): atrasados são realocados ao mês de competência a que se referem e
somados ao normal — regressão do bug em que eram descartados.
"""

from types import SimpleNamespace
from pathlib import Path

import pytest

from src.teses.tese_chs import TeseCHS
from src.export.chs_writer import write_chs_xlsx


def _verba(nat, valor, ini=None, fim=None):
    """Mock leve de Verba com o que _distribuir_por_pagamento consome."""
    return SimpleNamespace(
        natureza=SimpleNamespace(value=nat),
        valor=valor,
        periodo_inicio=ini,
        periodo_fim=fim,
    )


class TestLogicaAtrasados:
    """Testes unitários rápidos (sem PDF) da mecânica de atrasados."""

    def test_normal_vai_para_mes_de_pagamento(self):
        # Verba normal da competência 03/2024 é paga em 04/2024 (comp+1)
        out = TeseCHS._distribuir_por_pagamento(_verba('N', 500.0), '2024-03')
        assert out == [('2024-04', 500.0)]

    def test_atrasado_realocado_e_distribuido_pelo_periodo(self):
        # Atrasado achado no holerite 07/2024, referente a jan–mar/2024:
        # distribui 300 em 3 meses (100 cada) e realoca ao pagamento de cada mês.
        out = TeseCHS._distribuir_por_pagamento(
            _verba('A', 300.0, ini='2024-01', fim='2024-03'), '2024-07'
        )
        assert out == [('2024-02', 100.0), ('2024-03', 100.0), ('2024-04', 100.0)]

    def test_atrasado_sem_periodo_usa_competencia(self):
        # Sem periodo_inicio/fim, cai na competência do holerite (1 mês)
        out = TeseCHS._distribuir_por_pagamento(_verba('R', 80.0), '2022-05')
        assert out == [('2022-06', 80.0)]

    def test_add_separa_normal_de_atrasado(self):
        bucket = {'normal': 0.0, 'atrasados': []}
        TeseCHS._add(bucket, 'N', '2024-01', 100.0)
        TeseCHS._add(bucket, 'N', '2024-01', 50.0)
        TeseCHS._add(bucket, 'A', '2024-05', 40.0)
        assert bucket['normal'] == 150.0
        assert bucket['atrasados'] == [('2024-05', 40.0)]


# ---- End-to-end com PDF real (padrão dos demais testes e2e do projeto) ----

EDER_PDF = Path(
    "docs/referencias/06. HOLERITES - 02-21 A 02-26 - EDER ADRIANO PEREIRA.pdf"
)


@pytest.fixture(scope="module")
def eder_resultado():
    """Processa o EDER uma única vez para os testes e2e da CHS."""
    if not EDER_PDF.exists():
        pytest.skip("PDF de referência do EDER não encontrado")
    return TeseCHS().processar(str(EDER_PDF))


def _soma_diferencas_chs(resultado):
    """Diferença mensal da CHS = (piso_total / jornada) * horas suplementares."""
    total = 0.0
    for d in resultado['periodos'].values():
        piso = d['piso_normal'] + sum(v for _, v in d['piso_atrasados'])
        jornada = d['jornada_horas'] or 0
        horas = d['horas_suplementares'] or 0
        if jornada:
            total += (piso / jornada) * horas
    return total


class TestTeseCHSEndToEnd:
    def test_metadados(self, eder_resultado):
        assert eder_resultado['nome_cliente'].startswith("EDER")
        assert eder_resultado['tese_tipo'] == 'chs'
        assert eder_resultado['vinculo'] == 'efetivo'
        assert eder_resultado['situacao'] == 'ativo'

    def test_consolida_13_atrasados_de_piso(self, eder_resultado):
        # Regressão: antes o código descartava natureza != N (0 atrasados).
        n_atrasados = sum(
            len(d['piso_atrasados']) for d in eder_resultado['periodos'].values()
        )
        assert n_atrasados == 13

    def test_soma_diferencas_bate_valor_esperado(self, eder_resultado):
        # Valor validado manualmente; com os atrasados de piso incluídos.
        assert _soma_diferencas_chs(eder_resultado) == pytest.approx(7083.52, abs=1.0)

    def test_gera_xlsx_sem_erro(self, eder_resultado, tmp_path):
        out = tmp_path / "eder_chs.xlsx"
        write_chs_xlsx(eder_resultado, str(out))
        assert out.exists() and out.stat().st_size > 0
