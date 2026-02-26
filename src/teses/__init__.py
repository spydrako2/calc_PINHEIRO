from .base_tese import BaseTese
from .tese_piso_docente import TesePisoDocente
from .tese_iamspe import TeseIAMSPE
from .tese_apeoesp import TeseApeoesp

TESES_DISPONIVEIS = {
    "piso_docente": TesePisoDocente,
    "iamspe": TeseIAMSPE,
    "apeoesp": TeseApeoesp,
}

__all__ = ["BaseTese", "TesePisoDocente", "TeseIAMSPE", "TeseApeoesp", "TESES_DISPONIVEIS"]
