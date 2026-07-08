from .base_tese import BaseTese
from .tese_piso_docente import TesePisoDocente
from .tese_iamspe import TeseIAMSPE
from .tese_apeoesp import TeseApeoesp
from .tese_chs import TeseCHS

TESES_DISPONIVEIS = {
    "piso_docente": TesePisoDocente,
    "iamspe": TeseIAMSPE,
    "apeoesp": TeseApeoesp,
    "chs": TeseCHS,
}

__all__ = ["BaseTese", "TesePisoDocente", "TeseIAMSPE", "TeseApeoesp", "TeseCHS", "TESES_DISPONIVEIS"]
