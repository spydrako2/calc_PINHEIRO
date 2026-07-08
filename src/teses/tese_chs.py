"""
Tese: Reflexo do Piso Salarial Docente sobre a base de cálculo da CHS
(Carga Horária Suplementar).

Objetivo: recalcular a CHS incluindo o piso na base de cálculo por hora,
e apurar a diferença mensal, com reflexo de quinquênios e sexta parte.

Fórmula por mês (mesma da planilha modelo):
    CHS_recebida = (SalárioBase / Jornada) × HorasSuplementares
    CHS_devida   = (SalárioBase + Piso) / Jornada × HorasSuplementares
    Diferença    = CHS_devida − CHS_recebida
    Reflexo Quinq = Diferença × (quinq × 5%)
    Reflexo 6ª    = (Diferença + Reflexo Quinq) / 6   (se tem 6ª parte)
    Total Devido  = Diferença + Reflexo Quinq + Reflexo 6ª

Vínculo detectado no cabeçalho do holerite (para decidir "Salário Base"):
    - "TITULAR DE CARGO EFETIVO"       → efetivo (col B = 001001 SALARIO BASE)
    - "ADM.LEI 500/74"                 → lei500  (col B = soma das CHS principais)

Situação (para escolher a aba do XLSX):
    - Baseada no último holerite (por competência): DDPE → ATIVO; SPPREV → INATIVO
"""

import re
from collections import defaultdict, OrderedDict

from src.core.pdf_reader import PDFReader
from src.core.parsers.ddpe_parser import DDPEParser
from src.core.parsers.spprev_aposentado_parser import SpprevAposentadoParser
from src.teses.base_tese import BaseTese


CHS_PRINCIPAIS = {"002044", "002045", "002051", "002004"}
CHS_OUTRAS = {"002062"}
CHS_TODOS = CHS_PRINCIPAIS | CHS_OUTRAS

CODIGO_INATIVO = "002004"

CODIGO_PISO = "001035"
CODIGOS_SALARIO_BASE = {"001001", "001002"}
CODIGO_QUINQ_CHS = "009003"
CODIGO_SEXTA_CHS = "010003"

CHS_LABELS = {
    "002044": "CHS Fundamental\n(cód. 02.044)",
    "002045": "CHS Ensino Médio\n(cód. 02.045)",
    "002051": "CHS Genérica\n(cód. 02.051)",
    "002062": "Aulas Reposição\n(cód. 02.062)",
    "002004": "CHS Inativo\n(cód. 02.004)",
}


class TeseCHS(BaseTese):
    nome = "CHS sobre Piso Salarial Docente"
    descricao = (
        "Recalcula a Carga Horária Suplementar incluindo o Piso Salarial "
        "Docente (Decreto 62.500/2017 e Lei Federal 11.738/2008) na base de "
        "cálculo por hora, apurando a diferença mensal e seus reflexos."
    )
    tese_tipo = "chs"

    verba_codigo = ""
    verba_nome = ""

    def processar(self, pdf_path: str) -> dict:
        pages = PDFReader.read_pdf(pdf_path)
        _ddpe = DDPEParser()
        _spprev = SpprevAposentadoParser()

        nome_cliente = "UNKNOWN"
        vinculo = None

        raw: dict = defaultdict(lambda: {
            'salario_base_verba': 0.0,
            'piso_valor': 0.0,
            'piso_qtd': None,
            'chs_por_codigo': {},
            'chs_qtd_por_codigo': {},
            'quinquenios': 0,
            'tem_sexta_parte': False,
        })

        pay_to_fmt: dict = {}

        for p in pages:
            is_ddpe = _ddpe.detect_template(p.texto)
            is_spprev = _spprev.detect_template(p.texto)
            if not (is_ddpe or is_spprev):
                continue

            comp = self._extract_competencia(p.texto)
            if not comp:
                continue
            pay_key = self.mes_pagamento(comp)
            pay_to_fmt[pay_key] = 'ativo' if is_ddpe else 'inativo'

            if vinculo is None and is_ddpe:
                if re.search(r'ADM\.?\s*LEI\s*500', p.texto, re.IGNORECASE):
                    vinculo = 'lei500'
                elif re.search(r'TITULAR\s+DE\s+CARGO\s+EFETIVO', p.texto, re.IGNORECASE):
                    vinculo = 'efetivo'

            if nome_cliente == "UNKNOWN":
                nome_cliente = self._extract_nome(p.texto)

            ParserClass = DDPEParser if is_ddpe else SpprevAposentadoParser
            pi = ParserClass()
            pi.paginas = [p]
            verbas = pi._extract_verbas()

            for v in verbas:
                if v.natureza.value != 'N':
                    continue

                if v.codigo in CODIGOS_SALARIO_BASE:
                    raw[pay_key]['salario_base_verba'] += v.valor
                elif v.codigo == CODIGO_PISO:
                    raw[pay_key]['piso_valor'] += v.valor
                    if v.quantidade:
                        raw[pay_key]['piso_qtd'] = v.quantidade
                elif v.codigo in CHS_TODOS:
                    d = raw[pay_key]
                    d['chs_por_codigo'][v.codigo] = d['chs_por_codigo'].get(v.codigo, 0.0) + v.valor
                    if v.quantidade:
                        d['chs_qtd_por_codigo'][v.codigo] = v.quantidade
                elif self._is_quinquenio_verba(v) or v.codigo == CODIGO_QUINQ_CHS:
                    q = self._extract_quinquenios(v)
                    if q > 0 and q > raw[pay_key]['quinquenios']:
                        raw[pay_key]['quinquenios'] = q
                elif v.codigo == CODIGO_SEXTA_CHS or v.codigo in self.VERBAS_SEXTA_PARTE:
                    raw[pay_key]['tem_sexta_parte'] = True

        if vinculo is None:
            vinculo = 'efetivo'

        # Situação da aba = tipo do último holerite (por data)
        if pay_to_fmt:
            situacao = pay_to_fmt[max(pay_to_fmt.keys())]
        else:
            situacao = 'ativo'

        # Propaga 6ª parte a partir da primeira ocorrência
        sorted_keys = sorted(raw.keys())
        primeiro_sexta = next(
            (pk for pk in sorted_keys if raw[pk]['tem_sexta_parte']),
            None
        )
        if primeiro_sexta:
            for pk in sorted_keys:
                if pk >= primeiro_sexta:
                    raw[pk]['tem_sexta_parte'] = True

        # Propaga quinquênios (usa o maior visto até o momento)
        max_q = 0
        for pk in sorted_keys:
            if raw[pk]['quinquenios'] > max_q:
                max_q = raw[pk]['quinquenios']
            elif max_q > 0:
                raw[pk]['quinquenios'] = max_q

        # Se o cliente foi ATIVO em algum momento, remapeia CHS Inativo (002004)
        # para o código CHS ativo mais usado — mantém uma coluna contínua na planilha
        teve_periodo_ativo = any(fmt == 'ativo' for fmt in pay_to_fmt.values())
        if teve_periodo_ativo:
            # Conta frequência dos códigos CHS ativos (exceto 002004)
            freq: dict = {}
            for pk in sorted_keys:
                if pay_to_fmt.get(pk) == 'ativo':
                    for c in raw[pk]['chs_por_codigo']:
                        if c != CODIGO_INATIVO:
                            freq[c] = freq.get(c, 0) + 1
            if freq:
                # Escolhe o código ativo mais frequente como destino do remap
                codigo_destino = max(freq.items(), key=lambda kv: (kv[1], kv[0]))[0]
                for pk in sorted_keys:
                    d = raw[pk]
                    if CODIGO_INATIVO in d['chs_por_codigo']:
                        valor_inativo = d['chs_por_codigo'].pop(CODIGO_INATIVO)
                        d['chs_por_codigo'][codigo_destino] = (
                            d['chs_por_codigo'].get(codigo_destino, 0.0) + valor_inativo
                        )
                        if CODIGO_INATIVO in d['chs_qtd_por_codigo']:
                            qtd_inativo = d['chs_qtd_por_codigo'].pop(CODIGO_INATIVO)
                            d['chs_qtd_por_codigo'].setdefault(codigo_destino, qtd_inativo)

        # Descobre todos os códigos CHS que apareceram (para colunas F-J)
        codigos_chs_vistos = set()
        for pk in sorted_keys:
            codigos_chs_vistos.update(raw[pk]['chs_por_codigo'].keys())

        codigos_ordenados = self._ordenar_codigos_chs(codigos_chs_vistos)

        periodos_out = OrderedDict()
        for pk in sorted_keys:
            d = raw[pk]
            chs_principais_soma = sum(
                v for c, v in d['chs_por_codigo'].items() if c in CHS_PRINCIPAIS
            )

            # Coluna B — Salário Base
            if vinculo == 'lei500':
                salario_base = chs_principais_soma
            elif d['salario_base_verba'] > 0:
                salario_base = d['salario_base_verba']
            else:
                # Aposentado sem 001001 (ex: era Lei 500 e aposentou) — usa CHS
                salario_base = chs_principais_soma

            jornada_horas = d['piso_qtd']
            horas_suplementares = sum(d['chs_qtd_por_codigo'].values()) or None

            # Lei 500: horas suplementares = jornada total (o servidor SÓ faz CHS)
            if vinculo == 'lei500' and jornada_horas is not None:
                horas_suplementares = jornada_horas

            periodos_out[pk] = {
                'salario_base': salario_base,
                'piso': d['piso_valor'],
                'jornada_horas': jornada_horas,
                'horas_suplementares': horas_suplementares,
                'chs_por_codigo': dict(d['chs_por_codigo']),
                'quinquenios': d['quinquenios'],
                'tem_sexta_parte': d['tem_sexta_parte'],
            }

        return {
            'nome_cliente': nome_cliente,
            'tese_nome': self.nome,
            'tese_descricao': self.descricao,
            'tese_tipo': self.tese_tipo,
            'vinculo': vinculo,
            'situacao': situacao,
            'codigos_chs_colunas': codigos_ordenados,
            'periodos': periodos_out,
        }

    @staticmethod
    def _ordenar_codigos_chs(codigos: set) -> list:
        """Ordena códigos CHS: principais primeiro, depois outras. Máx 5 colunas F-J."""
        principais = sorted(c for c in codigos if c in CHS_PRINCIPAIS)
        outras = sorted(c for c in codigos if c in CHS_OUTRAS)
        return (principais + outras)[:5]
