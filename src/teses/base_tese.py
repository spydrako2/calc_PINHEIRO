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
from src.core.parsers.spprev_aposentado_parser import SpprevAposentadoParser


class BaseTese(ABC):
    """Abstract base for a legal thesis calculation."""

    nome: str = ""
    descricao: str = ""
    verba_codigo: str = ""          # Target verba code (e.g. "003007")
    verba_nome: str = ""            # Display name
    quinquenio_codigo: str = "009001"

    # Codes that indicate the server has Sexta Parte (permanent right once seen)
    VERBAS_SEXTA_PARTE = {"010001", "010002", "010003", "010010", "010021"}

    def processar(self, pdf_path: str) -> dict:
        """
        Full pipeline: read PDF → extract → calculate.

        Rows are keyed by PAYMENT month (competência + 1 month).
        Period ranges are split across months (valor / n_meses per month).
        Atrasado formula: atrasados stored separately so writer can emit =normal+atraso1+...

        Returns:
            {
                'nome_cliente': str,
                'periodos': OrderedDict[str, {
                    'normal': float,
                    'atrasados': [(holerite_comp, valor), ...],
                    'quinquenios': int,
                    'total': float,
                    'reflexo': float,
                }],
                'total_verba': float,
                'total_reflexo': float,
            }
        """
        pages = PDFReader.read_pdf(pdf_path)
        _ddpe = DDPEParser()
        _spprev = SpprevAposentadoParser()

        nome_cliente = "UNKNOWN"
        periods = defaultdict(lambda: {
            'normal': 0.0,
            'atrasados': [],
            'quinquenios': 0,
            'tem_sexta_parte': False,
        })
        quinq_by_comp = {}
        sexta_parte_comp = None  # first comp where sexta parte was detected

        for p in pages:
            if _ddpe.detect_template(p.texto):
                ParserClass = DDPEParser
            elif _spprev.detect_template(p.texto):
                ParserClass = SpprevAposentadoParser
            else:
                continue

            comp = self._extract_competencia(p.texto)
            if not comp:
                continue

            # Extract client name from first detected page
            if nome_cliente == "UNKNOWN":
                nome_cliente = self._extract_nome(p.texto)

            pi = ParserClass()
            pi.paginas = [p]
            verbas = pi._extract_verbas()

            for v in verbas:
                if v.codigo == self.verba_codigo:
                    periodo_fim = v.periodo_fim or comp
                    periodo_inicio = v.periodo_inicio or periodo_fim
                    months = self._months_in_range(periodo_inicio, periodo_fim)
                    valores = self._distribute_valor(v.valor, len(months))

                    for m, val in zip(months, valores):
                        pay_key = self.mes_pagamento(m)
                        if v.natureza.value == 'N':
                            periods[pay_key]['normal'] += val
                        elif v.natureza.value in ('A', 'R'):
                            # comp = holerite where this atrasado was found (for comment)
                            periods[pay_key]['atrasados'].append((comp, val))

                elif self._is_quinquenio_verba(v):
                    q = self._extract_quinquenios(v)
                    if q > 0:
                        quinq_by_comp[comp] = q

                elif v.codigo in self.VERBAS_SEXTA_PARTE:
                    if sexta_parte_comp is None or comp < sexta_parte_comp:
                        sexta_parte_comp = comp

        # Fill quinquenios — periods are now keyed by payment month (comp+1)
        # Compare mes_pagamento(c) against pay_key to stay aligned
        all_comp_keys = sorted(quinq_by_comp.keys())
        for pay_key in sorted(periods.keys()):
            best_q = 0
            for c in all_comp_keys:
                if self.mes_pagamento(c) <= pay_key:
                    best_q = quinq_by_comp[c]
                else:
                    break
            if best_q == 0 and all_comp_keys:
                best_q = quinq_by_comp[all_comp_keys[0]]
            periods[pay_key]['quinquenios'] = best_q

        # Propagate sexta parte — permanent right from first occurrence onwards
        if sexta_parte_comp is not None:
            primeiro_pay = self.mes_pagamento(sexta_parte_comp)
            for pay_key in periods:
                if pay_key >= primeiro_pay:
                    periods[pay_key]['tem_sexta_parte'] = True

        # Calculate totals and reflexo (including 6ª parte when applicable)
        total_verba = 0.0
        total_reflexo = 0.0
        for per in periods:
            d = periods[per]
            d['total'] = d['normal'] + sum(v for _, v in d['atrasados'])
            pct = d['quinquenios'] * 5 / 100
            d['reflexo'] = d['total'] * pct
            d['reflexo_6p'] = d['reflexo'] / 6 if d['tem_sexta_parte'] else 0.0
            d['total_devido'] = d['reflexo'] + d['reflexo_6p']
            total_verba += d['total']
            total_reflexo += d['total_devido']

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
        # DDPE: "FOLHA NORMAL - 11/2025" or similar
        m = re.search(r'FOLHA\s+\w+\s*-?\s*(\d{2}/\d{4})', texto, re.IGNORECASE)
        if m:
            mm, yyyy = m.group(1).split('/')
            return f"{yyyy}-{mm}"
        # SPPREV: label "COMPETÊNCIA" on one line, value "05/2020" on the next
        m = re.search(r'COMPET[A-Z]*.*?(\d{1,2}/\d{4})', texto, re.IGNORECASE | re.DOTALL)
        if m:
            mm, yyyy = m.group(1).split('/')
            return f"{yyyy}-{int(mm):02d}"
        return None

    @staticmethod
    def _extract_nome(texto: str) -> str:
        lines = texto.split('\n')
        for i, line in enumerate(lines):
            lu = line.upper()
            if 'NOME' in lu and ('C.P.F' in lu or 'CPF' in lu):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    m = re.match(r'^([A-ZÁÉÍÓÚÂÃÕÊÔÇÜ\s]+)', next_line)
                    if m:
                        nome = m.group(1).strip()
                        if len(nome) > 3:
                            return nome
        return "UNKNOWN"

    @staticmethod
    def _distribute_valor(valor: float, n: int) -> list:
        """
        Distribui valor em n partes iguais com residuo no último mês (evita drift de centavos).

        Exemplo: 100.00 / 3 → [33.33, 33.33, 33.34]
        Garante que sum(resultado) == valor (sem erro de arredondamento).
        """
        if n <= 1:
            return [round(valor, 2)]
        base = round(valor / n, 2)
        ultimo = round(valor - base * (n - 1), 2)
        return [base] * (n - 1) + [ultimo]

    @staticmethod
    def _months_in_range(periodo_inicio: str, periodo_fim: str) -> list:
        """
        Returns list of 'YYYY-MM' months in [inicio, fim] inclusive.
        Used to split period-range verbas across multiple months.
        """
        y1, m1 = int(periodo_inicio[:4]), int(periodo_inicio[5:7])
        y2, m2 = int(periodo_fim[:4]), int(periodo_fim[5:7])
        months = []
        y, m = y1, m1
        while (y, m) <= (y2, m2):
            months.append(f"{y:04d}-{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1
        if not months:
            import warnings
            warnings.warn(f"periodo_inicio {periodo_inicio} > periodo_fim {periodo_fim}, usando periodo_fim como fallback")
            return [periodo_fim]
        return months

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
    def _is_quinquenio_verba(v) -> bool:
        """Detecta verba de quinquênio: família 009xxx OU 'QUINQ' na denominação."""
        return v.codigo.startswith("009") or "QUINQ" in v.denominacao.upper()

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
