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
        # {periodo: {codigo: float}}
        pivot: dict = defaultdict(lambda: defaultdict(float))
        # {codigo: label} — ordem de aparição
        rubrica_labels: dict = {}

        for p in pages:
            if not parser.detect_template(p.texto):
                continue

            comp = BaseTese._extract_competencia(p.texto)
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

                # Atribuir ao período de competência original (periodo_fim) se disponível
                periodo = v.periodo_fim or comp
                # Descontos são negativos no holerite; armazenar como positivo (valor a cobrar)
                pivot[periodo][v.codigo] += abs(v.valor)

        # Ordenar períodos cronologicamente
        sorted_periods = sorted(pivot.keys())
        # Ordenar códigos numericamente
        sorted_codes = sorted(rubrica_labels.keys())

        periodos_out = OrderedDict()
        for per in sorted_periods:
            periodos_out[per] = {
                code: pivot[per].get(code, 0.0)
                for code in sorted_codes
            }

        total_por_rubrica = {
            code: sum(pivot[per].get(code, 0.0) for per in sorted_periods)
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
            'rubricas': rubricas,            # {code: label}
            'periodos': periodos_out,         # {periodo: {code: value}}
            'total_por_rubrica': total_por_rubrica,
            'total_geral': total_geral,
        }
