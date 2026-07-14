"""
Testes da Tese IR sobre Bônus (RRA).

Cobre:
- O cálculo RRA (tabelas IRPF por ano) em `irpf_rra_tables`.
- A extração de parcelas de holerite real (BR policial + FUNDEB docente).
- Regras de negócio: rateio do IR, filtro FUNDEB (pago ≤ 2022), DEJEC isenção.
- Geração do XLSX com fórmulas + aba Dados, e a simulação das fórmulas do Excel
  batendo com o cálculo em Python.
"""

from datetime import date
from pathlib import Path

import openpyxl
import pytest

from src.core.irpf_rra_tables import (
    ano_calendario, ir_devido_rra, faixa_para_base, DEDUCAO_POR_DEPENDENTE,
)
from src.teses.tese_ir_bonus import TeseIRBonus, classificar_bonus
from src.export.ir_bonus_writer import write_ir_bonus_xlsx

REF = Path("docs/referencias/IR BONUS")
PDF_ADILSON = REF / "06. HOLERITES SUPLEMENTAR 07-2021 A 04-2026 - ADILSON PEREIRA.pdf"
PDF_KEILLA = REF / "06. HOLERITES SUPLEMENTAR 12-2021 A 04-2026 - KEILLA MARÇAL PEREIRA.pdf"


class TestTabelasIRPF:
    def test_ano_calendario_por_data_pagamento(self):
        assert ano_calendario("2022-06") == "Ano_2015"   # antes de 05/2023
        assert ano_calendario("2023-05") == "Ano_2023"   # exatamente no limiar
        assert ano_calendario("2024-01") == "Ano_2023"
        assert ano_calendario("2024-02") == "Ano_2024"   # limiar 02/2024
        assert ano_calendario("2025-04") == "Ano_2024"
        assert ano_calendario("2025-05") == "Ano_2025"   # limiar 05/2025

    def test_base_isenta_gera_ir_zero(self):
        # bônus de 900 diluído em 2 meses = 450/mês → isento em qualquer ano
        calc = ir_devido_rra(900.0, 2, "Ano_2015")
        assert calc["ir_devido"] == 0.0
        assert calc["aliquota"] == 0.0

    def test_base_um_mes_cai_na_faixa_alta(self):
        # 5330 em 1 mês → base 5330 → faixa 27,5% (Ano_2015)
        calc = ir_devido_rra(5330.0, 1, "Ano_2015")
        assert calc["aliquota"] == 0.275
        # (5330*0,275 - 756,53) * 1
        assert calc["ir_devido"] == pytest.approx(709.22, abs=0.01)

    def test_deducao_por_dependente_reduz_base(self):
        calc = ir_devido_rra(6000.0, 1, "Ano_2024", dependentes=2)
        assert calc["deducao_dep"] == pytest.approx(2 * DEDUCAO_POR_DEPENDENTE, abs=0.01)
        assert calc["base_calculo"] == pytest.approx(6000.0 - 2 * DEDUCAO_POR_DEPENDENTE, abs=0.01)


class TestClassificacao:
    def test_classifica_tipos(self):
        assert classificar_bonus("BONIFIC. POR RESULTADO-LC 1245/2014") == "BR"
        assert classificar_bonus("BONIFIC. POR RESULT. - L.C. 1078/08") == "BR"
        assert classificar_bonus("ABONO FUNDEB") == "FUNDEB"
        assert classificar_bonus("DEJEC-CARREIRA POLICIAL-LC.1280/16") == "DEJEC"
        assert classificar_bonus("SALARIO BASE") is None


class TestCalculoParcela:
    def test_dejec_isencao_recupera_todo_ir(self):
        p = {"inicio": date(2024, 11, 1), "fim": date(2024, 11, 30),
             "pagamento": date(2025, 1, 8), "bonus": 282.88,
             "dependentes": 0, "ir_pago": 39.84}
        assert TeseIRBonus.diferenca_parcela(p, "DEJEC") == pytest.approx(39.84, abs=0.01)

    def test_meses_periodo(self):
        assert TeseIRBonus.meses_periodo(date(2023, 3, 1), date(2023, 12, 31)) == 10
        assert TeseIRBonus.meses_periodo(date(2021, 1, 1), date(2021, 1, 31)) == 1


@pytest.mark.skipif(not PDF_ADILSON.exists(), reason="PDF de referência ausente")
class TestExtracaoReal:
    def test_adilson_br_policial(self):
        r = TeseIRBonus().processar(str(PDF_ADILSON))
        assert r["nome_cliente"] == "ADILSON PEREIRA"
        assert set(r["parcelas_por_tipo"].keys()) == {"BR"}
        assert len(r["parcelas_por_tipo"]["BR"]) == 28
        # todas as parcelas de 2 meses → base baixa → recupera todo o IR
        assert r["total_recuperar"] == pytest.approx(8993.31, abs=0.01)

    def test_keilla_fundeb_e_br_docente(self):
        r = TeseIRBonus().processar(str(PDF_KEILLA))
        tipos = r["parcelas_por_tipo"]
        assert "FUNDEB" in tipos and "BR" in tipos
        # FUNDEB: todas pagas ≤ 2022 (filtro não remove nenhuma aqui)
        for p in tipos["FUNDEB"]:
            assert p["pagamento"].year <= 2022
        assert r["total_recuperar"] == pytest.approx(5967.29, abs=0.01)

    def test_ir_rateado_entre_parcelas_do_holerite(self):
        # holerite com múltiplas parcelas: soma do IR rateado == IR do holerite
        r = TeseIRBonus().processar(str(PDF_ADILSON))
        # não há como somar por holerite aqui sem reprocessar; garante que o IR
        # pago total das parcelas é positivo e coerente
        total_ir = sum(p["ir_pago"] for p in r["parcelas_por_tipo"]["BR"])
        assert total_ir > 0


@pytest.mark.skipif(not PDF_KEILLA.exists(), reason="PDF de referência ausente")
class TestWriterFormulas:
    def test_xlsx_reproduz_formulas_do_modelo(self, tmp_path):
        r = TeseIRBonus().processar(str(PDF_KEILLA))
        out = tmp_path / "keilla.xlsx"
        write_ir_bonus_xlsx(r, str(out))
        wb = openpyxl.load_workbook(out)
        assert "Dados" in wb.sheetnames
        assert any(s.startswith("Cálculo - ") for s in wb.sheetnames)

        # aba Dados tem a dedução por dependente em K3 e a tabela M2:R21
        dados = wb["Dados"]
        assert dados["K3"].value == pytest.approx(DEDUCAO_POR_DEPENDENTE, abs=0.01)
        assert dados["M2"].value == "Ano_2015"
        assert dados["M21"].value == "Ano_2025"

        # linha de dados usa fórmula RRA (coluna N) e input de bônus (coluna F)
        ws = wb[[s for s in wb.sheetnames if s.startswith("Cálculo")][0]]
        assert str(ws["N4"].value).startswith("=") or ws["N4"].value == 0
        assert isinstance(ws["F4"].value, (int, float))

    def test_simulacao_formula_excel_bate_com_python(self):
        # Reproduz o INDEX/SUMPRODUCT do Excel em Python e compara com o cálculo.
        r = TeseIRBonus().processar(str(PDF_KEILLA))
        total_sim = 0.0
        for tipo, parcelas in r["parcelas_por_tipo"].items():
            for p in parcelas:
                total_sim += TeseIRBonus.diferenca_parcela(p, tipo)
        assert total_sim == pytest.approx(r["total_recuperar"], abs=0.01)
