"""
Base class for all legal theses (teses jurídicas).
Each tese extracts a target verba from DDPE payslips and calculates its reflexo.
"""

import re
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List, Dict, Optional

from src.core.pdf_reader import PDFReader
from src.core.parsers.ddpe_parser import DDPEParser


class BaseTese(ABC):
    """Abstract base for a legal thesis calculation."""

    nome: str = ""
    descricao: str = ""
    verba_codigo: str = ""          # Target verba code (e.g. "003007")
    verba_nome: str = ""            # Display name
    quinquenio_codigo: str = "009001"

    def processar(self, pdf_path: str) -> dict:
        """
        Full pipeline: read PDF → extract → calculate.

        Returns:
            {
                'nome_cliente': str,
                'periodos': OrderedDict[str, {
                    'normal': float,
                    'atrasados': [(comp_pgto, valor), ...],
                    'quinquenios': int,
                    'total': float,
                    'reflexo': float,
                }],
                'total_verba': float,
                'total_reflexo': float,
            }
        """
        pages = PDFReader.read_pdf(pdf_path)
        parser = DDPEParser()

        nome_cliente = "UNKNOWN"
        periods = defaultdict(lambda: {
            'normal': 0.0,
            'atrasados': [],
            'quinquenios': 0,
        })
        quinq_by_comp = {}

        for p in pages:
            if not parser.detect_template(p.texto):
                continue

            comp = self._extract_competencia(p.texto)
            if not comp:
                continue

            # Extract client name from first detected page
            if nome_cliente == "UNKNOWN":
                nome_cliente = self._extract_nome(p.texto)

            pi = DDPEParser()
            pi.paginas = [p]
            verbas = pi._extract_verbas()

            for v in verbas:
                if v.codigo == self.verba_codigo:
                    periodo = v.periodo_fim or comp
                    if v.natureza.value == 'N':
                        periods[periodo]['normal'] += v.valor
                    elif v.natureza.value in ('A', 'R'):
                        periods[periodo]['atrasados'].append((comp, v.valor))

                elif v.codigo == self.quinquenio_codigo:
                    q = self._extract_quinquenios(v)
                    if q > 0:
                        quinq_by_comp[comp] = q

        # Fill quinquenios
        all_comps = sorted(quinq_by_comp.keys())
        for per in sorted(periods.keys()):
            best_q = 0
            for c in all_comps:
                if c <= per:
                    best_q = quinq_by_comp[c]
                else:
                    break
            if best_q == 0 and all_comps:
                best_q = quinq_by_comp[all_comps[0]]
            periods[per]['quinquenios'] = best_q

        # Calculate totals and reflexo
        total_verba = 0.0
        total_reflexo = 0.0
        for per in periods:
            d = periods[per]
            d['total'] = d['normal'] + sum(v for _, v in d['atrasados'])
            pct = d['quinquenios'] * 5 / 100
            d['reflexo'] = d['total'] * pct
            total_verba += d['total']
            total_reflexo += d['reflexo']

        return {
            'nome_cliente': nome_cliente,
            'tese_nome': self.nome,
            'tese_descricao': self.descricao,
            'verba_nome': self.verba_nome,
            'periodos': dict(periods),
            'total_verba': total_verba,
            'total_reflexo': total_reflexo,
        }

    @staticmethod
    def _extract_competencia(texto: str) -> Optional[str]:
        m = re.search(r'FOLHA\s+\w+\s*-?\s*(\d{2}/\d{4})', texto, re.IGNORECASE)
        if m:
            mm, yyyy = m.group(1).split('/')
            return f"{yyyy}-{mm}"
        return None

    @staticmethod
    def _extract_nome(texto: str) -> str:
        lines = texto.split('\n')
        for i, line in enumerate(lines):
            if 'Nome' in line and ('C.P.F' in line or 'CPF' in line):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    m = re.match(r'^([A-ZÁÉÍÓÚÂÃÕÊÔÇÜ\s]+)', next_line)
                    if m:
                        nome = m.group(1).strip()
                        if len(nome) > 3:
                            return nome
        return "UNKNOWN"

    @staticmethod
    def _extract_quinquenios(verba) -> int:
        if verba.quantidade is not None:
            return int(verba.quantidade)
        m = re.search(r'(\d{1,3})\s*QUINQ', verba.denominacao, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.search(r'(\d+)[,.](\d+)\s*PERC', verba.denominacao, re.IGNORECASE)
        if m:
            perc = float(f"{m.group(1)}.{m.group(2)}")
            return int(perc / 5)
        return 0

    @staticmethod
    def mes_pagamento(competencia: str) -> str:
        """Mês de pagamento real = competência + 1 mês."""
        yyyy, mm = competencia.split('-')
        m = int(mm) + 1
        y = int(yyyy)
        if m > 12:
            m = 1
            y += 1
        return f"{y:04d}-{m:02d}"

    @staticmethod
    def format_comp_display(comp: str) -> str:
        """YYYY-MM → MM/YYYY"""
        yyyy, mm = comp.split('-')
        return f"{mm}/{yyyy}"
