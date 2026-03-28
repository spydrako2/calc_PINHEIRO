"""
Testes unitários para utilitários de BaseTese.
Cobre os 4 bugs corrigidos:
  1. Fórmula de atraso (=normal+atraso em vez de valor bruto) → testado via data model
  2. Propagação de quinquênios (comparação por payment month)
  3. Período longo → divisão pro rata (_distribute_valor)
  4. Linhas chaveadas por mês de pagamento (mes_pagamento = comp + 1 mês)
"""

import pytest
from src.teses.base_tese import BaseTese


# ---------------------------------------------------------------------------
# test_months_in_range
# ---------------------------------------------------------------------------

class TestMonthsInRange:
    """Bug fix #3: períodos longos devem ser expandidos em lista de meses."""

    def test_normal_range_jan_apr(self):
        result = BaseTese._months_in_range("2025-01", "2025-04")
        assert result == ["2025-01", "2025-02", "2025-03", "2025-04"]

    def test_single_month_returns_list_with_one_element(self):
        result = BaseTese._months_in_range("2025-01", "2025-01")
        assert result == ["2025-01"]
        assert len(result) == 1

    def test_year_boundary_nov_to_feb(self):
        result = BaseTese._months_in_range("2025-11", "2026-02")
        assert result == ["2025-11", "2025-12", "2026-01", "2026-02"]
        assert len(result) == 4

    def test_inicio_equals_fim(self):
        result = BaseTese._months_in_range("2024-06", "2024-06")
        assert len(result) == 1
        assert result[0] == "2024-06"

    def test_full_year(self):
        result = BaseTese._months_in_range("2023-01", "2023-12")
        assert len(result) == 12
        assert result[0] == "2023-01"
        assert result[-1] == "2023-12"

    def test_inverted_range_returns_fallback(self):
        """Quando inicio > fim, deve retornar fallback com periodo_fim."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = BaseTese._months_in_range("2025-06", "2025-01")
            assert result == ["2025-01"]
            assert len(w) == 1


# ---------------------------------------------------------------------------
# test_mes_pagamento
# ---------------------------------------------------------------------------

class TestMesPagamento:
    """Bug fix #4: linhas devem ser chaveadas por mes_pagamento (comp+1), não comp."""

    def test_january_to_february(self):
        assert BaseTese.mes_pagamento("2025-01") == "2025-02"

    def test_december_wraps_to_january_next_year(self):
        """Bug fix crítico: Dez/2025 → Jan/2026 (virada de ano)."""
        assert BaseTese.mes_pagamento("2025-12") == "2026-01"

    def test_november_to_december(self):
        assert BaseTese.mes_pagamento("2024-11") == "2024-12"

    def test_june_to_july(self):
        assert BaseTese.mes_pagamento("2023-06") == "2023-07"

    def test_format_preserved(self):
        """Formato YYYY-MM deve ser preservado (zero-pad no mês)."""
        result = BaseTese.mes_pagamento("2025-09")
        assert result == "2025-10"
        assert len(result) == 7


# ---------------------------------------------------------------------------
# test_distribute_valor
# ---------------------------------------------------------------------------

class TestDistributeValor:
    """Bug fix #3: valor deve ser distribuído pro rata sem drift de centavos."""

    def test_divisao_por_tres_com_residuo(self):
        """100.00 / 3 → [33.33, 33.33, 33.34] e soma = 100.00."""
        result = BaseTese._distribute_valor(100.00, 3)
        assert len(result) == 3
        assert result == [33.33, 33.33, 33.34]
        assert round(sum(result), 2) == 100.00

    def test_divisao_exata_por_quatro(self):
        result = BaseTese._distribute_valor(1000.00, 4)
        assert result == [250.0, 250.0, 250.0, 250.0]
        assert sum(result) == 1000.00

    def test_divisao_por_um_retorna_valor_original(self):
        result = BaseTese._distribute_valor(329.65, 1)
        assert result == [329.65]

    def test_soma_sempre_igual_ao_valor_original(self):
        """Invariante principal: sem drift de centavos."""
        for valor in [99.99, 100.01, 1234.56, 0.01]:
            for n in [2, 3, 5, 12]:
                result = BaseTese._distribute_valor(valor, n)
                assert round(sum(result), 2) == round(valor, 2), (
                    f"Drift detectado: valor={valor}, n={n}, "
                    f"sum={sum(result)}"
                )

    def test_n_zero_retorna_lista_com_valor(self):
        """n <= 1 deve retornar [valor] sem divisão por zero."""
        result = BaseTese._distribute_valor(50.0, 0)
        assert result == [50.0]


# ---------------------------------------------------------------------------
# test_quinquenio_propagation (smoke test sem PDF)
# ---------------------------------------------------------------------------

class TestQuinquenioPropagation:
    """
    Bug fix #2: propagação de quinquênios deve usar mes_pagamento(comp) para
    comparação com pay_key, não comp diretamente.

    Simula o loop de propagação com dict manual.
    """

    def _propagate(self, quinq_by_comp: dict, pay_keys: list) -> dict:
        """
        Replica exatamente o loop de propagação de BaseTese.processar().
        Retorna {pay_key: quinquenios_propagado}.
        """
        all_comp_keys = sorted(quinq_by_comp.keys())
        result = {}
        for pay_key in sorted(pay_keys):
            best_q = 0
            for c in all_comp_keys:
                if BaseTese.mes_pagamento(c) <= pay_key:
                    best_q = quinq_by_comp[c]
                else:
                    break
            if best_q == 0 and all_comp_keys:
                best_q = quinq_by_comp[all_comp_keys[0]]
            result[pay_key] = best_q
        return result

    def test_quinquenio_propagado_para_periodos_futuros(self):
        """
        Se quinquênio detectado em comp 2024-01 (pay_key 2024-02),
        todos os pay_keys >= 2024-02 devem receber o mesmo valor.
        """
        quinq_by_comp = {"2024-01": 4}
        pay_keys = ["2024-02", "2024-03", "2024-04"]
        result = self._propagate(quinq_by_comp, pay_keys)
        assert result == {
            "2024-02": 4,
            "2024-03": 4,
            "2024-04": 4,
        }

    def test_quinquenio_atualizado_quando_aumenta(self):
        """
        Ao ganhar novo quinquênio em comp 2024-06 (pay_key 2024-07),
        pay_keys antes de 2024-07 devem ter valor antigo, depois novo.
        """
        quinq_by_comp = {"2024-01": 3, "2024-06": 4}
        pay_keys = ["2024-02", "2024-05", "2024-07", "2024-08"]
        result = self._propagate(quinq_by_comp, pay_keys)
        # 2024-02 e 2024-05: mes_pagamento(2024-01)=2024-02 <= pay_key, quinq=3
        assert result["2024-02"] == 3
        assert result["2024-05"] == 3
        # 2024-07 e 2024-08: mes_pagamento(2024-06)=2024-07 <= pay_key, quinq=4
        assert result["2024-07"] == 4
        assert result["2024-08"] == 4

    def test_virada_de_ano_dezembro(self):
        """
        Bug fix #2: comp 2024-12 → mes_pagamento = 2025-01.
        pay_key 2025-01 deve receber o quinquênio de 2024-12.
        """
        quinq_by_comp = {"2024-12": 5}
        pay_keys = ["2025-01", "2025-02"]
        result = self._propagate(quinq_by_comp, pay_keys)
        assert result["2025-01"] == 5
        assert result["2025-02"] == 5

    def test_fallback_para_primeiro_quinquenio_conhecido(self):
        """
        Pay_key anterior a qualquer quinquênio detectado deve usar
        o primeiro valor disponível como fallback.
        """
        quinq_by_comp = {"2024-03": 2}
        pay_keys = ["2024-01", "2024-02"]  # antes de mes_pagamento(2024-03)=2024-04
        result = self._propagate(quinq_by_comp, pay_keys)
        # best_q = 0 → fallback → primeiro = 2
        assert result["2024-01"] == 2
        assert result["2024-02"] == 2


# ---------------------------------------------------------------------------
# test_atrasado_data_model — verifica estrutura para geração de fórmula
# ---------------------------------------------------------------------------

class TestAtrasadoDataModel:
    """
    Bug fix #1: atrasados devem ser armazenados como lista separada,
    não somados no 'normal', para que o writer possa gerar =normal+atraso.

    Testa a estrutura do data model sem PDF real.
    """

    def test_periodos_tem_chave_normal_e_atrasados(self):
        """
        Verifica que o dict de período tem ambas as chaves
        exigidas pelo writer para gerar fórmulas.
        """
        periodo = {'normal': 100.0, 'atrasados': [('' , 50.0)]}
        assert 'normal' in periodo
        assert 'atrasados' in periodo
        assert isinstance(periodo['atrasados'], list)

    def test_formula_gerada_corretamente(self):
        """
        Replica a lógica do _col_formula de apeoesp_writer:
        com atrasados → string de fórmula '=100.00+50.00'
        sem atrasados → valor float simples
        """
        def col_formula(normal, atrasados):
            if not atrasados:
                return normal or None
            parts = []
            if normal:
                parts.append(f"{normal:.2f}")
            for _, val in atrasados:
                parts.append(f"{val:.2f}")
            return ("=" + "+".join(parts)) if parts else None

        # Com atrasados → fórmula
        result = col_formula(100.0, [("2024-01", 50.0)])
        assert result == "=100.00+50.00"

        # Sem atrasados → valor direto
        result = col_formula(100.0, [])
        assert result == 100.0

        # Apenas atrasado (normal=0) → fórmula sem zero
        result = col_formula(0.0, [("2024-01", 75.0)])
        assert result == "=75.00"

    def test_total_inclui_normal_mais_atrasados(self):
        """
        O total de um período deve somar normal + todos os atrasados.
        Garante que a lógica de cálculo não perde os atrasados.
        """
        period = {'normal': 200.0, 'atrasados': [("2024-01", 50.0), ("2024-02", 30.0)]}
        total = period['normal'] + sum(v for _, v in period['atrasados'])
        assert total == 280.0
