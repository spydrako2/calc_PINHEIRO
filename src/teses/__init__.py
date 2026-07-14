from .base_tese import BaseTese
from .tese_piso_docente import TesePisoDocente
from .tese_iamspe import TeseIAMSPE
from .tese_apeoesp import TeseApeoesp
from .tese_chs import TeseCHS
from .tese_ir_bonus import TeseIRBonus

TESES_DISPONIVEIS = {
    "piso_docente": TesePisoDocente,
    "iamspe": TeseIAMSPE,
    "apeoesp": TeseApeoesp,
    "chs": TeseCHS,
    "ir_bonus": TeseIRBonus,
}

__all__ = [
    "BaseTese", "TesePisoDocente", "TeseIAMSPE", "TeseApeoesp", "TeseCHS",
    "TeseIRBonus", "TESES_DISPONIVEIS",
]
