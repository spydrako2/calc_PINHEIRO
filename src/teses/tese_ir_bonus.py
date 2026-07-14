"""
Tese: IR sobre Bônus pago acumuladamente.

Dois tratamentos, como na planilha modelo do escritório:

  BLOCO 1 — RRA (Rendimentos Recebidos Acumuladamente):
    Só a BONIFICAÇÃO POR RESULTADOS (BR). O bônus é pago de uma vez mas
    refere-se a vários meses; o IR retido (faixa alta) é recalculado
    diluindo o valor nos meses de referência → faixa menor. Diferença
    (IR pago − IR devido RRA) é recuperável.

  BLOCO 2 — ISENÇÃO:
    ABONO FUNDEB e DEJEC. Verbas isentas de IR → o IR retido é restituível
    por INTEIRO (IR devido = 0, diferença = todo o IR pago).

Verbas reconhecidas (por nome):
    - BR     — "BONIFIC. POR RESULT..." (cód. 004239 policial, 004180/004260 docente)
    - FUNDEB — "ABONO FUNDEB" (cód. 015060)   → isenção
    - DEJEC  — "DEJEC..." (cód. 014084)        → isenção

Regras de negócio (escritório):
    - Cada PARCELA de bônus (um período de referência) vira uma linha.
    - O IR retido no holerite (cód. 070012) é ÚNICO para todas as parcelas
      daquele holerite → rateado entre elas proporcionalmente ao valor.
    - Nº de dependentes: vem na denominação da linha do IR
      ("IMPOSTO DE RENDA NA FONTE 002 DEPTE" → 2; sem número → 0).
    - FUNDEB: só é restituível o que foi PAGO até 2022 (ano de pagamento ≤ 2022).
    - Aceita vários PDFs (holerite normal + suplementar) numa só planilha.

O cálculo RRA (tabelas IRPF) fica em `src/core/irpf_rra_tables.py`, e é
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

# Tipos que vão para o bloco de isenção (restituição total).
TIPOS_ISENCAO = ("FUNDEB", "DEJEC")


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
    nome = "IR sobre Bônus (RRA / Isenção)"
    descricao = (
        "Recupera o IRRF retido sobre bônus: Bonificação por Resultados pela "
        "regra RRA (imposto diluído nos meses de referência) e Abono FUNDEB / "
        "DEJEC por isenção (restituição integral do imposto retido)."
    )
    tese_tipo = "ir_bonus"

    verba_codigo = ""
    verba_nome = ""

    def processar(self, pdf_path) -> dict:
        """`pdf_path` pode ser um caminho (str) ou uma lista de caminhos
        (holerite normal + suplementar do mesmo cliente)."""
        paths = [pdf_path] if isinstance(pdf_path, str) else list(pdf_path)
        _ddpe = DDPEParser()

        nome_cliente = "UNKNOWN"
        parcelas_rra: list = []                      # BR
        parcelas_isencao: dict = defaultdict(list)   # FUNDEB / DEJEC
        vistos: set = set()   # dedup se o mesmo holerite vier em 2 PDFs

        for path in paths:
            pages = PDFReader.read_pdf(path)
            for p in pages:
                if not _ddpe.detect_template(p.texto):
                    continue

                if nome_cliente == "UNKNOWN":
                    nome_cliente = self._extract_nome_ddpe(p.texto)

                pag_date = self._extract_data_pagamento(p.texto)

                pi = DDPEParser()
                pi.paginas = [p]
                verbas = pi._extract_verbas()

                bonus = [
                    (v, classificar_bonus(v.denominacao))
                    for v in verbas
                    if classificar_bonus(v.denominacao) and v.natureza.value in ("A", "R")
                ]
                if not bonus:
                    continue

                # IR retido do holerite (070012) e nº de dependentes (na denominação)
                ir_lines = [v for v in verbas if v.codigo == CODIGO_IR_FONTE]
                ir_total = sum(-v.valor for v in ir_lines)
                dependentes = self._extract_dependentes(ir_lines)
                soma_bonus = sum(v.valor for v, _ in bonus)

                for v, tipo in bonus:
                    ini_ym = v.periodo_inicio or v.periodo_fim
                    fim_ym = v.periodo_fim or ini_ym
                    if not ini_ym or not fim_ym:
                        continue

                    ir_pago = ir_total * (v.valor / soma_bonus) if soma_bonus else 0.0
                    parcela = {
                        "tipo": tipo,
                        "inicio": self._primeiro_dia(ini_ym),
                        "fim": self._ultimo_dia(fim_ym),
                        "pagamento": pag_date,
                        "bonus": round(v.valor, 2),
                        "dependentes": dependentes,
                        "ir_pago": round(ir_pago, 2),
                    }
                    # evita contar 2x a mesma parcela (mesmo holerite em 2 PDFs)
                    chave = (tipo, parcela["inicio"], parcela["fim"],
                             parcela["pagamento"], parcela["bonus"], parcela["ir_pago"])
                    if chave in vistos:
                        continue
                    vistos.add(chave)

                    if tipo == "BR":
                        parcelas_rra.append(parcela)
                    else:
                        parcelas_isencao[tipo].append(parcela)

        # FUNDEB: só restituível o que foi pago até 2022
        if "FUNDEB" in parcelas_isencao:
            parcelas_isencao["FUNDEB"] = [
                p for p in parcelas_isencao["FUNDEB"]
                if p["pagamento"] and p["pagamento"].year <= FUNDEB_ANO_PAGAMENTO_MAX
            ]
            if not parcelas_isencao["FUNDEB"]:
                del parcelas_isencao["FUNDEB"]

        # ordena por data de pagamento
        parcelas_rra.sort(key=lambda x: (x["pagamento"] or date.min, x["inicio"]))
        for tipo in parcelas_isencao:
            parcelas_isencao[tipo].sort(key=lambda x: (x["pagamento"] or date.min, x["inicio"]))

        isencao_ordenado = OrderedDict(
            (t, parcelas_isencao[t]) for t in TIPOS_ISENCAO if t in parcelas_isencao
        )
        total_recuperar = self._calcular_total(parcelas_rra, isencao_ordenado)

        return {
            "nome_cliente": nome_cliente,
            "tese_nome": self.nome,
            "tese_descricao": self.descricao,
            "tese_tipo": self.tese_tipo,
            "rra": parcelas_rra,
            "isencao": isencao_ordenado,
            "total_recuperar": total_recuperar,
        }

    # ---- cálculo em Python (espelha as fórmulas da planilha, p/ preview/total) ----

    @classmethod
    def _calcular_total(cls, parcelas_rra: list, isencao: dict) -> float:
        total = sum(cls.diferenca_rra(p) for p in parcelas_rra)
        for parcelas in isencao.values():
            total += sum(p["ir_pago"] for p in parcelas)   # isenção = IR pago integral
        return round(total, 2)

    @staticmethod
    def meses_periodo(inicio: date, fim: date) -> int:
        return (fim.year - inicio.year) * 12 + (fim.month - inicio.month) + 1

    @classmethod
    def diferenca_rra(cls, parcela: dict) -> float:
        """IR pago − IR devido (RRA), para parcela de Bonificação por Resultados."""
        n = cls.meses_periodo(parcela["inicio"], parcela["fim"])
        pag = parcela["pagamento"]
        ano = ano_calendario(f"{pag.year:04d}-{pag.month:02d}") if pag else "Ano_2025"
        calc = ir_devido_rra(parcela["bonus"], n, ano, parcela["dependentes"])
        return round(parcela["ir_pago"] - calc["ir_devido"], 2)

    # ---- extração ----

    @staticmethod
    def _extract_dependentes(ir_lines) -> int:
        """Nº de dependentes na denominação do IR: '...FONTE 002 DEPTE' → 2."""
        for v in ir_lines:
            m = re.search(r"FONTE\s+(\d+)\s*DEPTE", v.denominacao, re.IGNORECASE)
            if m:
                return int(m.group(1))
        return 0

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
