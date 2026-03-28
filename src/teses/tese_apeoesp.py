"""
Tese: Quinquênio e Sexta Parte sobre Gratificações APEOESP
(Gratificação Geral, GTE, GAM)

Lógica:
    TOTAL_VANTAGENS = GratifGeral + GTE + GAM
    DIFERENÇA_QUINQ = TOTAL_VANTAGENS × (quinquênios × 5%)
    DIFERENÇA_6P    = DIFERENÇA_QUINQ / 6  (se servidor tem Sexta Parte)
    TOTAL_DEVIDO    = DIFERENÇA_QUINQ + DIFERENÇA_6P

Ao final de cada ano:
    13° SALÁRIO  = SUM(TOTAL_DEVIDO do ano) / 12
    1/3 FÉRIAS   = 13° / 3
"""

import re
from collections import defaultdict, OrderedDict
from typing import Optional

from src.core.pdf_reader import PDFReader
from src.core.parsers.ddpe_parser import DDPEParser
from src.teses.base_tese import BaseTese


# Verbas que compõem cada coluna
VERBAS_GRATIF_GERAL = {"004118", "004119"}
VERBAS_GTE          = {"004107", "004109"}
VERBAS_GAM          = {"004130", "004131"}
VERBAS_SEXTA_PARTE  = {"010001", "010002", "010003", "010010", "010021"}


class TeseApeoesp(BaseTese):
    nome = "Quinquênio e Sexta Parte — Gratificações APEOESP"
    descricao = (
        "Reflexo dos adicionais temporais (quinquênios) e da sexta parte sobre as "
        "gratificações integrais APEOESP: Gratificação Geral (LC 901/2001), "
        "GTE (Trabalho Educacional) e GAM (Atividade de Magistério)."
    )
    tese_tipo = "apeoesp"
    # Não usa verba_codigo nem quinquenio_codigo do BaseTese (lógica própria)
    verba_codigo = ""
    verba_nome = ""

    def processar(self, pdf_path: str) -> dict:
        pages = PDFReader.read_pdf(pdf_path)
        parser = DDPEParser()

        nome_cliente = "UNKNOWN"

        # {payment_key: {campo: valor}}
        # gratif/gte/gam track normal + atrasados separately for formula generation
        raw: dict = defaultdict(lambda: {
            'gratif_geral': {'normal': 0.0, 'atrasados': []},
            'gte':          {'normal': 0.0, 'atrasados': []},
            'gam':          {'normal': 0.0, 'atrasados': []},
            'quinquenios': 0,
            'tem_sexta_parte': False,
        })

        quinq_by_comp: dict = {}

        for p in pages:
            if not parser.detect_template(p.texto):
                continue

            comp = self._extract_competencia(p.texto)
            if not comp:
                continue

            if nome_cliente == "UNKNOWN":
                nome_cliente = self._extract_nome(p.texto)

            pi = DDPEParser()
            pi.paginas = [p]
            verbas = pi._extract_verbas()

            for v in verbas:
                # Quinquênios and sexta_parte don't need period expansion
                if BaseTese._is_quinquenio_verba(v):
                    q = self._extract_quinquenios(v)
                    if q > 0:
                        quinq_by_comp[comp] = q
                    continue

                if v.codigo in VERBAS_SEXTA_PARTE:
                    pay_key = self.mes_pagamento(v.periodo_fim or comp)
                    raw[pay_key]['tem_sexta_parte'] = True
                    continue

                # Determine which gratif field
                if v.codigo in VERBAS_GRATIF_GERAL:
                    field = 'gratif_geral'
                elif v.codigo in VERBAS_GTE:
                    field = 'gte'
                elif v.codigo in VERBAS_GAM:
                    field = 'gam'
                else:
                    continue

                # Expand period range across months; row = payment month
                periodo_fim = v.periodo_fim or comp
                periodo_inicio = v.periodo_inicio or periodo_fim
                months = self._months_in_range(periodo_inicio, periodo_fim)
                valores = BaseTese._distribute_valor(v.valor, len(months))
                is_atrasado = v.natureza.value in ('A', 'R')

                for m, val in zip(months, valores):
                    pay_key = self.mes_pagamento(m)
                    if is_atrasado:
                        raw[pay_key][field]['atrasados'].append((comp, val))
                    else:
                        raw[pay_key][field]['normal'] += val

        # Propagar quinquênios — períodos agora são payment months (comp+1)
        all_comp_keys = sorted(quinq_by_comp.keys())
        for pay_key in sorted(raw.keys()):
            best_q = 0
            for c in all_comp_keys:
                if self.mes_pagamento(c) <= pay_key:
                    best_q = quinq_by_comp[c]
                else:
                    break
            if best_q == 0 and all_comp_keys:
                best_q = quinq_by_comp[all_comp_keys[0]]
            raw[pay_key]['quinquenios'] = best_q

        # Propagar sexta_parte (direito permanente após a primeira ocorrência)
        has_sexta = any(raw[p]['tem_sexta_parte'] for p in raw)
        if has_sexta:
            primeiro_sexta = min(
                (p for p in raw if raw[p]['tem_sexta_parte']),
                default=None
            )
            if primeiro_sexta:
                for per in raw:
                    if per >= primeiro_sexta:
                        raw[per]['tem_sexta_parte'] = True

        # Calcular diferenças
        sorted_periods = sorted(raw.keys())
        periodos_out = OrderedDict()
        total_geral = 0.0

        for per in sorted_periods:
            d = raw[per]
            gratif = d['gratif_geral']['normal'] + sum(v for _, v in d['gratif_geral']['atrasados'])
            gte   = d['gte']['normal']          + sum(v for _, v in d['gte']['atrasados'])
            gam   = d['gam']['normal']          + sum(v for _, v in d['gam']['atrasados'])
            total_vantagens = gratif + gte + gam
            quinq = d['quinquenios']
            pct = quinq * 5 / 100
            diferenca_quinq = total_vantagens * pct
            diferenca_6p = diferenca_quinq / 6 if d['tem_sexta_parte'] else 0.0
            total_devido = diferenca_quinq + diferenca_6p
            total_geral += total_devido

            periodos_out[per] = {
                # Breakdown for writer formula generation
                'gratif_geral_normal':    d['gratif_geral']['normal'],
                'gratif_geral_atrasados': d['gratif_geral']['atrasados'],
                'gte_normal':             d['gte']['normal'],
                'gte_atrasados':          d['gte']['atrasados'],
                'gam_normal':             d['gam']['normal'],
                'gam_atrasados':          d['gam']['atrasados'],
                # Totals for downstream calculations
                'gratif_geral': gratif,
                'gte': gte,
                'gam': gam,
                'total_vantagens': total_vantagens,
                'quinquenios': quinq,
                'porcentagem': pct,
                'diferenca_quinq': diferenca_quinq,
                'tem_sexta_parte': d['tem_sexta_parte'],
                'diferenca_6p': diferenca_6p,
                'total_devido': total_devido,
            }

        return {
            'nome_cliente': nome_cliente,
            'tese_nome': self.nome,
            'tese_descricao': self.descricao,
            'tese_tipo': self.tese_tipo,
            'periodos': periodos_out,
            'total_geral': total_geral,
        }
