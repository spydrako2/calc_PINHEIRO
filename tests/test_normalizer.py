"""Tests for normalizer.py"""

import pytest
from src.core.normalizer import CodigoVerbaNotmalizer, AlocacaoTemporal


class TestCodigoVerbaNormalizer:
    """Test verba code normalization"""

    def test_normalize_ddpe_format(self):
        """Convert XX.XXX to XXXXXX"""
        result = CodigoVerbaNotmalizer.normalize("70.006")
        assert result == "070006"

    def test_normalize_already_normalized(self):
        """Already in XXXXXX format"""
        result = CodigoVerbaNotmalizer.normalize("070006")
        assert result == "070006"

    def test_normalize_with_spaces(self):
        """Handle spaces"""
        result = CodigoVerbaNotmalizer.normalize("70 . 006")
        assert result == "070006"

    def test_normalize_padding(self):
        """Pad with zeros"""
        result = CodigoVerbaNotmalizer.normalize("1")
        assert result == "000001"

    def test_to_display_format(self):
        """Convert to XX.XXX display format"""
        result = CodigoVerbaNotmalizer.to_display_format("070006")
        assert result == "70.006"

    def test_to_display_format_from_display(self):
        """Already in display format"""
        result = CodigoVerbaNotmalizer.to_display_format("70.006")
        assert result == "70.006"

    def test_find_equivalente_ddpe_to_spprev(self):
        """Find SPPREV equivalent for DDPE code"""
        result = CodigoVerbaNotmalizer.find_equivalente("70.006")
        assert result == "070006"

    def test_find_equivalente_spprev_to_ddpe(self):
        """Find DDPE equivalent for SPPREV code"""
        result = CodigoVerbaNotmalizer.find_equivalente("070006")
        assert result == "070006"

    def test_find_equivalente_not_found(self):
        """Unknown code has no equivalent"""
        result = CodigoVerbaNotmalizer.find_equivalente("99.999")
        assert result is None


class TestAlocacaoTemporal:
    """Test temporal allocation"""

    def test_parse_periodo_aaaa_mm(self):
        """Parse AAAA-MM format"""
        result = AlocacaoTemporal.parse_periodo("2021-03")
        assert result == (2021, 3)

    def test_parse_periodo_mm_aaaa(self):
        """Parse MM/AAAA format"""
        result = AlocacaoTemporal.parse_periodo("03/2021")
        assert result == (2021, 3)

    def test_parse_periodo_invalid(self):
        """Invalid format raises error"""
        with pytest.raises(ValueError):
            AlocacaoTemporal.parse_periodo("mar-2021")

    def test_parse_periodo_invalid_month(self):
        """Invalid month raises error"""
        with pytest.raises(ValueError):
            AlocacaoTemporal.parse_periodo("2021-13")

    def test_formato_standard_from_aaaa_mm(self):
        """Convert to standard format"""
        result = AlocacaoTemporal.formato_standard("2021-03")
        assert result == "2021-03"

    def test_formato_standard_from_mm_aaaa(self):
        """Convert MM/AAAA to AAAA-MM"""
        result = AlocacaoTemporal.formato_standard("03/2021")
        assert result == "2021-03"

    def test_get_mes_alocacao_normal(self):
        """Normal verba (N) stays in same month"""
        result = AlocacaoTemporal.get_mes_alocacao("2021-03", "N")
        assert result == "2021-03"

    def test_get_mes_alocacao_atrasado(self):
        """Atrasado (A) allocated to next month"""
        result = AlocacaoTemporal.get_mes_alocacao("2021-03", "A")
        assert result == "2021-04"

    def test_get_mes_alocacao_year_wrap(self):
        """Allocation wraps year boundary"""
        result = AlocacaoTemporal.get_mes_alocacao("2021-12", "A")
        assert result == "2022-01"

    def test_get_mes_alocacao_reposicao(self):
        """Reposição (R) allocated to next month"""
        result = AlocacaoTemporal.get_mes_alocacao("2021-03", "R")
        assert result == "2021-04"

    def test_get_periodo_padrao(self):
        """Get default 5-year period"""
        inicio, fim = AlocacaoTemporal.get_periodo_padrao(5)

        # Verify format
        assert len(inicio) == 7  # AAAA-MM
        assert len(fim) == 7
        assert "-" in inicio
        assert "-" in fim

        # Verify fim is approximately today
        from datetime import datetime
        hoje = datetime.now()
        assert fim == f"{hoje.year:04d}-{hoje.month:02d}"
