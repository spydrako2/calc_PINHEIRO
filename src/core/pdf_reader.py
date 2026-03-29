"""
PDF Reader with hybrid text/OCR extraction
Motor primário: PyMuPDF (fitz) — ~10-20x mais rápido que pdfplumber
Fallback OCR: pytesseract para páginas escaneadas
"""
import fitz  # PyMuPDF
import pdfplumber  # mantido apenas para extrair_metadados_basicos
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from fuzzywuzzy import fuzz


@dataclass
class PaginaExtraida:
    """Extracted page with metadata"""
    numero: int
    texto: str
    metodo: str  # "TEXTO" or "OCR"
    confianca: float  # 0.0-1.0


class PDFReader:
    """Read PDFs with PyMuPDF (iterative, no memory overflow)"""

    # Text extraction confidence thresholds
    CONFIANCA_TEXTO = 0.95
    CONFIANCA_OCR = 0.70
    LIMIAR_MINIMO_CHARS = 50  # If < 50 chars, try OCR

    # Fuzzy matching thresholds
    FUZZY_MATCH_THRESHOLD = 0.75  # 75% match = valid match

    @staticmethod
    def read_pdf(pdf_path: str) -> List[PaginaExtraida]:
        """
        Read PDF page by page usando PyMuPDF (fitz) — motor rápido.
        Fallback para OCR via pytesseract em páginas sem texto suficiente.

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
            doc = fitz.open(str(pdf_path))
            for i, page in enumerate(doc, 1):
                texto = PDFReader._extrair_texto_fitz(page)

                if len(texto) >= PDFReader.LIMIAR_MINIMO_CHARS:
                    metodo = "TEXTO"
                    confianca = PDFReader.CONFIANCA_TEXTO
                else:
                    texto_ocr = PDFReader._apply_ocr_fitz(page)
                    if texto_ocr:
                        texto = texto_ocr
                        metodo = "OCR"
                        confianca = PDFReader.CONFIANCA_OCR
                    else:
                        metodo = "TEXTO"
                        confianca = 0.3

                paginas.append(PaginaExtraida(
                    numero=i,
                    texto=texto,
                    metodo=metodo,
                    confianca=confianca,
                ))
            doc.close()

        except Exception as e:
            raise Exception(f"Error reading PDF {pdf_path}: {str(e)}")

        return paginas

    @staticmethod
    def _extrair_texto_fitz(page) -> str:
        """Extrai texto de página fitz agrupando palavras por linha (Y → X).

        Usa get_text('words') para reconstruir linhas com a mesma lógica do pdfplumber:
        palavras com Y próximo (<= 3px de diferença) são agrupadas na mesma linha,
        depois ordenadas por X para preservar a ordem das colunas.
        """
        try:
            from collections import defaultdict
            words = page.get_text("words")  # (x0, y0, x1, y1, word, ...)
            # Agrupar por Y arredondado (tolerância de pixel natural do round())
            line_map = defaultdict(list)
            for w in words:
                y_key = round(w[1])
                line_map[y_key].append((w[0], w[4]))
            lines = []
            for y in sorted(line_map.keys()):
                words_sorted = sorted(line_map[y], key=lambda x: x[0])
                linha = " ".join(w for _, w in words_sorted)
                if linha.strip():
                    lines.append(linha)
            return "\n".join(lines)
        except Exception:
            return ""

    @staticmethod
    def _apply_ocr_fitz(page) -> Optional[str]:
        """OCR via renderização de página fitz → imagem → pytesseract."""
        try:
            import pytesseract
            from PIL import Image
            mat = fitz.Matrix(2, 2)  # 2x scale para melhor OCR
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texto = pytesseract.image_to_string(img)
            if not texto or len(texto.strip()) == 0:
                return None
            lines = [line.strip() for line in texto.split("\n")]
            return "\n".join(line for line in lines if line) or None
        except Exception:
            return None

    # --- Métodos legados mantidos para compatibilidade ---

    @staticmethod
    def _extrair_texto(page) -> str:
        """Legado: extrai texto de página pdfplumber."""
        try:
            texto = page.extract_text()
            if texto is None:
                return ""
            lines = [line.strip() for line in texto.split("\n")]
            return "\n".join(line for line in lines if line)
        except Exception:
            return ""

    @staticmethod
    def get_page_image(page):
        """Legado: retorna imagem de página pdfplumber."""
        try:
            return page.to_image()
        except Exception:
            return None

    @staticmethod
    def is_continuation_page(texto: str) -> bool:
        """
        Detect if page is continuation of previous holerite (page 2+)

        Heuristics:
        - Cabeçalho vazio (no common header fields)
        - Tabela de verbas presente (códigos numéricos + valores)

        Args:
            texto: Extracted text from page

        Returns:
            True if page appears to be continuation, False otherwise
        """
        if not texto or len(texto.strip()) < 20:
            return False

        # Check for header indicators (if present, not continuation)
        header_indicators = [
            "CPF",
            "COMPETÊNCIA",
            "COMPETENCIA",
            "NOME:",
            "HOLERITE",
            "FOLHA",
        ]

        has_header = any(indicator.lower() in texto.lower() for indicator in header_indicators)

        # Check for verba table indicators
        # Lines with patterns like "XX.XXX" or "XXXXXX" followed by numbers
        has_verba_table = any(
            pattern in texto.lower()
            for pattern in ["código", "codigo", "verba", "denominação", "denominacao"]
        )

        # Continuation: has verba table but no header
        is_continuation = has_verba_table and not has_header

        return is_continuation

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

    @staticmethod
    def fuzzy_match(text1: str, text2: str, threshold: float = None) -> Tuple[bool, float]:
        """
        Perform fuzzy string matching with configurable threshold

        Args:
            text1: First text to compare
            text2: Second text to compare
            threshold: Match threshold (default: FUZZY_MATCH_THRESHOLD)

        Returns:
            Tuple of (is_match, score) where score is 0-100
        """
        if threshold is None:
            threshold = PDFReader.FUZZY_MATCH_THRESHOLD * 100

        score = fuzz.token_set_ratio(text1.lower(), text2.lower())
        is_match = score >= threshold

        return is_match, score / 100.0

    @staticmethod
    def detect_template_type(texto: str) -> Tuple[Optional[str], float]:
        """
        Detect holerite template type using fuzzy matching

        Supports: DDPE, SPPREV_APOSENTADO, SPPREV_PENSIONISTA

        Args:
            texto: Extracted text from page

        Returns:
            Tuple of (template_type, confidence) or (None, 0.0) if no match
        """
        if not texto or len(texto.strip()) < 20:
            return None, 0.0

        texto_lower = texto.lower()

        # Template-specific keywords with priority/weight
        # Format: template_type -> (primary_keywords, secondary_keywords)
        template_patterns = {
            "DDPE": (
                ["departamento de despesa", "ddpe"],  # Primary
                ["secretaria de estado", "folha de pagamento"],  # Secondary
            ),
            "SPPREV_PENSIONISTA": (
                ["spprev", "pensionista"],  # Primary
                ["pensao", "beneficiario"],  # Secondary
            ),
            "SPPREV_APOSENTADO": (
                ["spprev", "aposentado"],  # Primary
                ["aposentadoria", "inativo"],  # Secondary
            ),
        }

        # Calculate match scores for each template
        best_template = None
        best_score = 0.0

        for template_type, (primary_kw, secondary_kw) in template_patterns.items():
            primary_matches = 0
            secondary_matches = 0

            # Check primary keywords (exact or fuzzy match)
            for keyword in primary_kw:
                # Try exact match first
                if keyword in texto_lower:
                    primary_matches += 1
                else:
                    # Try fuzzy match (lowered to 60% for OCR tolerance)
                    is_match, score = PDFReader.fuzzy_match(keyword, texto_lower, threshold=60.0)
                    if is_match:
                        primary_matches += 1

            # Check secondary keywords (exact or fuzzy match)
            for keyword in secondary_kw:
                # Try exact match first
                if keyword in texto_lower:
                    secondary_matches += 1
                else:
                    # Try fuzzy match (lowered to 60% for OCR tolerance)
                    is_match, score = PDFReader.fuzzy_match(keyword, texto_lower, threshold=60.0)
                    if is_match:
                        secondary_matches += 1

            # Calculate weighted score
            # Primary matches have higher weight
            total_matches = primary_matches * 2 + secondary_matches
            max_possible = len(primary_kw) * 2 + len(secondary_kw)

            if max_possible > 0:
                template_score = total_matches / max_possible
            else:
                template_score = 0.0

            if template_score > best_score and template_score >= PDFReader.FUZZY_MATCH_THRESHOLD:
                best_score = template_score
                best_template = template_type

        return best_template, best_score

    @staticmethod
    def find_best_template_match(
        texto: str, candidates: Optional[List[str]] = None
    ) -> Tuple[Optional[str], float]:
        """
        Find best matching template from candidates using fuzzy matching

        Args:
            texto: Extracted text from page
            candidates: List of candidate template identifiers (default: all supported)

        Returns:
            Tuple of (best_match, confidence) or (None, 0.0) if no match above threshold
        """
        if not texto or len(texto.strip()) < 20:
            return None, 0.0

        if candidates is None:
            candidates = ["DDPE", "SPPREV_APOSENTADO", "SPPREV_PENSIONISTA"]

        # If only one candidate, use detect_template_type and filter by candidate
        if len(candidates) == 1:
            detected_type, score = PDFReader.detect_template_type(texto)
            if detected_type == candidates[0]:
                return detected_type, score
            return None, 0.0

        # For multiple candidates, use detect_template_type and check if result is in candidates
        detected_type, score = PDFReader.detect_template_type(texto)

        if detected_type in candidates:
            return detected_type, score

        # If no match in detect_template_type, try fuzzy matching on keywords
        scores = {}
        texto_lower = texto.lower()

        template_keywords = {
            "DDPE": ["departamento", "ddpe"],
            "SPPREV_APOSENTADO": ["spprev", "aposentado"],
            "SPPREV_PENSIONISTA": ["spprev", "pensionista"],
        }

        for candidate in candidates:
            if candidate in template_keywords:
                keyword_matches = sum(
                    1 for kw in template_keywords[candidate] if kw in texto_lower
                )
                candidate_score = keyword_matches / len(template_keywords[candidate])
                scores[candidate] = candidate_score

        if not scores:
            return None, 0.0

        best_candidate = max(scores, key=scores.get)
        best_score = scores[best_candidate]

        # Return only if above threshold
        if best_score >= PDFReader.FUZZY_MATCH_THRESHOLD:
            return best_candidate, best_score

        return None, 0.0
