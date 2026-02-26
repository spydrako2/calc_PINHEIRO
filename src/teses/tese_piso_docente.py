"""Tese: Piso Salarial Docente (Decreto 62.500/2017) + Reflexo de Quinquênios"""

from .base_tese import BaseTese


class TesePisoDocente(BaseTese):
    nome = "Piso Salarial Docente"
    descricao = (
        "Reflexo dos adicionais temporais (quinquênios) sobre o Piso Salarial "
        "Docente instituído pelo Decreto 62.500/2017."
    )
    verba_codigo = "001035"
    verba_nome = "PISO SAL.DOCENTE (R$)"
