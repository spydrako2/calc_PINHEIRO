"""
PDF Reader with hybrid text/OCR extraction
"""
import pdfplumber
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class PaginaExtraida:
    """Extracted page with metadata"""
    numero: int
    texto: str
    metodo: str  # "TEXTO" or "OCR"
    confianca: float  # 0.0-1.0


class PDFReader:
    """Read PDFs with pdfplumber (iterative, no memory overflow)"""

    # Text extraction confidence thresholds
    CONFIANCA_TEXTO = 0.95
    CONFIANCA_OCR = 0.70
    LIMIAR_MINIMO_CHARS = 50  # If < 50 chars, try OCR

    @staticmethod
    def read_pdf(pdf_path: str) -> List[PaginaExtraida]:
        """
        Read PDF page by page (iterative, no memory overflow)

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of PaginaExtraida objects with extracted text and metadata

        Raises:
            FileNotFoundError: If PDF file not found
            Exception: If PDF cannot be read
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        paginas = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    # Try text extraction first
                    texto = PDFReader._extrair_texto(page)

                    # Determine method and confidence
                    if len(texto) >= PDFReader.LIMIAR_MINIMO_CHARS:
                        metodo = "TEXTO"
                        confianca = PDFReader.CONFIANCA_TEXTO
                    else:
                        # Would use OCR here in Task 2
                        # For now, mark as low confidence text
                        metodo = "TEXTO"
                        confianca = 0.5

                    pagina = PaginaExtraida(
                        numero=i,
                        texto=texto,
                        metodo=metodo,
                        confianca=confianca,
                    )
                    paginas.append(pagina)

        except Exception as e:
            raise Exception(f"Error reading PDF {pdf_path}: {str(e)}")

        return paginas

    @staticmethod
    def _extrair_texto(page) -> str:
        """
        Extract text from PDF page using pdfplumber

        Args:
            page: pdfplumber page object

        Returns:
            Extracted text (cleaned)
        """
        try:
            texto = page.extract_text()
            if texto is None:
                return ""

            # Clean up whitespace but preserve structure
            lines = [line.strip() for line in texto.split("\n")]
            texto_limpo = "\n".join(line for line in lines if line)

            return texto_limpo
        except Exception:
            return ""

    @staticmethod
    def get_page_image(page):
        """
        Get page as image (for OCR processing in Task 2)

        Args:
            page: pdfplumber page object

        Returns:
            PIL Image object or None if fails
        """
        try:
            # Convert page to image
            im = page.to_image()
            return im
        except Exception:
            return None

    @staticmethod
    def extrair_metadados_basicos(pdf_path: str) -> Dict[str, Any]:
        """
        Extract basic metadata from PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with metadata: total_pages, metadata dict, etc.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return {
                    "total_paginas": len(pdf.pages),
                    "metadados": pdf.metadata,
                }
        except Exception as e:
            return {
                "total_paginas": 0,
                "metadados": {},
                "erro": str(e),
            }
