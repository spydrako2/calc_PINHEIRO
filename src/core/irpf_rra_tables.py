"""
Tabelas progressivas do IRPF para cálculo de Rendimentos Recebidos
Acumuladamente (RRA), usadas na tese de IR sobre Bônus.

A tese recalcula o IR de um bônus pago de uma vez (mas referente a vários
meses) como se tivesse sido diluído nos meses de referência — o que costuma
derrubar a faixa de tributação. A tabela IRPF aplicável é escolhida pela
DATA DE PAGAMENTO do bônus (não pela competência de referência).

Fonte: aba "Dados" das planilhas modelo (Pinheiro), replicando as tabelas
oficiais da Receita Federal vigentes em cada intervalo.
"""

from typing import NamedTuple

# Dedução por dependente (valor mensal vigente no período RRA das planilhas).
DEDUCAO_POR_DEPENDENTE = 189.59


class Faixa(NamedTuple):
    limite_inf: float
    limite_sup: float
    aliquota: float          # 0.075 = 7,5%
    parcela_deduzir: float
    descricao: str


# Cada "ano-calendário" é uma versão da tabela, com 5 faixas.
TABELAS = {
    "Ano_2015": [  # Tabela de IRRF de 04/2015 a 04/2023
        Faixa(0.0, 1903.98, 0.0, 0.0, "Até R$ 1.903,98"),
        Faixa(1903.99, 2826.65, 0.075, 122.78, "De R$ 1.903,99 até R$ 2.826,65"),
        Faixa(2826.66, 3751.05, 0.15, 306.80, "De R$ 2.826,66 até R$ 3.751,05"),
        Faixa(3751.06, 4664.68, 0.225, 552.15, "De R$ 3.751,06 até R$ 4.664,68"),
        Faixa(4664.69, 9999999.0, 0.275, 756.53, "Acima de R$ 4.664,68"),
    ],
    "Ano_2023": [  # Tabela de IRRF de 05/2023 a 01/2024
        Faixa(0.0, 2112.00, 0.0, 0.0, "Até R$ 2.112,00"),
        Faixa(2112.01, 2826.65, 0.075, 158.40, "De R$ 2.112,01 até R$ 2.826,65"),
        Faixa(2826.66, 3751.05, 0.15, 370.40, "De R$ 2.826,66 até R$ 3.751,05"),
        Faixa(3751.06, 4664.68, 0.225, 651.73, "De R$ 3.751,06 até R$ 4.664,68"),
        Faixa(4664.69, 9999999.0, 0.275, 884.96, "Acima de R$ 4.664,68"),
    ],
    "Ano_2024": [  # Tabela de IRRF de 02/2024 a 04/2025
        Faixa(0.0, 2259.20, 0.0, 0.0, "Até R$ 2.259,20"),
        Faixa(2259.21, 2826.65, 0.075, 169.44, "De R$ 2.259,21 até R$ 2.826,65"),
        Faixa(2826.66, 3751.05, 0.15, 381.44, "De R$ 2.826,66 até R$ 3.751,05"),
        Faixa(3751.06, 4664.68, 0.225, 662.77, "De R$ 3.751,06 até R$ 4.664,68"),
        Faixa(4664.69, 9999999.0, 0.275, 896.00, "Acima de R$ 4.664,68"),
    ],
    "Ano_2025": [  # Tabela de IRRF de 05/2025 a 05/2026
        Faixa(0.0, 2428.80, 0.0, 0.0, "Até R$ 2.428,80"),
        Faixa(2428.81, 2826.65, 0.075, 182.16, "De R$ 2.428,81 até R$ 2.826,65"),
        Faixa(2826.66, 3751.05, 0.15, 394.16, "De R$ 2.826,66 até R$ 3.751,05"),
        Faixa(3751.06, 4664.68, 0.225, 675.49, "De R$ 3.751,06 até R$ 4.664,68"),
        Faixa(4664.69, 9999999.0, 0.275, 908.73, "Acima de R$ 4.664,69"),
    ],
}


def ano_calendario(pagamento_yyyy_mm: str) -> str:
    """
    Escolhe a versão da tabela IRPF pela data de pagamento (competência do
    holerite suplementar + 1 mês). Os limiares caem sempre no dia 1º de um mês,
    então a granularidade de mês (YYYY-MM) é suficiente.
    """
    yyyy, mm = pagamento_yyyy_mm.split("-")
    ordinal = int(yyyy) * 12 + int(mm)   # mês absoluto, comparável
    if ordinal < 2023 * 12 + 5:          # antes de 05/2023
        return "Ano_2015"
    if ordinal < 2024 * 12 + 2:          # antes de 02/2024
        return "Ano_2023"
    if ordinal < 2025 * 12 + 5:          # antes de 05/2025
        return "Ano_2024"
    return "Ano_2025"


def faixa_para_base(base_calculo: float, ano: str) -> Faixa:
    """Retorna a Faixa da tabela `ano` em que a base de cálculo se enquadra."""
    for f in TABELAS[ano]:
        if f.limite_inf <= base_calculo <= f.limite_sup:
            return f
    # base acima do teto (não deve ocorrer: última faixa vai a ~10M)
    return TABELAS[ano][-1]


def ir_devido_rra(bonus: float, n_meses: int, ano: str, dependentes: int = 0) -> dict:
    """
    Calcula o IR devido pelo regime RRA para uma parcela de bônus.

    base_bruta   = bonus / n_meses
    base_calculo = base_bruta − dependentes × dedução
    ir_devido    = máx(0, (base_calculo × alíquota − parcela_deduzir) × n_meses)

    Retorna dict com todos os intermediários (para o writer/planilha).
    """
    if n_meses <= 0:
        return {
            'base_bruta': 0.0, 'deducao_dep': 0.0, 'base_calculo': 0.0,
            'faixa': '', 'aliquota': 0.0, 'parcela_deduzir': 0.0, 'ir_devido': 0.0,
        }
    base_bruta = bonus / n_meses
    deducao_dep = dependentes * DEDUCAO_POR_DEPENDENTE
    # A dedução por dependente não pode tornar a base negativa (piso em 0).
    base_calculo = max(0.0, base_bruta - deducao_dep)
    f = faixa_para_base(base_calculo, ano)
    ir_devido = max(0.0, (base_calculo * f.aliquota - f.parcela_deduzir) * n_meses)
    return {
        'base_bruta': base_bruta,
        'deducao_dep': deducao_dep,
        'base_calculo': base_calculo,
        'faixa': f.descricao,
        'aliquota': f.aliquota,
        'parcela_deduzir': f.parcela_deduzir,
        'ir_devido': ir_devido,
    }
