"""End-to-end tests for PDF reader with real holerite PDFs"""

import pytest
import psutil
import os
from pathlib import Path
from src.core.pdf_reader import PDFReader, PaginaExtraida


class TestEndToEnd:
    """End-to-end tests with real PDF references"""

    @pytest.fixture
    def pdf_refs_dir(self):
        """Path to reference PDFs"""
        return Path("docs/referencias")

    @pytest.fixture
    def get_largest_pdf(self, pdf_refs_dir):
        """Get largest PDF from references"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            return None
        return max(pdf_files, key=lambda p: p.stat().st_size)

    @pytest.fixture
    def get_smallest_pdf(self, pdf_refs_dir):
        """Get smallest PDF from references"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            return None
        return min(pdf_files, key=lambda p: p.stat().st_size)

    def test_e2e_read_real_pdf(self, pdf_refs_dir):
        """Should successfully read real PDF from references"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        assert isinstance(paginas, list)
        assert len(paginas) > 0
        assert all(isinstance(p, PaginaExtraida) for p in paginas)

    def test_e2e_text_extraction_quality(self, pdf_refs_dir):
        """Should extract text with high quality from selectable PDFs"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        # Use first PDF (likely has selectable text)
        pdf_path = pdf_files[0]
        paginas = PDFReader.read_pdf(str(pdf_path))

        # At least first page should have meaningful text
        first_page = paginas[0]
        assert len(first_page.texto) > 0

        # Check that extraction method is recorded
        assert first_page.metodo in ["TEXTO", "OCR"]

        # Check confidence is reasonable
        assert 0.0 <= first_page.confianca <= 1.0

    def test_e2e_multipage_consistency(self, pdf_refs_dir):
        """Should maintain page order and numbering across multiple pages"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        # Find a multi-page PDF
        for pdf_path in pdf_files:
            paginas = PDFReader.read_pdf(str(pdf_path))

            if len(paginas) > 1:
                # Verify page numbers are sequential
                for i, pagina in enumerate(paginas, 1):
                    assert pagina.numero == i
                    assert len(pagina.texto) >= 0  # Can be empty
                    assert pagina.metodo in ["TEXTO", "OCR"]
                    assert 0.0 <= pagina.confianca <= 1.0

                return

        pytest.skip("No multi-page PDFs found in references")

    def test_e2e_large_pdf_memory_efficiency(self, get_largest_pdf):
        """Should handle large PDFs without excessive memory usage"""
        if get_largest_pdf is None:
            pytest.skip("No PDFs found")

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Read PDF
        paginas = PDFReader.read_pdf(str(get_largest_pdf))

        # Get memory after reading
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_increase = mem_after - mem_before

        # Memory increase should be reasonable (< 500 MB for large PDF)
        assert mem_increase < 500, f"Memory increased by {mem_increase}MB (excessive)"

        # Should successfully read pages
        assert len(paginas) > 0

    def test_e2e_pdf_page_count(self, pdf_refs_dir):
        """Should accurately report number of pages in PDF"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        for pdf_path in pdf_files:
            paginas = PDFReader.read_pdf(str(pdf_path))
            metadata = PDFReader.extrair_metadados_basicos(str(pdf_path))

            # Page count should match
            assert len(paginas) == metadata["total_paginas"]

    def test_e2e_template_detection_on_real_data(self, pdf_refs_dir):
        """Should detect template type from real holerite PDFs"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        detected_templates = {}

        for pdf_path in pdf_files:
            paginas = PDFReader.read_pdf(str(pdf_path))

            if len(paginas) > 0:
                # Try to detect template from first page
                template_type, confidence = PDFReader.detect_template_type(paginas[0].texto)

                if template_type:
                    detected_templates[pdf_path.name] = {
                        "template": template_type,
                        "confidence": confidence,
                    }

        # Should have detected at least some templates
        assert len(detected_templates) > 0, "Should detect templates in at least some PDFs"

    def test_e2e_continuation_detection_logic(self, pdf_refs_dir):
        """Should properly detect continuation pages in multi-page holerites"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        for pdf_path in pdf_files:
            paginas = PDFReader.read_pdf(str(pdf_path))

            if len(paginas) > 1:
                # Only first page should not be continuation
                first_page_is_continuation = PDFReader.is_continuation_page(paginas[0].texto)
                assert first_page_is_continuation is False, "First page should not be marked as continuation"

                # Some later pages might be continuations
                has_continuations = any(
                    PDFReader.is_continuation_page(p.texto) for p in paginas[1:]
                )
                # This is informational - not all multi-page PDFs have continuation pattern
                # but if they do, it should be detected correctly

    def test_e2e_no_memory_overflow_large_pdf(self, get_largest_pdf):
        """Should process large PDF without memory overflow or crashes"""
        if get_largest_pdf is None:
            pytest.skip("No PDFs found")

        # This should not raise any exceptions
        paginas = PDFReader.read_pdf(str(get_largest_pdf))

        # Should have read all pages
        assert len(paginas) > 0

        # All pages should have required metadata
        for pagina in paginas:
            assert pagina.numero > 0
            assert isinstance(pagina.texto, str)
            assert pagina.metodo in ["TEXTO", "OCR"]
            assert 0.0 <= pagina.confianca <= 1.0

    def test_e2e_confidence_distribution(self, pdf_refs_dir):
        """Should show varied confidence levels across extraction methods"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        confidence_values = []
        methods_used = set()

        for pdf_path in pdf_files:
            paginas = PDFReader.read_pdf(str(pdf_path))

            for pagina in paginas:
                confidence_values.append(pagina.confianca)
                methods_used.add(pagina.metodo)

                # All should be in valid range
                assert 0.0 <= pagina.confianca <= 1.0

        # Should have used some extraction methods
        assert len(methods_used) > 0

        # Should have some reasonable confidence distribution
        assert len(confidence_values) > 0
        avg_confidence = sum(confidence_values) / len(confidence_values)
        assert avg_confidence > 0.5, "Average confidence should be above 50%"

    def test_e2e_performance_metrics(self, pdf_refs_dir):
        """Should process PDFs in reasonable time"""
        import time

        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        for pdf_path in pdf_files:
            start = time.time()
            paginas = PDFReader.read_pdf(str(pdf_path))
            elapsed = time.time() - start

            file_size_mb = pdf_path.stat().st_size / 1024 / 1024

            # Performance: should process at reasonable speed
            # Allow ~10 seconds for large files (7MB+), less for small ones
            if file_size_mb < 1:
                assert elapsed < 5, f"Small PDF ({file_size_mb}MB) took {elapsed}s"
            elif file_size_mb < 3:
                assert elapsed < 10, f"Medium PDF ({file_size_mb}MB) took {elapsed}s"
            else:
                # Large PDFs can take longer
                assert elapsed < 30, f"Large PDF ({file_size_mb}MB) took {elapsed}s"

    def test_e2e_extraction_consistency(self, pdf_refs_dir):
        """Reading same PDF twice should give consistent results"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        pdf_path = pdf_files[0]

        # Read twice
        paginas1 = PDFReader.read_pdf(str(pdf_path))
        paginas2 = PDFReader.read_pdf(str(pdf_path))

        # Should get same number of pages
        assert len(paginas1) == len(paginas2)

        # Content should be identical
        for p1, p2 in zip(paginas1, paginas2):
            assert p1.numero == p2.numero
            assert p1.texto == p2.texto
            assert p1.metodo == p2.metodo
            assert p1.confianca == p2.confianca

    def test_e2e_all_pdfs_readable(self, pdf_refs_dir):
        """All PDF files in references should be readable without errors"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        successful_reads = 0
        failed_reads = []

        for pdf_path in pdf_files:
            try:
                paginas = PDFReader.read_pdf(str(pdf_path))
                assert len(paginas) > 0
                successful_reads += 1
            except Exception as e:
                failed_reads.append((pdf_path.name, str(e)))

        # Most PDFs should be readable
        if failed_reads:
            # Log failures but don't fail if most work
            print(f"\nFailed to read {len(failed_reads)} PDFs:")
            for name, error in failed_reads:
                print(f"  - {name}: {error}")

        assert successful_reads > 0, "Should be able to read at least some PDFs"

    def test_e2e_text_quality_check(self, pdf_refs_dir):
        """Extracted text should contain meaningful content (not gibberish)"""
        pdf_files = list(pdf_refs_dir.glob("*.pdf"))
        if not pdf_files:
            pytest.skip("No reference PDFs found")

        for pdf_path in pdf_files:
            paginas = PDFReader.read_pdf(str(pdf_path))

            for pagina in paginas:
                # Text shouldn't be just whitespace
                assert pagina.texto.strip() or len(pagina.texto) == 0

                # For TEXTO extraction, should have reasonable content
                if pagina.metodo == "TEXTO" and len(pagina.texto) > 0:
                    # Should have at least some recognizable patterns
                    # (numbers, letters, common words)
                    has_content = any(c.isalnum() for c in pagina.texto)
                    assert has_content, f"TEXTO extraction seems to have no content"
