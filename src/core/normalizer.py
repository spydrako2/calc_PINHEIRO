"""
Normalization utilities for holerite data
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple


class CodigoVerbaNotmalizer:
    """Normalize verba codes between formats (XX.XXX <-> XXXXXX)"""

    # Equivalence table for verba codes (across template versions)
    EQUIVALENCIAS = {
        "70.056": ["70.113"],  # Contribuição previdenciária changed in 2020
        "70.006": ["070006"],  # IAMSPE DDPE -> SPPREV
        "70.007": ["070007"],
        "01.001": ["010001"],  # Salário base
        "09.001": ["090001"],  # Quinquênio
        "10.001": ["100001"],  # Sexta-parte
    }

    @staticmethod
    def normalize(codigo: str) -> str:
        """
        Convert código to standard format (XXXXXX - 6 digits)

        Args:
            codigo: "70.006" or "070006" or "70006"

        Returns:
            Standard format: "070006"
        """
        # Remove dots and spaces
        clean = codigo.replace(".", "").replace(" ", "").strip()

        # Pad with zeros if needed
        if len(clean) < 6:
            clean = clean.zfill(6)

        return clean[:6]

    @staticmethod
    def to_display_format(codigo: str) -> str:
        """
        Convert to display format (XX.XXX)

        Args:
            codigo: "070006" or "70.006"

        Returns:
            Display format: "70.006"
        """
        normalized = CodigoVerbaNotmalizer.normalize(codigo)
        # Remove leading zero: 070006 -> 70006, then format as XX.XXX
        value = int(normalized)  # 070006 -> 70006
        return f"{value // 1000:02d}.{value % 1000:03d}"

    @staticmethod
    def find_equivalente(codigo: str) -> Optional[str]:
        """
        Find equivalent codigo in other template format

        Args:
            codigo: Verba code in any format

        Returns:
            Equivalent code or None if not found
        """
        normalized = CodigoVerbaNotmalizer.normalize(codigo)

        for key, values in CodigoVerbaNotmalizer.EQUIVALENCIAS.items():
            key_norm = CodigoVerbaNotmalizer.normalize(key)
            if key_norm == normalized:
                return CodigoVerbaNotmalizer.normalize(values[0])

            for val in values:
                if CodigoVerbaNotmalizer.normalize(val) == normalized:
                    return key_norm

        return None


class AlocacaoTemporal:
    """Handle temporal allocation of verba values (período + 1 mês)"""

    @staticmethod
    def parse_periodo(periodo_str: str) -> Tuple[int, int]:
        """
        Parse período string to (year, month)

        Args:
            periodo_str: "2021-03" or "03/2021" or "mar/2021"

        Returns:
            (year, month) tuple

        Raises:
            ValueError: If period format invalid
        """
        # Try AAAA-MM format
        if "-" in periodo_str:
            parts = periodo_str.split("-")
            if len(parts) == 2:
                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    if 1 <= month <= 12:
                        return (year, month)
                except ValueError:
                    pass

        # Try MM/AAAA format
        if "/" in periodo_str:
            parts = periodo_str.split("/")
            if len(parts) == 2:
                try:
                    month = int(parts[0])
                    year = int(parts[1])
                    if 1 <= month <= 12 and year > 1900:
                        return (year, month)
                except ValueError:
                    pass

        raise ValueError(f"Invalid period format: {periodo_str}")

    @staticmethod
    def formato_standard(periodo: str) -> str:
        """
        Convert any period format to standard AAAA-MM

        Args:
            periodo: Any format

        Returns:
            Standard format: "2021-03"
        """
        year, month = AlocacaoTemporal.parse_periodo(periodo)
        return f"{year:04d}-{month:02d}"

    @staticmethod
    def get_mes_alocacao(periodo_referencia: str, natureza: str = "N") -> str:
        """
        Get allocation month for a verba

        Rule: Period + 1 month (unless natureza=N, then same month)

        Args:
            periodo_referencia: Reference period (e.g., "2021-03")
            natureza: Verba type ("N"=Normal, "A"=Atrasado, etc.)

        Returns:
            Allocation month in format "2021-04"
        """
        year, month = AlocacaoTemporal.parse_periodo(periodo_referencia)

        # Normal verbas stay in same month
        if natureza == "N":
            return f"{year:04d}-{month:02d}"

        # All others allocated to next month
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1

        return f"{next_year:04d}-{next_month:02d}"

    @staticmethod
    def get_periodo_padrao(anos_retroativos: int = 5) -> Tuple[str, str]:
        """
        Get default period (N years back from today)

        Args:
            anos_retroativos: Number of years back (default 5)

        Returns:
            (data_inicio, data_fim) in format "2021-03"
        """
        hoje = datetime.now()

        # End: today (this month)
        data_fim = f"{hoje.year:04d}-{hoje.month:02d}"

        # Start: N years ago
        data_inicio_obj = hoje - timedelta(days=365 * anos_retroativos)
        data_inicio = f"{data_inicio_obj.year:04d}-{data_inicio_obj.month:02d}"

        return (data_inicio, data_fim)
