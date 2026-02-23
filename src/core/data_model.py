"""
Data model for HoleritePRO - Core entities for holerite processing
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class NaturezaVerba(Enum):
    """Natura of a verba (earnings line item)"""
    NORMAL = "N"
    ATRASADO = "A"
    REPOSICAO = "R"
    DEVOLUCAO = "D"
    ESTORNO = "E"


class TipoFolha(Enum):
    """Type of payroll"""
    NORMAL = "NORMAL"
    SUPLEMENTAR = "SUPLEMENTAR"
    DECIMO_TERCEIRO = "13O"


class TemplateType(Enum):
    """PDF holerite template type"""
    DDPE = "DDPE"
    SPPREV_APOSENTADO = "SPPREV_APOSENTADO"
    SPPREV_PENSIONISTA = "SPPREV_PENSIONISTA"


@dataclass
class Verba:
    """A single earnings/deduction line item from a holerite"""
    codigo: str  # e.g., "70.006" or "070006"
    denominacao: str
    natureza: NaturezaVerba
    quantidade: Optional[float] = None
    unidade: Optional[str] = None
    periodo_inicio: Optional[str] = None  # AAAA-MM
    periodo_fim: Optional[str] = None  # AAAA-MM
    valor: float = 0.0
    qualificadores_detectados: List[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.natureza, str):
            self.natureza = NaturezaVerba(self.natureza)


@dataclass
class CabecalhoHolerite:
    """Header information from a holerite"""
    nome: str
    cpf: str
    cargo: Optional[str] = None
    unidade: Optional[str] = None
    competencia: str = ""  # AAAA-MM
    tipo_folha: TipoFolha = TipoFolha.NORMAL
    data_pagamento: Optional[str] = None
    template_type: TemplateType = TemplateType.DDPE

    def __post_init__(self):
        if isinstance(self.tipo_folha, str):
            self.tipo_folha = TipoFolha(self.tipo_folha)
        if isinstance(self.template_type, str):
            self.template_type = TemplateType(self.template_type)


@dataclass
class Holerite:
    """Complete holerite with header and earnings lines"""
    cabecalho: CabecalhoHolerite
    verbas: List[Verba] = field(default_factory=list)
    total_vencimentos: float = 0.0
    total_descontos: float = 0.0
    liquido: float = 0.0
    pagina_numero: int = 0
    metodo_extracao: str = "TEXTO"  # "TEXTO" or "OCR"
    confianca: float = 1.0  # 0.0-1.0

    def add_verba(self, verba: Verba):
        """Add a verba to this holerite"""
        self.verbas.append(verba)

    def calcula_totais(self):
        """Recalculate totals from verbas"""
        self.total_vencimentos = sum(v.valor for v in self.verbas if v.valor > 0)
        self.total_descontos = abs(sum(v.valor for v in self.verbas if v.valor < 0))
        self.liquido = self.total_vencimentos - self.total_descontos


@dataclass
class ExtractionContext:
    """Shared state for multi-page holerite extraction"""
    cabecalho_extraido: Optional[CabecalhoHolerite] = None
    competencia: Optional[str] = None
    cpf: Optional[str] = None
    pagina_numero: int = 0
    metodo_extracao: str = "TEXTO"
    confianca: float = 1.0
    verbas_pendentes: List[Verba] = field(default_factory=list)
