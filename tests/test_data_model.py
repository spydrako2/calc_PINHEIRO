"""Tests for data_model.py"""

import pytest
from src.core.data_model import (
    Holerite,
    CabecalhoHolerite,
    Verba,
    NaturezaVerba,
    TipoFolha,
    TemplateType,
)


class TestVerba:
    """Test Verba dataclass"""

    def test_create_verba(self):
        v = Verba(
            codigo="70.006",
            denominacao="IAMSPE",
            natureza=NaturezaVerba.NORMAL,
            valor=1000.0,
        )
        assert v.codigo == "70.006"
        assert v.denominacao == "IAMSPE"
        assert v.valor == 1000.0

    def test_verba_with_string_natureza(self):
        """Should convert string natureza to enum"""
        v = Verba(
            codigo="70.006",
            denominacao="IAMSPE",
            natureza="N",  # String instead of enum
            valor=1000.0,
        )
        assert v.natureza == NaturezaVerba.NORMAL


class TestCabecalhoHolerite:
    """Test CabecalhoHolerite dataclass"""

    def test_create_cabecalho(self):
        cab = CabecalhoHolerite(
            nome="LUCIANO BASTOS",
            cpf="123.456.789-00",
            competencia="2021-03",
            template_type=TemplateType.DDPE,
        )
        assert cab.nome == "LUCIANO BASTOS"
        assert cab.cpf == "123.456.789-00"
        assert cab.competencia == "2021-03"

    def test_cabecalho_default_tipo_folha(self):
        """Should default to NORMAL"""
        cab = CabecalhoHolerite(
            nome="Test",
            cpf="000.000.000-00",
        )
        assert cab.tipo_folha == TipoFolha.NORMAL

    def test_cabecalho_with_string_tipo_folha(self):
        """Should convert string tipo_folha to enum"""
        cab = CabecalhoHolerite(
            nome="Test",
            cpf="000.000.000-00",
            tipo_folha="SUPLEMENTAR",
        )
        assert cab.tipo_folha == TipoFolha.SUPLEMENTAR


class TestHolerite:
    """Test Holerite dataclass"""

    def test_create_holerite(self):
        cab = CabecalhoHolerite(
            nome="LUCIANO",
            cpf="123.456.789-00",
            competencia="2021-03",
        )
        hol = Holerite(cabecalho=cab)
        assert hol.cabecalho.nome == "LUCIANO"
        assert len(hol.verbas) == 0

    def test_add_verba(self):
        cab = CabecalhoHolerite(
            nome="LUCIANO",
            cpf="123.456.789-00",
            competencia="2021-03",
        )
        hol = Holerite(cabecalho=cab)

        v = Verba(
            codigo="70.006",
            denominacao="IAMSPE",
            natureza=NaturezaVerba.NORMAL,
            valor=1000.0,
        )
        hol.add_verba(v)

        assert len(hol.verbas) == 1
        assert hol.verbas[0].valor == 1000.0

    def test_calcula_totais(self):
        cab = CabecalhoHolerite(
            nome="LUCIANO",
            cpf="123.456.789-00",
            competencia="2021-03",
        )
        hol = Holerite(cabecalho=cab)

        hol.add_verba(
            Verba(
                codigo="70.006",
                denominacao="IAMSPE",
                natureza=NaturezaVerba.NORMAL,
                valor=1000.0,
            )
        )
        hol.add_verba(
            Verba(
                codigo="01.001",
                denominacao="INSS",
                natureza=NaturezaVerba.NORMAL,
                valor=-200.0,
            )
        )

        hol.calcula_totais()

        assert hol.total_vencimentos == 1000.0
        assert hol.total_descontos == 200.0
        assert hol.liquido == 800.0
