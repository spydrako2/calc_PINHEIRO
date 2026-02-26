from .base_tese import BaseTese
from .tese_art133 import TeseArt133
from .tese_piso_docente import TesePisoDocente
from .tese_iamspe import TeseIAMSPE
from .tese_apeoesp import TeseApeoesp

TESES_DISPONIVEIS = {
    "art133": TeseArt133,
    "piso_docente": TesePisoDocente,
    "iamspe": TeseIAMSPE,
    "apeoesp": TeseApeoesp,
}

__all__ = ["BaseTese", "TeseArt133", "TesePisoDocente", "TeseIAMSPE", "TeseApeoesp", "TESES_DISPONIVEIS"]
