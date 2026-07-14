"""
Tese: IR sobre Bônus pago acumuladamente (RRA — Rendimentos Recebidos
Acumuladamente).

O bônus (Bonificação por Resultados, Abono FUNDEB, DEJEC) é pago de uma vez
num holerite SUPLEMENTAR, mas refere-se a vários meses passados. Na folha, o
IR foi retido como renda de um mês só (faixa alta). Pelo RRA, o IR é
recalculado dividindo o bônus pelo nº de meses de referência → faixa menor
→ a diferença (IR retido − IR devido) é recuperável.

Tipos de bônus reconhecidos:
    - BR     — "BONIFIC. POR RESULT..." (cód. 004239 policial, 004180/004260 docente)
    - FUNDEB — "ABONO FUNDEB" (cód. 015060)
    - DEJEC  — "DEJEC..." (cód. 014084)

Regras de negócio (definidas pelo escritório):
    - Cada PARCELA de bônus (um período de referência) vira uma linha.
    - O IR retido no holerite (cód. 070012) é ÚNICO para todas as parcelas
      daquele holerite → é rateado entre elas proporcionalmente ao valor.
    - FUNDEB: só é restituível o que foi PAGO até 2022 (ano de pagamento ≤ 2022).
    - DEJEC: isenção do período todo → IR devido = 0, recupera todo o IR pago.
    - Dependentes: não vêm no holerite suplementar → default 0 (editável na planilha).

O cálculo em si (tabelas IRPF-RRA) fica em `src/core/irpf_rra_tables.py`, e é
reproduzido por FÓRMULAS na planilha de saída (auditável pelo advogado).
"""

import re
import calendar
from datetime import date
from collections import defaultdict, OrderedDict

from src.core.pdf_reader import PDFReader
from src.core.parsers.ddpe_parser import DDPEParser
from src.core.irpf_rra_tables import ano_calendario, ir_devido_rra
from src.teses.base_tese import BaseTese

CODIGO_IR_FONTE = "070012"        # IMPOSTO DE RENDA NA FONTE (retido na folha)

# Ano de pagamento máximo restituível para o Abono FUNDEB.
FUNDEB_ANO_PAGAMENTO_MAX = 2022


def classificar_bonus(denominacao: str) -> str | None:
    """Classifica a verba de bônus pelo nome. None se não for bônus."""
    d = denominacao.upper()
    if "BONIF" in d and "RESULT" in d:
        return "BR"
    if "FUNDEB" in d:
        return "FUNDEB"
    if "DEJEC" in d:
        return "DEJEC"
    return None


class TeseIRBonus(BaseTese):
    nome = "IR sobre Bônus (RRA)"
    descricao = (
        "Recupera o IRRF retido a maior sobre bônus pagos acumuladamente "
        "(Bonificação por Resultados, Abono FUNDEB, DEJEC). O imposto é "
        "recalculado pelo regime de Rendimentos Recebidos Acumuladamente "
        "(RRA), diluindo o valor nos meses de referência."
    )
    tese_tipo = "ir_bonus"

    verba_codigo = ""
    verba_nome = ""

    def processar(self, pdf_path: str) -> dict:
        pages = PDFReader.read_pdf(pdf_path)
        _ddpe = DDPEParser()

        nome_cliente = "UNKNOWN"
        # parcelas agrupadas por tipo (BR / FUNDEB / DEJEC)
        parcelas_por_tipo: dict = defaultdict(list)

        for p in pages:
            if not _ddpe.detect_template(p.texto):
                continue

            if nome_cliente == "UNKNOWN":
                nome_cliente = self._extract_nome_ddpe(p.texto)

            pag_date = self._extract_data_pagamento(p.texto)

            pi = DDPEParser()
            pi.paginas = [p]
            verbas = pi._extract_verbas()

            # bônus retroativos (A/R) com período de referência
            bonus = [
                (v, classificar_bonus(v.denominacao))
                for v in verbas
                if classificar_bonus(v.denominacao) and v.natureza.value in ("A", "R")
            ]
            if not bonus:
                continue

            # IR retido no holerite (soma das linhas 070012, em positivo)
            ir_total = sum(-v.valor for v in verbas if v.codigo == CODIGO_IR_FONTE)
            soma_bonus = sum(v.valor for v, _ in bonus)

            for v, tipo in bonus:
                ini_ym = v.periodo_inicio or v.periodo_fim
                fim_ym = v.periodo_fim or ini_ym
                if not ini_ym or not fim_ym:
                    continue

                # rateio do IR proporcional ao valor da parcela
                ir_pago = ir_total * (v.valor / soma_bonus) if soma_bonus else 0.0

                parcela = {
                    "tipo": tipo,
                    "inicio": self._primeiro_dia(ini_ym),
                    "fim": self._ultimo_dia(fim_ym),
                    "pagamento": pag_date,
                    "bonus": round(v.valor, 2),
                    "dependentes": 0,
                    "ir_pago": round(ir_pago, 2),
                }
                parcelas_por_tipo[tipo].append(parcela)

        # FUNDEB: só restituível o que foi pago até 2022
        if "FUNDEB" in parcelas_por_tipo:
            parcelas_por_tipo["FUNDEB"] = [
                p for p in parcelas_por_tipo["FUNDEB"]
                if p["pagamento"] and p["pagamento"].year <= FUNDEB_ANO_PAGAMENTO_MAX
            ]
            if not parcelas_por_tipo["FUNDEB"]:
                del parcelas_por_tipo["FUNDEB"]

        # ordena parcelas por data de pagamento dentro de cada tipo
        for tipo in parcelas_por_tipo:
            parcelas_por_tipo[tipo].sort(key=lambda x: (x["pagamento"] or date.min, x["inicio"]))

        total_recuperar = self._calcular_total(parcelas_por_tipo)

        return {
            "nome_cliente": nome_cliente,
            "tese_nome": self.nome,
            "tese_descricao": self.descricao,
            "tese_tipo": self.tese_tipo,
            "parcelas_por_tipo": OrderedDict(
                (t, parcelas_por_tipo[t])
                for t in ("BR", "FUNDEB", "DEJEC") if t in parcelas_por_tipo
            ),
            "total_recuperar": total_recuperar,
        }

    # ---- cálculo em Python (espelha as fórmulas da planilha, p/ preview/total) ----

    @classmethod
    def _calcular_total(cls, parcelas_por_tipo: dict) -> float:
        total = 0.0
        for tipo, parcelas in parcelas_por_tipo.items():
            for p in parcelas:
                total += cls.diferenca_parcela(p, tipo)
        return round(total, 2)

    @staticmethod
    def meses_periodo(inicio: date, fim: date) -> int:
        return (fim.year - inicio.year) * 12 + (fim.month - inicio.month) + 1

    @classmethod
    def diferenca_parcela(cls, parcela: dict, tipo: str) -> float:
        """IR pago − IR devido (RRA). DEJEC = isenção → IR devido 0."""
        if tipo == "DEJEC":
            return round(parcela["ir_pago"], 2)
        n = cls.meses_periodo(parcela["inicio"], parcela["fim"])
        pag = parcela["pagamento"]
        ano = ano_calendario(f"{pag.year:04d}-{pag.month:02d}") if pag else "Ano_2025"
        calc = ir_devido_rra(parcela["bonus"], n, ano, parcela["dependentes"])
        return round(parcela["ir_pago"] - calc["ir_devido"], 2)

    # ---- extração ----

    @staticmethod
    def _extract_nome_ddpe(texto: str) -> str:
        lines = texto.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("Nome") and "Reg" in line:
                if i + 1 < len(lines):
                    m = re.match(r"^([A-ZÁÉÍÓÚÂÃÕÊÔÇÜ ]+?)\s+\d", lines[i + 1])
                    if m and len(m.group(1).strip()) > 3:
                        return m.group(1).strip()
        return "UNKNOWN"

    @staticmethod
    def _extract_data_pagamento(texto: str):
        """Data de pagamento exata: 'FOLHA ... - MM/YYYY  DD/MM/YYYY'."""
        m = re.search(r"FOLHA\s+\w+\s*-\s*\d{2}/\d{4}\s+(\d{2})/(\d{2})/(\d{4})", texto)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return date(y, mo, d)
            except ValueError:
                return None
        return None

    @staticmethod
    def _primeiro_dia(yyyy_mm: str) -> date:
        y, m = int(yyyy_mm[:4]), int(yyyy_mm[5:7])
        return date(y, m, 1)

    @staticmethod
    def _ultimo_dia(yyyy_mm: str) -> date:
        y, m = int(yyyy_mm[:4]), int(yyyy_mm[5:7])
        return date(y, m, calendar.monthrange(y, m)[1])
