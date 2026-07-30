"""
PDF Reader with hybrid text/OCR extraction
Motor primário: PyMuPDF (fitz) — ~10-20x mais rápido que pdfplumber
Fallback OCR: pytesseract para páginas escaneadas
"""
import os
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

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

    # OCR é ~2s por página (o tesseract domina o custo; o render do fitz é ~0,2s).
    # Como o tesseract roda num subprocesso, o GIL é liberado e threads dão
    # speedup quase linear. O render fica FORA das threads: PyMuPDF não é
    # thread-safe e usar o mesmo documento em paralelo pode derrubar o processo.
    OCR_MAX_WORKERS = min(8, os.cpu_count() or 1)

    # Cache de leitura: o app lê o mesmo PDF duas vezes (diagnóstico no upload e
    # depois no cálculo da tese). Sem cache, todo PDF escaneado paga OCR em
    # dobro. As páginas guardam só texto, então o custo de memória é baixo.
    _CACHE_MAX = 4
    _cache: "OrderedDict[tuple, List[PaginaExtraida]]" = OrderedDict()

    @staticmethod
    def limpar_cache() -> None:
        """Descarta o cache de leitura (usar em testes ou ao trocar de cliente)."""
        PDFReader._cache.clear()

    @staticmethod
    def _chave_cache(pdf_path: Path):
        """Identidade do arquivo: caminho + mtime + tamanho (pega reescritas)."""
        try:
            st = pdf_path.stat()
            return (str(pdf_path.resolve()), st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    @staticmethod
    def read_pdf(pdf_path: str) -> List[PaginaExtraida]:
        """
        Read PDF page by page usando PyMuPDF (fitz) — motor rápido.
        Fallback para OCR via pytesseract em páginas sem texto suficiente.

        Páginas que precisam de OCR são processadas em paralelo (ver
        OCR_MAX_WORKERS) e o resultado do arquivo fica em cache, para o mesmo
        PDF não ser lido/OCRado duas vezes na mesma sessão.

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

        chave = PDFReader._chave_cache(pdf_path)
        if chave is not None and chave in PDFReader._cache:
            PDFReader._cache.move_to_end(chave)
            return PDFReader._cache[chave]

        try:
            doc = fitz.open(str(pdf_path))
            # Materializa as páginas: o documento é percorrido mais de uma vez
            # (texto primeiro, OCR depois) e um iterador seria consumido.
            pages = list(doc)

            textos = [PDFReader._extrair_texto_fitz(p) for p in pages]
            pendentes = [
                i for i, t in enumerate(textos)
                if len(t) < PDFReader.LIMIAR_MINIMO_CHARS
            ]
            textos_ocr = PDFReader._ocr_em_lote(pages, pendentes)

            paginas = []
            for i, texto in enumerate(textos):
                if i not in pendentes:
                    metodo, confianca = "TEXTO", PDFReader.CONFIANCA_TEXTO
                elif textos_ocr.get(i):
                    texto = textos_ocr[i]
                    metodo, confianca = "OCR", PDFReader.CONFIANCA_OCR
                else:
                    metodo, confianca = "TEXTO", 0.3

                paginas.append(PaginaExtraida(
                    numero=i + 1,
                    texto=texto,
                    metodo=metodo,
                    confianca=confianca,
                ))
            doc.close()

        except Exception as e:
            raise Exception(f"Error reading PDF {pdf_path}: {str(e)}")

        if chave is not None:
            PDFReader._cache[chave] = paginas
            PDFReader._cache.move_to_end(chave)
            while len(PDFReader._cache) > PDFReader._CACHE_MAX:
                PDFReader._cache.popitem(last=False)

        return paginas

    @staticmethod
    def _ocr_em_lote(pages: list, indices: List[int]) -> Dict[int, Optional[str]]:
        """
        Aplica OCR nas páginas indicadas, em paralelo quando vale a pena.

        O render (PyMuPDF) roda sequencialmente na thread principal; só o
        tesseract vai para as threads. Processa em lotes do tamanho do pool
        para não segurar todas as imagens em memória de uma vez.
        """
        if not indices:
            return {}

        # Página única: caminho direto (mais simples e sem overhead de pool).
        if len(indices) == 1:
            i = indices[0]
            return {i: PDFReader._apply_ocr_fitz(pages[i])}

        workers = max(1, PDFReader.OCR_MAX_WORKERS)
        resultado: Dict[int, Optional[str]] = {}

        for inicio in range(0, len(indices), workers):
            lote = indices[inicio:inicio + workers]
            imagens = [(i, PDFReader._render_para_ocr(pages[i])) for i in lote]

            prontas = [(i, img) for i, img in imagens if img is not None]
            for i, img in imagens:
                if img is None:
                    resultado[i] = None

            if not prontas:
                continue
            if len(prontas) == 1:
                i, img = prontas[0]
                resultado[i] = PDFReader._ocr_imagem(img)
                continue

            with ThreadPoolExecutor(max_workers=min(workers, len(prontas))) as pool:
                textos = pool.map(PDFReader._ocr_imagem, [img for _, img in prontas])
                for (i, _), texto in zip(prontas, textos):
                    resultado[i] = texto

        return resultado

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
    def _render_para_ocr(page):
        """Renderiza a página fitz na imagem que vai para o OCR.

        Usa 3x scale, escala de cinza e reforço de contraste. Corta barras de
        UI de capturas mobile (topo ~5%, rodapé ~8%).

        Fica FORA das threads de OCR: PyMuPDF não é thread-safe.
        """
        try:
            from PIL import Image, ImageEnhance

            # Renderizar em 3x para melhor qualidade OCR
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Cortar barras de UI mobile (status bar topo ~5%, navbar rodapé ~8%)
            w, h = img.size
            img = img.crop((0, int(h * 0.05), w, int(h * 0.92)))

            # Escala de cinza + contraste aumentado para melhor leitura
            img = img.convert("L")
            return ImageEnhance.Contrast(img).enhance(2.0)
        except Exception:
            return None

    # Confiança mínima do OSD para aceitar a rotação. Abaixo disso é chute e
    # girar uma página que já estava certa seria pior do que não fazer nada.
    OSD_CONFIANCA_MINIMA = 1.0
    # None = ainda não testado; False = osd.traineddata indisponível no ambiente
    _osd_disponivel: Optional[bool] = None

    @staticmethod
    def _corrigir_orientacao(img):
        """Endireita página digitalizada de lado (foto/print girado).

        Uma página a 90/180/270° é perda TOTAL hoje: o OCR devolve texto
        ilegível, o template não é reconhecido e o holerite some do cálculo
        sem nenhum aviso. O OSD do tesseract detecta e corrige.

        Depende de `osd.traineddata`. Se não existir no ambiente, desativa-se
        sozinho na primeira tentativa e o fluxo segue como antes.
        """
        if img is None or PDFReader._osd_disponivel is False:
            return img
        try:
            import pytesseract

            osd = pytesseract.image_to_osd(img)
            PDFReader._osd_disponivel = True

            graus = confianca = 0.0
            for linha in osd.split("\n"):
                if linha.startswith("Rotate:"):
                    graus = int(linha.split(":")[1])
                elif linha.startswith("Orientation confidence:"):
                    confianca = float(linha.split(":")[1])

            if graus and confianca >= PDFReader.OSD_CONFIANCA_MINIMA:
                return img.rotate(-graus, expand=True, fillcolor=255)
        except Exception:
            # osd.traineddata ausente (ex.: Streamlit Cloud) ou página sem texto
            # suficiente para o OSD decidir — segue sem girar.
            PDFReader._osd_disponivel = False
        return img

    @staticmethod
    def _ocr_imagem(img) -> Optional[str]:
        """Roda o tesseract sobre a imagem já renderizada.

        Seguro para chamar de várias threads: o pytesseract executa o binário
        do tesseract num subprocesso, liberando o GIL enquanto espera.
        """
        if img is None:
            return None
        try:
            import pytesseract

            # Configurar caminho do Tesseract no Windows se não estiver no PATH
            import shutil
            if not shutil.which("tesseract"):
                pytesseract.pytesseract.tesseract_cmd = (
                    os.environ.get("TESSERACT_CMD")
                    or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                )

            # Configurar tessdata local (~\tessdata) via variável de ambiente
            tessdata_local = os.path.join(os.path.expanduser("~"), "tessdata")
            lang = "por"
            if os.path.isdir(tessdata_local) and os.path.isfile(
                os.path.join(tessdata_local, "por.traineddata")
            ):
                os.environ.setdefault("TESSDATA_PREFIX", tessdata_local)
            else:
                lang = "eng"

            def _ler(imagem):
                bruto = pytesseract.image_to_string(
                    imagem, lang=lang, config="--oem 3 --psm 6")
                if not bruto or not bruto.strip():
                    return None
                linhas = [l.strip() for l in bruto.split("\n")]
                return "\n".join(l for l in linhas if l) or None

            texto = _ler(img)

            # Só paga o custo do OSD (uma chamada extra ao tesseract, ~1s) quando
            # a leitura não rendeu um holerite reconhecível. Em PDF normal isso
            # nunca dispara; em página girada, é a diferença entre o holerite
            # entrar no cálculo ou sumir sem aviso.
            if not PDFReader._parece_holerite(texto):
                girada = PDFReader._corrigir_orientacao(img)
                if girada is not img:
                    texto_girado = _ler(girada)
                    if PDFReader._parece_holerite(texto_girado):
                        return texto_girado

            return texto
        except Exception:
            return None

    @staticmethod
    def _parece_holerite(texto: Optional[str]) -> bool:
        """A leitura resultou num holerite que algum parser reconhece?"""
        if not texto:
            return False
        # Import adiado: os parsers importam PaginaExtraida deste módulo.
        from src.core.parsers.ddpe_parser import DDPEParser
        from src.core.parsers.spprev_aposentado_parser import SpprevAposentadoParser

        return (DDPEParser().detect_template(texto)
                or SpprevAposentadoParser().detect_template(texto))

    @staticmethod
    def _apply_ocr_fitz(page) -> Optional[str]:
        """OCR de uma página: render + tesseract."""
        return PDFReader._ocr_imagem(PDFReader._render_para_ocr(page))

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
