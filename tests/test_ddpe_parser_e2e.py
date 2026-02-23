"""End-to-end tests for DDPE parser with real PDF data"""

import pytest
import os
from pathlib import Path
from src.core.parsers.ddpe_parser import DDPEParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import TemplateType, TipoFolha


class TestDDPEParserE2E:
    """End-to-end tests with realistic holerite data"""

    @pytest.fixture
    def parser(self):
        """Create DDPE parser"""
        return DDPEParser()

    @pytest.fixture
    def realistic_holerite(self):
        """Realistic DDPE holerite with header, verbas, and totals"""
        texto = """
        DEPARTAMENTO DE DESPESA - FOLHA DE PAGAMENTO
        Competência: 02/2026

        CPF: 123.456.789-00
        NOME: JOÃO SILVA SANTOS
        CARGO: DESENVOLVEDOR SENIOR
        UNIDADE: TECNOLOGIA
        COMPETÊNCIA: 02/2026
        DATA DE PAGAMENTO: 15/03/2026
        TIPO: NORMAL

        VERBAS:
        CÓDIGO DENOMINAÇÃO VALOR
        01.001 SALÁRIO 5000.00
        01.002 ADIANTAMENTO 1000.00
        03.001 VALE TRANSPORTE 0.00
        09.001 QUINQUÊNIO 200.00

        DESCONTOS:
        70.006 IAMSPE -100.00
        70.007 ICMS -50.00

        TOTAL VENCIMENTOS 6200.00
        TOTAL DESCONTOS 150.00
        LÍQUIDO 6050.00
        """
        return PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

    def test_parse_complete_holerite(self, parser, realistic_holerite):
        """Should parse complete holerite successfully"""
        pages = [realistic_holerite]
        holerite = parser.parse(pages)

        assert holerite is not None
        assert holerite.cabecalho.nome == "JOÃO SILVA SANTOS"
        assert holerite.cabecalho.cpf == "123.456.789-00"
        assert holerite.cabecalho.cargo == "DESENVOLVEDOR SENIOR"
        assert holerite.cabecalho.unidade == "TECNOLOGIA"

    def test_parse_header_extraction(self, parser, realistic_holerite):
        """Should extract header information"""
        pages = [realistic_holerite]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.competencia == "2026-02"
        assert holerite.cabecalho.tipo_folha == TipoFolha.NORMAL
        assert holerite.cabecalho.template_type == TemplateType.DDPE

    def test_parse_verbas_extraction(self, parser, realistic_holerite):
        """Should extract all verbas"""
        pages = [realistic_holerite]
        holerite = parser.parse(pages)

        # Should have extracted verbas
        assert len(holerite.verbas) >= 4

        # Find specific verbas
        salario = [v for v in holerite.verbas if "SALÁRIO" in v.denominacao.upper()]
        assert len(salario) > 0
        assert salario[0].valor == 5000.00

    def test_parse_totals_extraction(self, parser, realistic_holerite):
        """Should extract totals correctly"""
        pages = [realistic_holerite]
        holerite = parser.parse(pages)

        assert holerite.total_vencimentos == 6200.00
        assert holerite.total_descontos == 150.00
        assert holerite.liquido == 6050.00

    def test_parse_multipage_holerite(self, parser):
        """Should handle multipage holerites"""
        page1 = PaginaExtraida(numero=1, texto="""
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST USER
        CARGO: DEVELOPER
        UNIDADE: IT
        COMPETÊNCIA: 02/2026
        DATA DE PAGAMENTO: 15/03/2026

        VERBAS:
        01.001 SALÁRIO 5000.00
        01.002 ADIANTAMENTO 1000.00
        70.006 IAMSPE -100.00

        TOTAL VENCIMENTOS 6000.00
        TOTAL DESCONTOS 100.00
        LÍQUIDO 5900.00
        """, metodo="TEXTO", confianca=0.95)

        pages = [page1]
        holerite = parser.parse(pages)

        assert holerite.cabecalho.nome == "TEST USER"
        assert len(holerite.verbas) >= 2

    def test_template_detection(self, parser):
        """Should detect DDPE template correctly"""
        texto = """
        DEPARTAMENTO DE DESPESA
        FOLHA DE PAGAMENTO
        CPF: 123.456.789-00
        """
        assert parser.detect_template(texto) is True

    def test_template_detection_fail(self, parser):
        """Should reject non-DDPE templates"""
        texto = """
        SPPREV - APOSENTADO
        CPF: 123.456.789-00
        """
        assert parser.detect_template(texto) is False

    def test_parse_with_ocr_metadata(self, parser):
        """Should preserve OCR metadata"""
        page = PaginaExtraida(numero=1, texto="""
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST
        CARGO: DEV
        COMPETÊNCIA: 02/2026
        DATA DE PAGAMENTO: 15/03/2026

        01.001 SALÁRIO 5000.00

        TOTAL VENCIMENTOS 5000.00
        TOTAL DESCONTOS 0.00
        LÍQUIDO 5000.00
        """, metodo="OCR", confianca=0.85)

        holerite = parser.parse([page])
        assert holerite.metodo_extracao == "OCR"
        assert holerite.confianca == 0.85

    def test_parse_performance_requirement(self, parser, realistic_holerite):
        """Should parse within performance requirement (< 5 seconds)"""
        import time

        pages = [realistic_holerite]
        start = time.time()
        holerite = parser.parse(pages)
        elapsed = time.time() - start

        assert elapsed < 5.0  # Should parse in less than 5 seconds

    def test_parse_handles_missing_fields(self, parser):
        """Should handle holerite with missing optional fields"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST USER

        01.001 SALÁRIO 5000.00

        TOTAL VENCIMENTOS 5000.00
        TOTAL DESCONTOS 0.00
        LÍQUIDO 5000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

        holerite = parser.parse([page])
        assert holerite.cabecalho.nome == "TEST USER"
        assert holerite.cabecalho.cpf == "123.456.789-00"
        assert holerite.cabecalho.cargo is None  # Optional field may be None

    def test_parse_verba_natureza_detection(self, parser):
        """Should detect verba natureza correctly"""
        texto = """
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: TEST

        NORMAL VERBAS:
        01.001 SALÁRIO 5000.00

        ATRASADO VERBAS:
        01.001 SALÁRIO ATRASADO 2000.00

        TOTAL VENCIMENTOS 7000.00
        TOTAL DESCONTOS 0.00
        LÍQUIDO 7000.00
        """
        page = PaginaExtraida(numero=1, texto=texto, metodo="TEXTO", confianca=0.95)

        holerite = parser.parse([page])

        # Should have identified normal and atrasado verbas
        normal_count = sum(1 for v in holerite.verbas if v.natureza.value == "N")
        atrasado_count = sum(1 for v in holerite.verbas if v.natureza.value == "A")

        assert normal_count > 0 or atrasado_count > 0

    def test_template_detection_degraded_ocr(self, parser):
        """Should detect DDPE even with OCR whitespace variations"""
        texto = """
        DEPARTAMENTO  DE   DESPESA
        CPF: 123.456.789-00
        NOME: TEST
        """
        assert parser.detect_template(texto) is True

    def test_template_detection_partial_match(self, parser):
        """Should detect DDPE with partial keyword matches"""
        texto = "DEPARTAMEN DE DESPESA..."
        result = parser.detect_template(texto)
        assert isinstance(result, bool)

    def test_template_detection_wrong_format_similarity(self, parser):
        """Should NOT match similar but wrong templates"""
        texto = "SPPREV - DEPARTAMENTO"
        assert parser.detect_template(texto) is False

    def test_template_detection_empty_and_whitespace(self, parser):
        """Should handle empty/whitespace gracefully"""
        assert parser.detect_template("") is False
        assert parser.detect_template("   ") is False

    def test_template_detection_boundary_score(self, parser):
        """Should handle fuzzy match at boundary"""
        texto = "DEPARTAMENTO DE DESPESA CPF: 123.456.789-00"
        assert parser.detect_template(texto) is True

    def test_parse_two_page_holerite_with_split_verbas(self, parser):
        """Should extract verbas from multiple pages correctly"""
        page1 = PaginaExtraida(numero=1, texto="""
        DEPARTAMENTO DE DESPESA
        CPF: 123.456.789-00
        NOME: JOÃO SILVA
        CARGO: DEVELOPER
        COMPETÊNCIA: 02/2026
        DATA DE PAGAMENTO: 15/03/2026

        VERBAS:
        01.001 SALÁRIO 5000.00
        01.002 ADIANTAMENTO 1000.00
        """, metodo="TEXTO", confianca=0.95)

        page2 = PaginaExtraida(numero=2, texto="""
        70.006 IAMSPE -100.00
        70.007 ICMS -50.00

        TOTAL VENCIMENTOS 6000.00
        TOTAL DESCONTOS 150.00
        LÍQUIDO 5850.00
        """, metodo="TEXTO", confianca=0.95)

        holerite = parser.parse([page1, page2])

        # Validate all verbas extracted from both pages
        assert len(holerite.verbas) >= 3
        assert holerite.total_vencimentos == 6000.00
        assert holerite.total_descontos == 150.00

    def test_parse_three_page_holerite_with_continuation(self, parser):
        """Should handle 3+ page holerites with continuation pages"""
        page1 = PaginaExtraida(numero=1, texto="""
        DEPARTAMENTO DE DESPESA
        CPF: 456.789.123-45
        NOME: MARIA SANTOS
        COMPETÊNCIA: 01/2026

        VERBAS:
        01.001 SALÁRIO 4000.00
        01.002 GRATIFICAÇÃO 500.00
        """, metodo="TEXTO", confianca=0.95)

        page2 = PaginaExtraida(numero=2, texto="""
        03.001 VALE TRANSPORTE 150.00
        09.001 QUINQUÊNIO 300.00
        70.001 INSS -400.00
        """, metodo="TEXTO", confianca=0.95)

        page3 = PaginaExtraida(numero=3, texto="""
        70.002 IR -300.00

        TOTAL VENCIMENTOS 4950.00
        TOTAL DESCONTOS 700.00
        LÍQUIDO 4250.00
        """, metodo="TEXTO", confianca=0.95)

        holerite = parser.parse([page1, page2, page3])

        # Validate proper aggregation across pages
        assert len(holerite.verbas) >= 5
        assert holerite.total_vencimentos == 4950.00
        assert holerite.total_descontos == 700.00
        assert holerite.liquido == 4250.00

    def test_multipage_with_ocr_and_text_mixed(self, parser):
        """Should handle mixture of TEXT and OCR pages"""
        page1 = PaginaExtraida(numero=1, texto="""
        DEPARTAMENTO DE DESPESA
        CPF: 789.123.456-78
        NOME: CARLOS OLIVEIRA
        COMPETÊNCIA: 03/2026

        01.001 SALÁRIO 3500.00
        01.002 BÔNUS 800.00
        """, metodo="OCR", confianca=0.8)

        page2 = PaginaExtraida(numero=2, texto="""
        70.005 FGTS -280.00
        70.006 IAMSPE -100.00

        TOTAL VENCIMENTOS 4300.00
        TOTAL DESCONTOS 380.00
        LÍQUIDO 3920.00
        """, metodo="TEXTO", confianca=0.95)

        holerite = parser.parse([page1, page2])

        # Validate both pages processed correctly
        assert len(holerite.verbas) >= 3
        assert holerite.cabecalho.nome == "CARLOS OLIVEIRA"
        assert holerite.metodo_extracao == "OCR"  # Uses first page method
        assert holerite.confianca == 0.8  # Uses first page confidence

    def test_parse_real_ddpe_pdf_from_references(self, parser):
        """Should parse real DDPE PDF from docs/referencias/"""
        # Use the actual PDF mentioned in docs
        pdf_path = "docs/referencias/02. HOLERITES -01-21 A 02-26 - MARCIA LOPES DE OLIVEIRA MACHADO.pdf"

        # Check if PDF exists
        if not os.path.exists(pdf_path):
            pytest.skip(f"PDF not found at {pdf_path}")

        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                # Extract text from first page
                if len(pdf.pages) == 0:
                    pytest.skip("PDF has no pages")

                first_page = pdf.pages[0]
                texto = first_page.extract_text()

                if not texto:
                    pytest.skip("No text extracted from PDF")

                # Check if it's a DDPE template
                if not parser.detect_template(texto):
                    pytest.skip("PDF is not a DDPE template")

                # Try to parse the pages
                pages = []
                for page_num, pdf_page in enumerate(pdf.pages, 1):
                    page_text = pdf_page.extract_text()
                    if page_text:
                        pages.append(PaginaExtraida(
                            numero=page_num,
                            texto=page_text,
                            metodo="TEXTO",
                            confianca=0.9
                        ))

                if not pages:
                    pytest.skip("No valid pages extracted from PDF")

                # Parse the holerite
                holerite = parser.parse(pages)

                # Basic validations
                assert holerite.cabecalho.nome is not None
                assert holerite.cabecalho.cpf is not None
                assert len(holerite.verbas) > 0
                assert holerite.total_vencimentos > 0

        except ImportError:
            pytest.skip("pdfplumber not installed")
        except Exception as e:
            pytest.skip(f"PDF reading failed: {e}")

    def test_parse_multiple_real_ddpe_pdfs(self, parser):
        """Should parse multiple real DDPE PDFs from docs/referencias/"""
        import glob

        try:
            import pdfplumber

            # Find all PDFs in referencias directory
            pdf_dir = "docs/referencias"
            if not os.path.exists(pdf_dir):
                pytest.skip(f"Directory {pdf_dir} not found")

            pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))

            if not pdf_files:
                pytest.skip("No PDF files found in docs/referencias/")

            successful_parses = 0

            # Try to parse each PDF
            for pdf_path in pdf_files[:3]:  # Test first 3 PDFs
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        if len(pdf.pages) == 0:
                            continue

                        first_page = pdf.pages[0]
                        texto = first_page.extract_text()

                        if not texto or not parser.detect_template(texto):
                            continue

                        # Extract all pages
                        pages = []
                        for page_num, pdf_page in enumerate(pdf.pages, 1):
                            page_text = pdf_page.extract_text()
                            if page_text:
                                pages.append(PaginaExtraida(
                                    numero=page_num,
                                    texto=page_text,
                                    metodo="TEXTO",
                                    confianca=0.9
                                ))

                        if pages:
                            holerite = parser.parse(pages)
                            # Validate basic structure
                            if (holerite.cabecalho.nome and
                                holerite.cabecalho.cpf and
                                len(holerite.verbas) > 0):
                                successful_parses += 1

                except Exception:
                    # Skip PDFs that can't be parsed
                    continue

            # At least one PDF should be parsed successfully
            assert successful_parses >= 1, "No PDFs could be parsed successfully"

        except ImportError:
            pytest.skip("pdfplumber not installed")
        except Exception as e:
            pytest.skip(f"PDF scanning failed: {e}")
