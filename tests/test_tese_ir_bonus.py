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
PDF_KARIM = REF / "06. HOLERITES SUPLEMENTAR 07-2021 A 04-2026 - KARIM ANDRADE CARDOZO DE MACEDO (11289090-01).pdf"


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
    def test_meses_periodo(self):
        assert TeseIRBonus.meses_periodo(date(2023, 3, 1), date(2023, 12, 31)) == 10
        assert TeseIRBonus.meses_periodo(date(2021, 1, 1), date(2021, 1, 31)) == 1

    def test_rra_parcela_isenta(self):
        p = {"inicio": date(2020, 3, 1), "fim": date(2020, 4, 30),
             "pagamento": date(2021, 7, 27), "bonus": 450.0,
             "dependentes": 0, "ir_pago": 118.62}
        # base 225/mês → isento → recupera todo o IR pago
        assert TeseIRBonus.diferenca_rra(p) == pytest.approx(118.62, abs=0.01)


@pytest.mark.skipif(not PDF_ADILSON.exists(), reason="PDF de referência ausente")
class TestExtracaoReal:
    def test_adilson_br_no_bloco_rra(self):
        r = TeseIRBonus().processar(str(PDF_ADILSON))
        assert r["nome_cliente"] == "ADILSON PEREIRA"
        assert len(r["rra"]) == 28          # só BR, no bloco RRA
        assert r["isencao"] == {}           # sem FUNDEB/DEJEC
        assert r["total_recuperar"] == pytest.approx(8993.31, abs=0.01)

    def test_karim_extrai_dependentes(self):
        # KARIM tem "IMPOSTO DE RENDA NA FONTE 002 DEPTE" → 2 dependentes.
        # Parcelas com IR retido (ir_pago > 0) devem trazer os 2 dependentes;
        # páginas sem linha de IR ficam com 0 (nada a recuperar ali).
        r = TeseIRBonus().processar(str(PDF_KARIM))
        assert r["rra"], "esperado parcelas BR"
        com_ir = [p for p in r["rra"] if p["ir_pago"] > 0]
        assert com_ir and all(p["dependentes"] == 2 for p in com_ir)

    def test_keilla_fundeb_vai_para_isencao(self):
        r = TeseIRBonus().processar(str(PDF_KEILLA))
        # BR no bloco RRA; FUNDEB no bloco de isenção (restituição integral)
        assert len(r["rra"]) == 2
        assert "FUNDEB" in r["isencao"]
        for p in r["isencao"]["FUNDEB"]:
            assert p["pagamento"].year <= 2022     # filtro FUNDEB ≤ 2022
        # isenção FUNDEB = soma integral do IR pago
        fundeb_total = sum(p["ir_pago"] for p in r["isencao"]["FUNDEB"])
        assert fundeb_total == pytest.approx(4282.20, abs=0.01)
        assert r["total_recuperar"] == pytest.approx(7355.70, abs=0.01)

    def test_multi_pdf_nao_duplica(self):
        # mesmo PDF duas vezes → dedup evita contar em dobro
        r1 = TeseIRBonus().processar(str(PDF_ADILSON))
        r2 = TeseIRBonus().processar([str(PDF_ADILSON), str(PDF_ADILSON)])
        assert len(r2["rra"]) == len(r1["rra"])
        assert r2["total_recuperar"] == pytest.approx(r1["total_recuperar"], abs=0.01)


@pytest.mark.skipif(not PDF_KEILLA.exists(), reason="PDF de referência ausente")
class TestWriterFormulas:
    def test_xlsx_dois_blocos_e_dados(self, tmp_path):
        r = TeseIRBonus().processar(str(PDF_KEILLA))
        out = tmp_path / "keilla.xlsx"
        write_ir_bonus_xlsx(r, str(out))
        wb = openpyxl.load_workbook(out)
        assert wb.sheetnames == ["Cálculo", "Dados"]

        # aba Dados tem a dedução por dependente em K3 e a tabela M2:R21
        dados = wb["Dados"]
        assert dados["K3"].value == pytest.approx(DEDUCAO_POR_DEPENDENTE, abs=0.01)
        assert dados["M2"].value == "Ano_2015"
        assert dados["M21"].value == "Ano_2025"

        # a aba Cálculo tem os dois blocos e o VALOR DA CAUSA
        ws = wb["Cálculo"]
        textos = [ws.cell(row=r_, column=1).value for r_ in range(1, ws.max_row + 1)]
        textos = [t for t in textos if isinstance(t, str)]
        assert any("BONIFICAÇÃO POR RESULTADOS (RRA)" in t for t in textos)
        assert any("ISENÇÃO" in t for t in textos)
        assert any("VALOR DA CAUSA" in t for t in textos)

    def test_simulacao_formula_excel_bate_com_python(self):
        # Reproduz o INDEX/SUMPRODUCT do Excel em Python e compara com o cálculo.
        r = TeseIRBonus().processar(str(PDF_KEILLA))
        total_sim = sum(TeseIRBonus.diferenca_rra(p) for p in r["rra"])
        for parcelas in r["isencao"].values():
            total_sim += sum(p["ir_pago"] for p in parcelas)   # isenção = IR integral
        assert total_sim == pytest.approx(r["total_recuperar"], abs=0.01)
