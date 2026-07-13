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


CHS_PRINCIPAIS = {"002044", "002045", "002046", "002051", "002004"}
CHS_OUTRAS = {"002062"}
CHS_TODOS = CHS_PRINCIPAIS | CHS_OUTRAS

CODIGO_INATIVO = "002004"

# 02.046 = CHS de Coord./Vice Diretor. É carga REAL própria (não é resumo dos
# demais): o servidor pode acumular 5-8 série (044), ensino médio (045) e a
# carga de vice/coord (046) no mesmo mês. Validação: a soma das horas de todas
# as CHS fecha com a "qtde" do piso do magistério (jornada). Ex.: EDER faz
# 50h(044)+50h(045)+100h(046)=200h = jornada; JAQUELINE só tem 046.
CODIGO_VICE_DIRETOR = "002046"

CODIGO_PISO = "001035"
CODIGOS_SALARIO_BASE = {"001001", "001002"}
CODIGO_QUINQ_CHS = "009003"
CODIGO_SEXTA_CHS = "010003"

CHS_LABELS = {
    "002044": "CHS Fundamental\n(cód. 02.044)",
    "002045": "CHS Ensino Médio\n(cód. 02.045)",
    "002046": "CHS Coord./Vice Diretor\n(cód. 02.046)",
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

        # Cada verba de valor guarda normal e atrasados SEPARADOS, para que o
        # writer emita fórmula auditável (=normal+atraso1+...). Atrasados são
        # realocados ao mês de competência a que se referem (mesma lógica da
        # ação de quinquênio em BaseTese), não ao mês em que foram pagos.
        raw: dict = defaultdict(lambda: {
            'salario_base': {'normal': 0.0, 'atrasados': []},
            'piso': {'normal': 0.0, 'atrasados': [], 'qtd_normal': None, 'qtd_atraso': None},
            'chs': {},   # codigo -> {'normal': 0.0, 'atrasados': [], 'qtd': None}
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
                nat = v.natureza.value
                # Só Normal, Atrasado e Reposição entram no cálculo
                # (Devolução/Estorno ficam de fora, como antes).
                if nat not in ('N', 'A', 'R'):
                    continue

                if v.codigo in CODIGOS_SALARIO_BASE:
                    for pk, val in self._distribuir_por_pagamento(v, comp):
                        self._add(raw[pk]['salario_base'], nat, comp, val)
                elif v.codigo == CODIGO_PISO:
                    for pk, val in self._distribuir_por_pagamento(v, comp):
                        self._add(raw[pk]['piso'], nat, comp, val)
                        if v.quantidade:
                            key = 'qtd_normal' if nat == 'N' else 'qtd_atraso'
                            raw[pk]['piso'][key] = v.quantidade
                elif v.codigo in CHS_TODOS:
                    for pk, val in self._distribuir_por_pagamento(v, comp):
                        bucket = raw[pk]['chs'].setdefault(
                            v.codigo, {'normal': 0.0, 'atrasados': [], 'qtd': None}
                        )
                        self._add(bucket, nat, comp, val)
                        if nat == 'N' and v.quantidade:
                            bucket['qtd'] = v.quantidade
                elif self._is_quinquenio_verba(v) or v.codigo == CODIGO_QUINQ_CHS:
                    if nat == 'N':
                        q = self._extract_quinquenios(v)
                        if q > 0 and q > raw[pay_key]['quinquenios']:
                            raw[pay_key]['quinquenios'] = q
                elif v.codigo == CODIGO_SEXTA_CHS or v.codigo in self.VERBAS_SEXTA_PARTE:
                    if nat == 'N':
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
                    for c in raw[pk]['chs']:
                        if c != CODIGO_INATIVO:
                            freq[c] = freq.get(c, 0) + 1
            if freq:
                # Escolhe o código ativo mais frequente como destino do remap
                codigo_destino = max(freq.items(), key=lambda kv: (kv[1], kv[0]))[0]
                for pk in sorted_keys:
                    chs = raw[pk]['chs']
                    if CODIGO_INATIVO in chs:
                        src = chs.pop(CODIGO_INATIVO)
                        dst = chs.setdefault(
                            codigo_destino, {'normal': 0.0, 'atrasados': [], 'qtd': None}
                        )
                        dst['normal'] += src['normal']
                        dst['atrasados'].extend(src['atrasados'])
                        if dst['qtd'] is None:
                            dst['qtd'] = src['qtd']

        # Descobre todos os códigos CHS que apareceram (para colunas F-J)
        codigos_chs_vistos = set()
        for pk in sorted_keys:
            codigos_chs_vistos.update(raw[pk]['chs'].keys())

        codigos_ordenados = self._ordenar_codigos_chs(codigos_chs_vistos)

        periodos_out = OrderedDict()
        for pk in sorted_keys:
            d = raw[pk]
            piso = d['piso']
            salbase = d['salario_base']
            chs = d['chs']

            # Soma das CHS principais (normal + atrasados) — base do salário lei500
            chs_principais_soma = sum(
                b['normal'] + sum(v for _, v in b['atrasados'])
                for c, b in chs.items() if c in CHS_PRINCIPAIS
            )

            # Coluna B — Salário Base
            if vinculo == 'lei500':
                # Base = soma das CHS principais (que já têm colunas F-J auditáveis)
                salario_base_normal = chs_principais_soma
                salario_base_atrasados = []
            elif salbase['normal'] > 0 or salbase['atrasados']:
                salario_base_normal = salbase['normal']
                salario_base_atrasados = list(salbase['atrasados'])
            else:
                # Aposentado sem 001001 (ex: era Lei 500 e aposentou) — usa CHS
                salario_base_normal = chs_principais_soma
                salario_base_atrasados = []

            # Jornada (col D): qtd do piso normal; se o mês só teve piso atrasado
            # (piso 100% retroativo), usa a qtd de referência do atrasado.
            jornada_horas = piso['qtd_normal'] if piso['qtd_normal'] is not None else piso['qtd_atraso']
            # Horas suplementares (col E): soma das qtd das CHS normais do mês
            horas_suplementares = sum(b['qtd'] for b in chs.values() if b['qtd']) or None

            # Lei 500: horas suplementares = jornada total (o servidor SÓ faz CHS)
            if vinculo == 'lei500' and jornada_horas is not None:
                horas_suplementares = jornada_horas

            periodos_out[pk] = {
                'salario_base_normal': salario_base_normal,
                'salario_base_atrasados': salario_base_atrasados,
                'piso_normal': piso['normal'],
                'piso_atrasados': list(piso['atrasados']),
                'jornada_horas': jornada_horas,
                'horas_suplementares': horas_suplementares,
                'chs_por_codigo': {
                    c: {'normal': b['normal'], 'atrasados': list(b['atrasados'])}
                    for c, b in chs.items()
                },
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
    def _add(bucket: dict, nat: str, comp: str, val: float) -> None:
        """Acumula valor no bucket: normal soma; atrasado (A/R) guarda (comp, val)."""
        if nat == 'N':
            bucket['normal'] += val
        else:
            bucket['atrasados'].append((comp, val))

    @classmethod
    def _distribuir_por_pagamento(cls, v, comp: str) -> list:
        """
        Retorna [(pay_key, valor), ...].

        Normal: uma parcela no mês de pagamento da competência corrente.
        Atrasado (A/R): distribui o valor pelos meses do período de referência
        (periodo_inicio..periodo_fim) e realoca cada parcela ao mês de pagamento
        do mês a que se refere — mesma lógica de atrasados de BaseTese.
        """
        if v.natureza.value == 'N':
            return [(cls.mes_pagamento(comp), v.valor)]
        fim = v.periodo_fim or comp
        inicio = v.periodo_inicio or fim
        months = cls._months_in_range(inicio, fim)
        valores = cls._distribute_valor(v.valor, len(months))
        return [(cls.mes_pagamento(m), val) for m, val in zip(months, valores)]

    @staticmethod
    def _ordenar_codigos_chs(codigos: set) -> list:
        """Ordena códigos CHS: principais primeiro, depois outras. Máx 5 colunas F-J."""
        principais = sorted(c for c in codigos if c in CHS_PRINCIPAIS)
        outras = sorted(c for c in codigos if c in CHS_OUTRAS)
        return (principais + outras)[:5]
