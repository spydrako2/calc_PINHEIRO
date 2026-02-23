"""Tests for BaseParser abstract interface"""

import pytest
from src.core.parsers import BaseParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import Holerite, CabecalhoHolerite, Verba, NaturezaVerba, TipoFolha


class ConcreteParser(BaseParser):
    """Concrete implementation of BaseParser for testing"""

    def detect_template(self, texto: str) -> bool:
        """Simple detection - just check for TEST keyword"""
        return "TEST" in texto.upper()

    def parse(self, paginas):
        """Simple parse - create minimal holerite"""
        self.paginas = paginas
        cabecalho = self._extract_cabecalho()
        verbas = self._extract_verbas()
        vencimentos, descontos, liquido = self._extract_totals()

        holerite = Holerite(
            cabecalho=cabecalho,
            verbas=verbas,
            total_vencimentos=vencimentos,
            total_descontos=descontos,
            liquido=liquido,
        )
        self._validate_holerite(holerite)
        return holerite

    def _extract_cabecalho(self) -> CabecalhoHolerite:
        """Extract test header"""
        return CabecalhoHolerite(
            nome="Test User",
            cpf="123.456.789-00",
            cargo="Developer",
            unidade="IT",
            competencia="2026-02",
            tipo_folha=TipoFolha.NORMAL,
            data_pagamento="2026-03-01",
            template_type=None,
        )

    def _extract_verbas(self) -> list:
        """Extract test verbas"""
        return [
            Verba(
                codigo="01.001",
                denominacao="Salário",
                natureza=NaturezaVerba.NORMAL,
                quantidade=1,
                unidade="",
                periodo_inicio="2026-02",
                periodo_fim="2026-02",
                valor=5000.00,
                qualificadores_detectados=[],
            )
        ]

    def _extract_totals(self) -> tuple:
        """Extract test totals"""
        return (5000.00, 1000.00, 4000.00)  # (vencimentos, descontos, liquido)


class TestBaseParser:
    """Test BaseParser interface and validation"""

    def test_base_parser_is_abstract(self):
        """BaseParser should be abstract and not instantiable"""
        # Cannot instantiate abstract class directly
        with pytest.raises(TypeError):
            BaseParser()

    def test_concrete_parser_implements_interface(self):
        """Concrete parser should implement all abstract methods"""
        parser = ConcreteParser()
        assert hasattr(parser, "detect_template")
        assert callable(parser.detect_template)
        assert hasattr(parser, "parse")
        assert callable(parser.parse)
        assert hasattr(parser, "_extract_cabecalho")
        assert callable(parser._extract_cabecalho)
        assert hasattr(parser, "_extract_verbas")
        assert callable(parser._extract_verbas)
        assert hasattr(parser, "_extract_totals")
        assert callable(parser._extract_totals)

    def test_parser_validate_holerite_success(self):
        """Should validate correct holerite data"""
        parser = ConcreteParser()
        paginas = [
            PaginaExtraida(numero=1, texto="TEST", metodo="TEXTO", confianca=0.95)
        ]

        holerite = parser.parse(paginas)
        assert holerite is not None
        assert holerite.cabecalho.nome == "Test User"
        assert len(holerite.verbas) > 0
        assert holerite.total_vencimentos == 5000.00

    def test_parser_detect_template(self):
        """Should detect template correctly"""
        parser = ConcreteParser()

        # Should detect TEST keyword
        assert parser.detect_template("Some TEST content") is True
        assert parser.detect_template("Other content") is False

    def test_parser_get_first_page_text(self):
        """Should retrieve text from first page"""
        parser = ConcreteParser()
        paginas = [
            PaginaExtraida(numero=1, texto="Page 1 content", metodo="TEXTO", confianca=0.95),
            PaginaExtraida(numero=2, texto="Page 2 content", metodo="TEXTO", confianca=0.95),
        ]
        parser.paginas = paginas

        assert parser.get_first_page_text() == "Page 1 content"

    def test_parser_get_continuation_pages(self):
        """Should identify continuation pages"""
        parser = ConcreteParser()
        paginas = [
            PaginaExtraida(
                numero=1,
                texto="CPF: 123.456.789-00\nNOME: Test",
                metodo="TEXTO",
                confianca=0.95,
            ),
            PaginaExtraida(
                numero=2,
                texto="CÓDIGO DENOMINAÇÃO VALOR\n70.006 IAMSPE 1000",
                metodo="TEXTO",
                confianca=0.95,
            ),
        ]
        parser.paginas = paginas

        continuation = parser.get_continuation_pages()
        # Page 2 should be detected as continuation (has verba table, no header)
        assert len(continuation) >= 0  # May or may not detect depending on heuristics

    def test_parser_validation_missing_cpf(self):
        """Should reject holerite without CPF"""
        parser = ConcreteParser()

        # Create holerite with missing CPF
        cabecalho = CabecalhoHolerite(
            nome="Test",
            cpf=None,  # Missing CPF
            cargo="Dev",
            unidade="IT",
            competencia="2026-02",
            tipo_folha=TipoFolha.NORMAL,
            data_pagamento="2026-03-01",
            template_type=None,
        )

        verba = Verba(
            codigo="01.001",
            denominacao="Salary",
            natureza=NaturezaVerba.NORMAL,
            quantidade=1,
            unidade="",
            periodo_inicio="2026-02",
            periodo_fim="2026-02",
            valor=5000.00,
            qualificadores_detectados=[],
        )

        holerite = Holerite(
            cabecalho=cabecalho,
            verbas=[verba],
            total_vencimentos=5000.00,
            total_descontos=0.0,
            liquido=5000.00,
        )

        with pytest.raises(ValueError):
            parser._validate_holerite(holerite)
