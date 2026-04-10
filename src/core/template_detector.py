"""
Template detector — centralized template detection for HoleritePRO.

Priority order: Pensionista > Aposentado > DDPE Imagem > DDPE (most specific first)
"""

from typing import Optional, Tuple
from src.core.data_model import TemplateType
from src.core.parsers.base_parser import BaseParser
from src.core.parsers.ddpe_parser import DDPEParser
from src.core.parsers.ddpe_ativo_imagem_parser import DDPEAtivoImagemParser
from src.core.parsers.spprev_aposentado_parser import SpprevAposentadoParser
from src.core.parsers.spprev_pensionista_parser import SpprevPensionistaParser


class TemplateDetector:
    """
    Centralized template detection.

    Uses each parser's detect_template() internally.
    Priority: Pensionista > Aposentado > DDPE Imagem > DDPE (most specific first to avoid
    SPPREV Aposentado matching Pensionista documents, and DDPE Imagem before DDPE text).
    """

    def __init__(self):
        # Ordered by priority: most specific first
        self._detectors: list[Tuple[TemplateType, BaseParser]] = [
            (TemplateType.SPPREV_PENSIONISTA, SpprevPensionistaParser()),
            (TemplateType.SPPREV_APOSENTADO, SpprevAposentadoParser()),
            # DDPEAtivoImagemParser antes do DDPEParser: requer marcadores mobile extras
            (TemplateType.DDPE, DDPEAtivoImagemParser()),
            (TemplateType.DDPE, DDPEParser()),
        ]

    def detect(self, texto: str) -> Optional[TemplateType]:
        """
        Detect template type from page text.

        Args:
            texto: Extracted text from a PDF page

        Returns:
            TemplateType or None if no template matches
        """
        if not texto or len(texto.strip()) < 20:
            return None

        for template_type, parser in self._detectors:
            if parser.detect_template(texto):
                return template_type

        return None

    def get_parser(self, template_type: TemplateType) -> BaseParser:
        """
        Get parser instance for a given template type.

        For DDPE, returns DDPEAtivoImagemParser if the text contains mobile markers,
        otherwise falls back to standard DDPEParser.

        Args:
            template_type: The detected template type

        Returns:
            Parser instance
        """
        parsers = {
            TemplateType.DDPE: DDPEParser,
            TemplateType.SPPREV_APOSENTADO: SpprevAposentadoParser,
            TemplateType.SPPREV_PENSIONISTA: SpprevPensionistaParser,
        }
        return parsers[template_type]()

    def get_parser_for_text(self, template_type: TemplateType, texto: str) -> BaseParser:
        """
        Get the most specific parser for a given template type and text.

        For DDPE text from OCR (mobile screenshots), returns DDPEAtivoImagemParser.
        """
        if template_type == TemplateType.DDPE:
            imagem_parser = DDPEAtivoImagemParser()
            if imagem_parser.detect_template(texto):
                return imagem_parser
            return DDPEParser()
        parsers = {
            TemplateType.SPPREV_APOSENTADO: SpprevAposentadoParser,
            TemplateType.SPPREV_PENSIONISTA: SpprevPensionistaParser,
        }
        return parsers[template_type]()
