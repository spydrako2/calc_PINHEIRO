"""
HoleritePRO Pipeline — End-to-end PDF processing.

Reads PDFs, detects templates, parses holerites, applies temporal allocation.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.core.data_model import Holerite, Verba, TemplateType, NaturezaVerba
from src.core.pdf_reader import PaginaExtraida, PDFReader
from src.core.template_detector import TemplateDetector
from src.core.normalizer import AlocacaoTemporal


@dataclass
class ProcessedVerba:
    """A verba with its temporal allocation info."""
    verba: Verba
    mes_alocacao: str           # YYYY-MM (month for spreadsheet column)
    competencia_holerite: str   # YYYY-MM (original competencia)


@dataclass
class ProcessedHolerite:
    """A holerite with its processed verbas."""
    holerite: Holerite
    verbas_processadas: List[ProcessedVerba] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result of pipeline processing."""
    holerites: List[ProcessedHolerite] = field(default_factory=list)
    relatorio: Dict[str, Any] = field(default_factory=dict)
    erros: List[str] = field(default_factory=list)


class Pipeline:
    """
    End-to-end pipeline for processing holerite PDFs.

    Steps:
    1. Read PDFs → pages (PDFReader)
    2. Detect template per page (TemplateDetector)
    3. Group pages into logical holerites (header = new, continuation = append)
    4. Parse each group (appropriate parser)
    5. Apply temporal allocation (AlocacaoTemporal)
    6. Group by CPF, sort by competencia
    """

    def __init__(self):
        self.detector = TemplateDetector()

    def process_pdfs(self, pdf_paths: List[str]) -> PipelineResult:
        """
        Process multiple PDFs through the full pipeline.

        Args:
            pdf_paths: List of paths to PDF files

        Returns:
            PipelineResult with processed holerites, stats, and non-fatal errors
        """
        result = PipelineResult()
        all_holerites: List[ProcessedHolerite] = []

        for pdf_path in pdf_paths:
            try:
                holerites = self._process_single_pdf(pdf_path, result.erros)
                all_holerites.extend(holerites)
            except Exception as e:
                result.erros.append(f"Error processing {pdf_path}: {str(e)}")

        # Group by CPF, sort by competencia
        cpf_groups: Dict[str, List[ProcessedHolerite]] = {}
        for ph in all_holerites:
            cpf = ph.holerite.cabecalho.cpf
            if cpf not in cpf_groups:
                cpf_groups[cpf] = []
            cpf_groups[cpf].append(ph)

        # Sort each group by competencia
        for cpf in cpf_groups:
            cpf_groups[cpf].sort(
                key=lambda ph: ph.holerite.cabecalho.competencia
            )

        # Flatten sorted groups
        result.holerites = []
        for cpf in sorted(cpf_groups.keys()):
            result.holerites.extend(cpf_groups[cpf])

        # Build report
        result.relatorio = {
            "total_pdfs": len(pdf_paths),
            "total_holerites": len(all_holerites),
            "total_verbas": sum(
                len(ph.verbas_processadas) for ph in all_holerites
            ),
            "cpfs_unicos": len(cpf_groups),
            "templates": {},
            "erros_count": len(result.erros),
        }

        for ph in all_holerites:
            t = ph.holerite.cabecalho.template_type.value
            result.relatorio["templates"][t] = (
                result.relatorio["templates"].get(t, 0) + 1
            )

        return result

    def _process_single_pdf(
        self, pdf_path: str, erros: List[str]
    ) -> List[ProcessedHolerite]:
        """Process a single PDF file."""
        paginas = PDFReader.read_pdf(pdf_path)

        if not paginas:
            erros.append(f"No pages extracted from {pdf_path}")
            return []

        # Group pages into logical holerites
        groups = self._group_pages(paginas, erros)

        processed = []
        for template_type, pages in groups:
            try:
                parser = self.detector.get_parser(template_type)
                holerite = parser.parse(pages)

                # Apply temporal allocation
                verbas_processadas = self._apply_alocacao(holerite)

                ph = ProcessedHolerite(
                    holerite=holerite,
                    verbas_processadas=verbas_processadas,
                )
                processed.append(ph)

            except Exception as e:
                page_nums = [p.numero for p in pages]
                erros.append(
                    f"Error parsing pages {page_nums} of {pdf_path}: {str(e)}"
                )

        return processed

    def _group_pages(
        self, paginas: List[PaginaExtraida], erros: List[str]
    ) -> List[tuple]:
        """
        Group pages into logical holerites.

        A new header page starts a new group. Continuation pages append to
        the current group.

        Returns:
            List of (TemplateType, List[PaginaExtraida]) tuples
        """
        groups = []
        current_pages = []
        current_template = None

        for pagina in paginas:
            template = self.detector.detect(pagina.texto)

            if template is not None:
                # New holerite detected
                if current_pages and current_template:
                    groups.append((current_template, current_pages))

                current_pages = [pagina]
                current_template = template
            elif current_pages:
                # Continuation page
                current_pages.append(pagina)
            else:
                # Orphan page (no header detected yet)
                erros.append(
                    f"Page {pagina.numero}: no template detected, skipping"
                )

        # Don't forget the last group
        if current_pages and current_template:
            groups.append((current_template, current_pages))

        return groups

    def _apply_alocacao(self, holerite: Holerite) -> List[ProcessedVerba]:
        """
        Apply temporal allocation to all verbas in a holerite.

        Rules:
        - Normal (N): mes_alocacao = verba.periodo_fim (or competencia)
        - Atrasado/Reposicao/etc: mes_alocacao = periodo_fim + 1 month
        - Multiple verbas with same (codigo, mes_alocacao) are preserved separately
        """
        competencia = holerite.cabecalho.competencia
        result = []

        for verba in holerite.verbas:
            try:
                mes_alocacao = AlocacaoTemporal.get_mes_alocacao_from_range(
                    periodo_inicio=verba.periodo_inicio,
                    periodo_fim=verba.periodo_fim,
                    natureza=verba.natureza.value,
                    competencia_fallback=competencia,
                )
            except (ValueError, AttributeError):
                # Fallback to competencia
                mes_alocacao = competencia or "0000-00"

            pv = ProcessedVerba(
                verba=verba,
                mes_alocacao=mes_alocacao,
                competencia_holerite=competencia,
            )
            result.append(pv)

        return result


def pipeline_to_json(result: PipelineResult) -> str:
    """Serialize PipelineResult to JSON string."""
    data = {
        "relatorio": result.relatorio,
        "erros": result.erros,
        "holerites": [],
    }

    for ph in result.holerites:
        h = ph.holerite
        holerite_data = {
            "cabecalho": {
                "nome": h.cabecalho.nome,
                "cpf": h.cabecalho.cpf,
                "cargo": h.cabecalho.cargo,
                "competencia": h.cabecalho.competencia,
                "template_type": h.cabecalho.template_type.value,
                "entidade": h.cabecalho.entidade,
                "numero_beneficio": h.cabecalho.numero_beneficio,
                "banco": h.cabecalho.banco,
                "agencia": h.cabecalho.agencia,
                "conta": h.cabecalho.conta,
            },
            "totais": {
                "vencimentos": h.total_vencimentos,
                "descontos": h.total_descontos,
                "liquido": h.liquido,
                "base_ir": h.base_ir,
                "base_redutor": h.base_redutor,
                "base_contrib_prev": h.base_contrib_prev,
            },
            "verbas": [],
        }

        for pv in ph.verbas_processadas:
            v = pv.verba
            holerite_data["verbas"].append({
                "codigo": v.codigo,
                "denominacao": v.denominacao,
                "natureza": v.natureza.value,
                "quantidade": v.quantidade,
                "unidade": v.unidade,
                "periodo_inicio": v.periodo_inicio,
                "periodo_fim": v.periodo_fim,
                "valor": v.valor,
                "mes_alocacao": pv.mes_alocacao,
                "competencia_holerite": pv.competencia_holerite,
            })

        data["holerites"].append(holerite_data)

    return json.dumps(data, indent=2, ensure_ascii=False)
