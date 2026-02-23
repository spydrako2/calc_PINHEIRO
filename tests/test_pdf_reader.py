"""Tests for pdf_reader.py"""

import pytest
from pathlib import Path
from src.core.pdf_reader import PDFReader, PaginaExtraida


class TestPDFReader:
    """Test PDF reading with pdfplumber"""

    @pytest.fixture
    def pdf_refs_dir(self):
        """Path to reference PDFs"""
        return Path("docs/referencias")

    def test_pdf_reader_initialization(self):
        """PDFReader should initialize without errors"""
        reader = PDFReader()
        assert reader is not None
        assert PDFReader.LIMIAR_MINIMO_CHARS == 50
        assert PDFReader.CONFIANCA_TEXTO == 0.95
        assert PDFReader.CONFIANCA_OCR == 0.70

    def test_read_pdf_not_found(self):
        """Should raise FileNotFoundError for non-existent PDF"""
        with pytest.raises(FileNotFoundError):
            PDFReader.read_pdf("nao_existe.pdf")

    def test_read_pdf_returns_list(self, pdf_refs_dir):
        """Should return list of PaginaExtraida objects"""
        # Find first available PDF
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        assert isinstance(paginas, list)
        assert len(paginas) > 0

    def test_pagina_extraida_structure(self, pdf_refs_dir):
        """PaginaExtraida should have correct structure"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        pagina = paginas[0]
        assert isinstance(pagina, PaginaExtraida)
        assert hasattr(pagina, "numero")
        assert hasattr(pagina, "texto")
        assert hasattr(pagina, "metodo")
        assert hasattr(pagina, "confianca")
        assert pagina.numero == 1
        assert pagina.metodo in ["TEXTO", "OCR"]
        assert 0.0 <= pagina.confianca <= 1.0

    def test_extrair_texto_basic(self, pdf_refs_dir):
        """Should extract text from page"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        # At least first page should have some text
        # (if it's a real holerite PDF)
        assert len(paginas[0].texto) > 0

    def test_metadados_basicos(self, pdf_refs_dir):
        """Should extract basic metadata"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        meta = PDFReader.extrair_metadados_basicos(str(pdf_path))

        assert "total_paginas" in meta
        assert meta["total_paginas"] > 0

    def test_read_pdf_multipage(self, pdf_refs_dir):
        """Should handle multi-page PDFs"""
        # Look for a larger PDF
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        # Try to find a multi-page PDF
        for pdf_path in pdf_files:
            paginas = PDFReader.read_pdf(str(pdf_path))
            if len(paginas) > 1:
                # Verify each page has correct numero
                for i, pagina in enumerate(paginas, 1):
                    assert pagina.numero == i
                return

        # If no multi-page PDF found, that's ok
        pytest.skip("No multi-page PDFs found in references")

    def test_read_pdf_page_order(self, pdf_refs_dir):
        """Pages should be in correct order"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        # Verify page numbers are sequential
        for i, pagina in enumerate(paginas, 1):
            assert pagina.numero == i

    def test_confianca_values(self, pdf_refs_dir):
        """Confidence values should reflect extraction method"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        for pagina in paginas:
            # Confidence should be in valid range
            assert 0.0 <= pagina.confianca <= 1.0

            if pagina.metodo == "TEXTO":
                # Text extraction confidence: high (0.95) or low (0.3)
                assert pagina.confianca in [0.95, 0.3]
            elif pagina.metodo == "OCR":
                assert pagina.confianca == PDFReader.CONFIANCA_OCR
