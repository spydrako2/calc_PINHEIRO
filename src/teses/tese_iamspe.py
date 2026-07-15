"""Tese: Acúmulo IAMSPE — descontos indevidos no segundo cargo."""

from collections import defaultdict, OrderedDict

from src.core.pdf_reader import PDFReader
from src.core.parsers.ddpe_parser import DDPEParser
from src.teses.base_tese import BaseTese  # apenas para helpers estáticos


class TeseIAMSPE:
    """
    IAMSPE só pode ser descontado em um cargo.
    Esta tese extrai TODOS os descontos IAMSPE lançados no segundo cargo,
    gerando uma planilha pivot para cobrança de devolução.

    Estrutura da planilha:
        linhas   = meses (competência)
        colunas  = cada rubrica IAMSPE encontrada
        última   = VALOR DEVIDO (soma das rubricas)
    """

    nome = "Acúmulo IAMSPE"
    descricao = (
        "IAMSPE só pode ser descontado em um cargo. "
        "Extrai todos os descontos IAMSPE do segundo cargo para cobrança de devolução."
    )
    tese_tipo = "iamspe"

    # Códigos de IAMSPE sobre 13º salário. Aparecem duas vezes por ano:
    # na antecipação (folha normal, geralmente meio do ano) e na folha do
    # 13º (competência "13/AAAA"). Ambos são consolidados numa linha anual.
    CODES_13 = {"070122", "070123", "070124"}

    # Rubricas IAMSPE conhecidas (fallback para quando a denominação não vier no PDF)
    LABELS_CONHECIDOS = {
        "070006": "70.006: IAMSPE",
        "070007": "70.007: IAMSPE S/ 1/3 FÉRIAS",
        "070037": "70.037: IAMSPE-AGREGADOS-LEI 11.125/2002",
        "070119": "70.119: IAMSPE BENEFICIARIOS-LEI 17.293/20",
        "070120": "70.120: IAMSPE AGREGADOS S/ FÉRIAS",
        "070121": "70.121: IAMSPE BENEFICIARIOS S/ FÉRIAS",
        "070122": "70.122: IAMSPE - 13 SALÁRIO",
        "070123": "70.123: IAMSPE AGREGADOS - 13 SALÁRIO",
        "070124": "70.124: IAMSPE BENEFICIARIOS - 13 SALÁRIO",
        "070125": "70.125: IAMSPE - LEI 17.293/2020",
    }

    @staticmethod
    def _format_code(codigo: str) -> str:
        """'070006' → '70.006'"""
        try:
            n = int(codigo)
            s = str(n)
            if len(s) <= 3:
                return s
            return f"{s[:-3]}.{s[-3:]}"
        except ValueError:
            return codigo

    @staticmethod
    def _is_iamspe(codigo: str, denominacao: str) -> bool:
        # Filtra apenas por denominação — mais confiável que checar prefixo "070"
        # (outros descontos como IRRF e Previdência também começam com 070xxx)
        return "IAMSPE" in denominacao.upper()

    @classmethod
    def _is_iamspe_13(cls, codigo: str, denominacao: str) -> bool:
        """IAMSPE sobre 13º salário — código dedicado (070122/123/124) ou
        denominação mencionando '13' (SALÁRIO). Vai para a linha anual do 13º."""
        if codigo in cls.CODES_13:
            return True
        d = denominacao.upper()
        return "IAMSPE" in d and ("13" in d or "DÉCIMO" in d or "DECIMO" in d)

    @staticmethod
    def _competencia(texto: str, parser: DDPEParser) -> str:
        """Competência 'AAAA-MM'. Faz fallback para o layout DDPE ('Tipo da Folha'),
        que reconhece a folha do 13º como mês '13' — caso em que a regex genérica
        de BaseTese falha e a página seria descartada indevidamente."""
        comp = BaseTese._extract_competencia(texto)
        if comp:
            return comp
        comp_ddpe = parser._extract_competencia_ddpe(texto)  # 'MM/AAAA', ex.: '13/2025'
        if comp_ddpe:
            mm, yyyy = comp_ddpe.split('/')
            return f"{yyyy}-{int(mm):02d}"
        return ""

    def _make_label(self, codigo: str, denominacao: str) -> str:
        """Gera label no formato '70.006: IAMSPE' para uso como cabeçalho."""
        if codigo in self.LABELS_CONHECIDOS:
            return self.LABELS_CONHECIDOS[codigo]
        fmt = self._format_code(codigo)
        return f"{fmt}: {denominacao}" if denominacao else fmt

    def processar(self, pdf_path: str) -> dict:
        pages = PDFReader.read_pdf(pdf_path)
        parser = DDPEParser()

        nome_cliente = "UNKNOWN"
        # {payment_key: {codigo: {'normal': float, 'atrasados': [(comp, val)]}}}
        pivot: dict = defaultdict(lambda: defaultdict(lambda: {'normal': 0.0, 'atrasados': []}))
        # {ano: {codigo: {'normal': float, 'atrasados': [(comp, val)]}}} — IAMSPE do 13º
        decimo: dict = defaultdict(lambda: defaultdict(lambda: {'normal': 0.0, 'atrasados': []}))
        # {codigo: label} — ordem de aparição
        rubrica_labels: dict = {}

        for p in pages:
            if not parser.detect_template(p.texto):
                continue

            comp = self._competencia(p.texto, parser)
            if not comp:
                continue

            if nome_cliente == "UNKNOWN":
                nome_cliente = BaseTese._extract_nome(p.texto)

            pi = DDPEParser()
            pi.paginas = [p]
            verbas = pi._extract_verbas()

            for v in verbas:
                if not self._is_iamspe(v.codigo, v.denominacao):
                    continue

                if v.codigo not in rubrica_labels:
                    rubrica_labels[v.codigo] = self._make_label(v.codigo, v.denominacao)

                is_atrasado = v.natureza.value in ('A', 'R')

                # IAMSPE do 13º: consolida o valor cheio na linha anual (antecipação
                # + folha do 13º), sem ratear por período nem virar linha mensal.
                if self._is_iamspe_13(v.codigo, v.denominacao):
                    ano = comp[:4]
                    if is_atrasado:
                        decimo[ano][v.codigo]['atrasados'].append((comp, abs(v.valor)))
                    else:
                        decimo[ano][v.codigo]['normal'] += abs(v.valor)
                    continue

                # Expand period range; row = payment month (comp+1)
                periodo_fim = v.periodo_fim or comp
                periodo_inicio = v.periodo_inicio or periodo_fim
                months = BaseTese._months_in_range(periodo_inicio, periodo_fim)
                valores = BaseTese._distribute_valor(abs(v.valor), len(months))

                for m, val in zip(months, valores):
                    pay_key = BaseTese.mes_pagamento(m)
                    if is_atrasado:
                        pivot[pay_key][v.codigo]['atrasados'].append((comp, val))
                    else:
                        pivot[pay_key][v.codigo]['normal'] += val

        # Ordenar períodos cronologicamente e códigos numericamente
        sorted_periods = sorted(pivot.keys())
        sorted_codes = sorted(rubrica_labels.keys())
        sorted_years = sorted(decimo.keys())

        ZERO = {'normal': 0.0, 'atrasados': []}

        periodos_out = OrderedDict()
        for per in sorted_periods:
            periodos_out[per] = {
                code: dict(pivot[per].get(code, ZERO))
                for code in sorted_codes
            }

        # IAMSPE do 13º consolidado por ano: {ano: {code: {'normal', 'atrasados'}}}
        decimo_out = OrderedDict()
        for ano in sorted_years:
            decimo_out[ano] = {
                code: dict(decimo[ano].get(code, ZERO))
                for code in sorted_codes
            }

        def _total_cell(cell):
            return cell['normal'] + sum(v for _, v in cell['atrasados'])

        total_por_rubrica = {
            code: (
                sum(_total_cell(pivot[per].get(code, ZERO)) for per in sorted_periods)
                + sum(_total_cell(decimo[ano].get(code, ZERO)) for ano in sorted_years)
            )
            for code in sorted_codes
        }
        total_geral = sum(total_por_rubrica.values())

        rubricas = OrderedDict(
            (code, rubrica_labels[code]) for code in sorted_codes
        )

        return {
            'nome_cliente': nome_cliente,
            'tese_nome': self.nome,
            'tese_descricao': self.descricao,
            'tese_tipo': self.tese_tipo,
            'rubricas': rubricas,             # {code: label}
            'periodos': periodos_out,          # {payment_key: {code: {'normal', 'atrasados'}}}
            'decimo_terceiro': decimo_out,     # {ano: {code: {'normal', 'atrasados'}}}
            'total_por_rubrica': total_por_rubrica,
            'total_geral': total_geral,
        }
