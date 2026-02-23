"""
Abstract base parser for holerite extraction
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import Holerite, CabecalhoHolerite, Verba


class BaseParser(ABC):
    """
    Abstract base class for holerite parsers

    Defines the interface that all specific parsers (DDPE, SPPREV, etc) must implement
    """

    def __init__(self):
        """Initialize parser"""
        self.paginas: List[PaginaExtraida] = []
        self.holerite: Optional[Holerite] = None

    @abstractmethod
    def detect_template(self, texto: str) -> bool:
        """
        Detect if text belongs to this parser's template

        Args:
            texto: Extracted text from page

        Returns:
            True if this parser can handle this template, False otherwise
        """
        pass

    @abstractmethod
    def parse(self, paginas: List[PaginaExtraida]) -> Holerite:
        """
        Parse extracted pages and return structured holerite data

        Args:
            paginas: List of extracted pages from PDF

        Returns:
            Holerite object with extracted data

        Raises:
            ValueError: If parsing fails or data validation fails
        """
        pass

    @abstractmethod
    def _extract_cabecalho(self) -> CabecalhoHolerite:
        """
        Extract header information (CPF, Nome, Cargo, etc)

        Returns:
            CabecalhoHolerite object
        """
        pass

    @abstractmethod
    def _extract_verbas(self) -> List[Verba]:
        """
        Extract earnings/deductions (verbas)

        Returns:
            List of Verba objects
        """
        pass

    @abstractmethod
    def _extract_totals(self) -> tuple:
        """
        Extract totals (vencimentos, descontos, líquido)

        Returns:
            Tuple of (vencimentos, descontos, liquido)
        """
        pass

    def _validate_holerite(self, holerite: Holerite) -> bool:
        """
        Validate extracted holerite data

        Args:
            holerite: Holerite object to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        if not holerite.cabecalho:
            raise ValueError("Cabeçalho is required")

        if not holerite.cabecalho.cpf:
            raise ValueError("CPF is required")

        if not holerite.cabecalho.nome:
            raise ValueError("Nome is required")

        if not holerite.verbas:
            raise ValueError("At least one verba is required")

        # Validate CPF format (basic check)
        cpf_clean = holerite.cabecalho.cpf.replace(".", "").replace("-", "")
        if not cpf_clean.isdigit() or len(cpf_clean) != 11:
            raise ValueError(f"Invalid CPF format: {holerite.cabecalho.cpf}")

        # Validate totals
        vencimentos = holerite.total_vencimentos
        descontos = holerite.total_descontos
        liquido = holerite.liquido

        # Check that values are numeric
        try:
            float(vencimentos)
            float(descontos)
            float(liquido)
        except (ValueError, TypeError):
            raise ValueError("Totals must be numeric")

        # Basic sanity check: liquido should be vencimentos - descontos
        # Allow small tolerance for rounding
        expected_liquido = vencimentos - descontos
        if abs(liquido - expected_liquido) > 0.01:
            raise ValueError(
                f"Líquido mismatch: {liquido} != {vencimentos} - {descontos}"
            )

        return True

    def get_first_page_text(self) -> str:
        """Get text from first page"""
        if not self.paginas or len(self.paginas) == 0:
            return ""
        return self.paginas[0].texto

    def get_continuation_pages(self) -> List[PaginaExtraida]:
        """Get pages that are continuation of holerite (page 2+)"""
        from src.core.pdf_reader import PDFReader

        continuation_pages = []
        for pagina in self.paginas[1:]:  # Skip first page
            if PDFReader.is_continuation_page(pagina.texto):
                continuation_pages.append(pagina)

        return continuation_pages
