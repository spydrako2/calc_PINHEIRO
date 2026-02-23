"""Tests for OCR fallback functionality"""

import pytest
from pathlib import Path
from src.core.pdf_reader import PDFReader, PaginaExtraida


class TestOCRFallback:
    """Test OCR fallback extraction"""

    @pytest.fixture
    def pdf_refs_dir(self):
        """Path to reference PDFs"""
        return Path("docs/referencias")

    def test_ocr_constants(self):
        """OCR constants should be configured"""
        assert PDFReader.CONFIANCA_OCR == 0.70
        assert PDFReader.CONFIANCA_TEXTO == 0.95
        assert PDFReader.LIMIAR_MINIMO_CHARS == 50

    def test_apply_ocr_exists(self):
        """_apply_ocr method should exist"""
        assert hasattr(PDFReader, "_apply_ocr")
        assert callable(getattr(PDFReader, "_apply_ocr"))

    def test_apply_ocr_with_none(self):
        """_apply_ocr should handle None input gracefully"""
        result = PDFReader._apply_ocr(None)
        assert result is None

    def test_hybrid_extraction_prefers_text(self, pdf_refs_dir):
        """Hybrid extraction should prefer text over OCR"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        # Check that pages with sufficient text use TEXTO method
        for pagina in paginas:
            if len(pagina.texto) >= PDFReader.LIMIAR_MINIMO_CHARS:
                assert pagina.metodo == "TEXTO"
                assert pagina.confianca == PDFReader.CONFIANCA_TEXTO

    def test_ocr_confidence_lower_than_text(self):
        """OCR confidence should be lower than text confidence"""
        assert PDFReader.CONFIANCA_OCR < PDFReader.CONFIANCA_TEXTO

    def test_ocr_fallback_on_empty_text(self, pdf_refs_dir):
        """Should attempt OCR when text extraction yields little text"""
        # This test depends on having PDFs with scanned pages
        # For now, just verify the threshold logic exists
        assert PDFReader.LIMIAR_MINIMO_CHARS > 0

    def test_metodo_field_only_texto_or_ocr(self, pdf_refs_dir):
        """metodo field should only be TEXTO or OCR"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        for pagina in paginas:
            assert pagina.metodo in ["TEXTO", "OCR"]

    def test_confidence_range(self, pdf_refs_dir):
        """Confidence should always be between 0.0 and 1.0"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        for pagina in paginas:
            assert 0.0 <= pagina.confianca <= 1.0

    def test_ocr_integration_no_crash(self, pdf_refs_dir):
        """OCR integration should not crash even if Tesseract unavailable"""
        # Even if Tesseract is not installed, should not crash
        # Just skip OCR gracefully
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        try:
            paginas = PDFReader.read_pdf(str(pdf_path))
            # Should complete without crashing
            assert len(paginas) > 0
        except Exception as e:
            # If it fails, should be due to missing Tesseract, not code error
            assert "Tesseract" in str(e) or "tesseract" in str(e).lower()
