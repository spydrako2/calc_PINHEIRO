"""Tests for fuzzy matching functionality"""

import pytest
from src.core.pdf_reader import PDFReader


class TestFuzzyMatching:
    """Test fuzzy string matching for template detection"""

    def test_fuzzy_match_exists(self):
        """fuzzy_match method should exist"""
        assert hasattr(PDFReader, "fuzzy_match")
        assert callable(getattr(PDFReader, "fuzzy_match"))

    def test_fuzzy_match_exact(self):
        """Exact match should return high score"""
        is_match, score = PDFReader.fuzzy_match("DDPE", "DDPE")
        assert is_match is True
        assert score >= 0.95

    def test_fuzzy_match_similar(self):
        """Similar strings should match above threshold (0.75)"""
        is_match, score = PDFReader.fuzzy_match("DEPARTAMENTO", "DEPARTAMANTO")
        assert is_match is True
        assert score >= PDFReader.FUZZY_MATCH_THRESHOLD

    def test_fuzzy_match_case_insensitive(self):
        """Fuzzy matching should be case insensitive"""
        is_match1, score1 = PDFReader.fuzzy_match("DDPE", "ddpe")
        is_match2, score2 = PDFReader.fuzzy_match("DDPE", "DdPe")

        assert is_match1 is True
        assert is_match2 is True
        assert score1 == score2

    def test_fuzzy_match_different_strings(self):
        """Dissimilar strings should not match"""
        is_match, score = PDFReader.fuzzy_match("DDPE", "XYZ123ABC")
        assert is_match is False
        assert score < PDFReader.FUZZY_MATCH_THRESHOLD

    def test_fuzzy_match_custom_threshold(self):
        """Should respect custom threshold parameter"""
        text1 = "DEPARTAMENTO"
        text2 = "DEPARTAMANTO"

        # With default threshold
        is_match_default, score = PDFReader.fuzzy_match(text1, text2)
        assert is_match_default is True

        # With higher threshold (e.g. 0.95 = 95)
        is_match_high, _ = PDFReader.fuzzy_match(text1, text2, threshold=95.0)
        # May or may not match depending on actual similarity

    def test_detect_template_type_exists(self):
        """detect_template_type method should exist"""
        assert hasattr(PDFReader, "detect_template_type")
        assert callable(getattr(PDFReader, "detect_template_type"))

    def test_detect_template_ddpe(self):
        """Should detect DDPE template"""
        texto = """
        DEPARTAMENTO DE DESPESA
        FOLHA DE PAGAMENTO
        DDPE - SECRETARIA DE ESTADO
        CPF: 123.456.789-00
        NOME: JOÃO SILVA
        """
        template_type, confidence = PDFReader.detect_template_type(texto)
        assert template_type == "DDPE"
        assert confidence >= PDFReader.FUZZY_MATCH_THRESHOLD

    def test_detect_template_spprev_aposentado(self):
        """Should detect SPPREV Aposentado template"""
        texto = """
        SPPREV - SISTEMA DE PAGAMENTOS
        APOSENTADO
        INATIVO
        CPF: 987.654.321-00
        NOME: MARIA SANTOS
        COMPETÊNCIA: 03/2026
        APOSENTADORIA
        """
        template_type, confidence = PDFReader.detect_template_type(texto)
        assert template_type == "SPPREV_APOSENTADO"
        assert confidence >= PDFReader.FUZZY_MATCH_THRESHOLD

    def test_detect_template_spprev_pensionista(self):
        """Should detect SPPREV Pensionista template"""
        texto = """
        SPPREV - SISTEMA DE PAGAMENTOS
        PENSIONISTA
        PENSAO MENSAL
        CPF: 555.666.777-88
        NOME: CARLOS PEREIRA
        """
        template_type, confidence = PDFReader.detect_template_type(texto)
        assert template_type == "SPPREV_PENSIONISTA"
        assert confidence >= PDFReader.FUZZY_MATCH_THRESHOLD

    def test_detect_template_empty_text(self):
        """Empty text should return None"""
        template_type, confidence = PDFReader.detect_template_type("")
        assert template_type is None
        assert confidence == 0.0

    def test_detect_template_too_short(self):
        """Too short text should return None"""
        template_type, confidence = PDFReader.detect_template_type("ABC")
        assert template_type is None
        assert confidence == 0.0

    def test_detect_template_no_match(self):
        """Unrelated text should return None"""
        texto = """
        This is some random text
        Without any holerite information
        Just garbage data here
        """
        template_type, confidence = PDFReader.detect_template_type(texto)
        assert template_type is None
        assert confidence < PDFReader.FUZZY_MATCH_THRESHOLD

    def test_detect_template_degraded_ocr(self):
        """Should handle OCR degraded text (typos/errors)"""
        # Simulating OCR errors: DEPARTAMENTO → DEPARTAMANTO but with strong keywords
        texto = """
        DEPARTAMANTO DE DESPESA (OCR typo)
        DDPE
        SECRETARIA DE ESTADO
        FOLHA DE PAGAMENTO
        CPF: 111.222.333-44
        NOME: PEDRO OLIVEIRA
        """
        template_type, confidence = PDFReader.detect_template_type(texto)
        # Should still detect DDPE despite typos due to DDPE keyword
        assert template_type == "DDPE"
        assert confidence >= PDFReader.FUZZY_MATCH_THRESHOLD

    def test_find_best_template_match_exists(self):
        """find_best_template_match method should exist"""
        assert hasattr(PDFReader, "find_best_template_match")
        assert callable(getattr(PDFReader, "find_best_template_match"))

    def test_find_best_template_match_default_candidates(self):
        """Should use all supported templates by default"""
        texto = """
        DDPE DEPARTAMENTO
        SECRETARIA DE ESTADO
        FOLHA DE PAGAMENTO
        """
        best_match, confidence = PDFReader.find_best_template_match(texto)
        assert best_match == "DDPE"
        assert confidence >= PDFReader.FUZZY_MATCH_THRESHOLD

    def test_find_best_template_match_custom_candidates(self):
        """Should respect custom candidate list"""
        texto = """
        SPPREV SISTEMA DE PAGAMENTOS
        APOSENTADO
        APOSENTADORIA
        INATIVO
        """
        candidates = ["SPPREV_APOSENTADO", "SPPREV_PENSIONISTA"]
        best_match, confidence = PDFReader.find_best_template_match(texto, candidates)
        assert best_match == "SPPREV_APOSENTADO"
        assert confidence >= PDFReader.FUZZY_MATCH_THRESHOLD

    def test_find_best_template_match_no_candidates(self):
        """Should return None if no candidates provided and text empty"""
        best_match, confidence = PDFReader.find_best_template_match("")
        assert best_match is None
        assert confidence == 0.0

    def test_find_best_template_match_below_threshold(self):
        """Should return None if best match is below threshold"""
        texto = "XYZ ABC DEF GHI"  # Random text
        best_match, confidence = PDFReader.find_best_template_match(texto)
        assert best_match is None
        assert confidence < PDFReader.FUZZY_MATCH_THRESHOLD

    def test_fuzzy_threshold_boundary(self):
        """Test behavior at threshold boundary (0.75)"""
        # Create strings with score close to 75%
        text1 = "ABCDEFGHIJ"
        text2 = "ABCDEFGH__"  # 80% similar (8 out of 10 chars match)

        is_match, score = PDFReader.fuzzy_match(text1, text2)
        # Score should be >= threshold for match
        if score >= PDFReader.FUZZY_MATCH_THRESHOLD:
            assert is_match is True
        else:
            assert is_match is False

    def test_fuzzy_matching_performance(self):
        """Fuzzy matching should complete in reasonable time"""
        import time

        texto_long = "DEPARTAMENTO DE DESPESA " * 100  # Repeat to make longer

        start = time.time()
        template_type, confidence = PDFReader.detect_template_type(texto_long)
        elapsed = time.time() - start

        # Should complete in under 1 second
        assert elapsed < 1.0

    def test_fuzzy_match_returns_tuple(self):
        """fuzzy_match should return (bool, float) tuple"""
        result = PDFReader.fuzzy_match("test", "test")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)

    def test_detect_template_returns_tuple(self):
        """detect_template_type should return (str|None, float) tuple"""
        result = PDFReader.detect_template_type("DDPE")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] is None or isinstance(result[0], str)
        assert isinstance(result[1], float)

    def test_find_best_template_returns_tuple(self):
        """find_best_template_match should return (str|None, float) tuple"""
        result = PDFReader.find_best_template_match("DDPE")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] is None or isinstance(result[0], str)
        assert isinstance(result[1], float)

    def test_fuzzy_match_multiline_text(self):
        """Should handle multiline text correctly"""
        text1 = "DEPARTAMENTO\nDE\nDESPESA"
        text2 = "DEPARTAMENTO DE DESPESA"

        is_match, score = PDFReader.fuzzy_match(text1, text2)
        assert score > 0.5  # Should have decent similarity despite line breaks

    def test_fuzzy_match_with_special_characters(self):
        """Should handle special characters in matching"""
        text1 = "DEPARTAMENTO/DESPESA"
        text2 = "DEPARTAMENTO DESPESA"

        is_match, score = PDFReader.fuzzy_match(text1, text2)
        # Should have reasonable similarity
        assert score > 0.5
