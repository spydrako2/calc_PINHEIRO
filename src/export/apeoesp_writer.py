"""
XLSX writer para Tese APEOESP — Quinquênio e Sexta Parte sobre Gratificações.

Estrutura por ano: 12 meses + linha 13° Salário + linha 1/3 Férias, seguindo
a planilha modelo do escritório. Layout no padrão visual Pinheiro (mesmo das
demais teses) e impressão em paisagem, todas as colunas em uma página.
"""

from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from openpyxl.worksheet.properties import PageSetupProperties

from src.teses.base_tese import BaseTese

# Identidade visual Pinheiro (igual às demais planilhas)
AZUL = "0D1525"
DOURADO = "B38642"
CINZA = "F2F2F2"
AMARELO = "FFF2CC"       # atrasados (fórmula auditável)
VERDE = "E2EFDA"         # 13° salário e 1/3 de férias
BRANCO = "FFFFFF"

FONT_NAME = "Lato"
MONEY_FMT = '_-"R$"\\ * #,##0.00_-;\\-"R$"\\ * #,##0.00_-;_-"R$"\\ * #,##0.00_-;_-@_-'
PCT_FMT = "0.00%"

thin = Border(
    left=Side(style="thin", color="D0D0D0"),
    right=Side(style="thin", color="D0D0D0"),
    top=Side(style="thin", color="D0D0D0"),
    bottom=Side(style="thin", color="D0D0D0"),
)


def _months_for_year_in_range(year_str: str, min_per: str, max_per: str) -> list:
    """Return all YYYY-MM months for year_str that fall within [min_per, max_per]."""
    y = int(year_str)
    min_y, min_m = int(min_per[:4]), int(min_per[5:7])
    max_y, max_m = int(max_per[:4]), int(max_per[5:7])
    start_m = min_m if y == min_y else 1
    end_m = max_m if y == max_y else 12
    return [f"{y:04d}-{m:02d}" for m in range(start_m, end_m + 1)]


# Colunas fixas (índices 1-based)
COL_DATA     = 1
COL_GRATIF   = 2
COL_GTE      = 3
COL_GAM      = 4
COL_TOTAL_V  = 5
COL_QUINQ    = 6
COL_PCT      = 7
COL_DQUINQ   = 8
COL_SEXTA    = 9
COL_D6P      = 10
COL_TOTAL    = 11

HEADERS = [
    "DATA DE\nPAGAMENTO",
    "GRATIFICAÇÃO\nGERAL",
    "GTE — GRATIFICAÇÃO POR\nTRABALHO EDUCACIONAL",
    "GAM — GRATIFICAÇÃO POR\nATIVIDADE DE MAGISTÉRIO",
    "TOTAL VANTAGENS\nINTEGRAIS",
    "QTDE.\nQUINQUÊNIOS",
    "PORCENTAGEM",
    "DIFERENÇA\nQUINQUÊNIOS",
    "TEM\n6ª PARTE?",
    "DIFERENÇA\n6ª PARTE",
    "TOTAL DEVIDO",
]

COLS_CINZA = {COL_TOTAL_V, COL_PCT, COL_DQUINQ, COL_D6P}   # colunas de fórmula intermediária


def _col_formula(normal: float, atrasados: list):
    """Retorna '=normal+atraso1+...' (fórmula auditável) ou valor simples."""
    if not atrasados:
        return normal or None
    parts = []
    if normal:
        parts.append(f"{normal:.2f}")
    for _, val in atrasados:
        parts.append(f"{val:.2f}")
    return ("=" + "+".join(parts)) if parts else None


def _comment_atrasados(normal, atrasados):
    linhas = []
    if normal:
        linhas.append(f"Normal: R$ {normal:.2f}")
    for comp_pgto, val in atrasados:
        pgto = BaseTese.format_comp_display(BaseTese.mes_pagamento(comp_pgto))
        linhas.append(f"Atraso pago em {pgto}: R$ {val:.2f}")
    return Comment("\n".join(linhas), "HoleritePRO")


def write_apeoesp_xlsx(resultado: dict, output_path: str) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Quinquênio e 6ª Parte"

    last_col = get_column_letter(COL_TOTAL)

    money_font = Font(name=FONT_NAME, size=10)
    bold10 = Font(name=FONT_NAME, size=10, bold=True)
    cinza_fill = PatternFill(start_color=CINZA, end_color=CINZA, fill_type="solid")
    amarelo_fill = PatternFill(start_color=AMARELO, end_color=AMARELO, fill_type="solid")
    verde_fill = PatternFill(start_color=VERDE, end_color=VERDE, fill_type="solid")

    # --- Título (linha 1) — banner azul ---
    ws.merge_cells(f"A1:{last_col}1")
    t = ws["A1"]
    t.value = "QUINQUÊNIO E SEXTA PARTE — GRATIFICAÇÕES APEOESP"
    t.font = Font(name=FONT_NAME, size=15, bold=True, color=BRANCO)
    t.fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # --- Requerente (linha 2) — banner dourado ---
    ws.merge_cells(f"A2:{last_col}2")
    s = ws["A2"]
    s.value = f"REQUERENTE: {resultado['nome_cliente']}"
    s.font = Font(name=FONT_NAME, size=12, bold=True, color=BRANCO)
    s.fill = PatternFill(start_color=DOURADO, end_color=DOURADO, fill_type="solid")
    s.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 20

    # --- Cabeçalho da tabela (linha 4) ---
    HDR = 4
    hdr_fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")
    for col, h in enumerate(HEADERS, 1):
        c = ws.cell(row=HDR, column=col, value=h)
        c.font = Font(name=FONT_NAME, size=9, bold=True, color=BRANCO)
        c.fill = hdr_fill
        c.border = thin
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[HDR].height = 42

    # --- Agrupar períodos por ano ---
    periodos = resultado["periodos"]
    all_sorted = sorted(periodos.keys())
    years = defaultdict(list)
    for per in all_sorted:
        years[per[:4]].append(per)

    min_per = all_sorted[0] if all_sorted else ""
    max_per = all_sorted[-1] if all_sorted else ""

    current_row = HDR + 1
    all_total_rows, all_13_rows, all_13f_rows = [], [], []

    for year, _ in sorted(years.items()):
        all_months_in_year = _months_for_year_in_range(year, min_per, max_per)
        year_total_rows = []

        for per in all_months_in_year:
            row = current_row
            yyyy, mm = per.split("-")

            # Data (col A)
            cd = ws.cell(row=row, column=COL_DATA, value=f"{mm}/{yyyy}")
            cd.border = thin
            cd.font = money_font
            cd.alignment = Alignment(horizontal="center", vertical="center")

            if per not in periodos:
                for col in range(2, COL_TOTAL + 1):
                    cell = ws.cell(row=row, column=col)
                    cell.border = thin
                    if col in COLS_CINZA:
                        cell.fill = cinza_fill
                year_total_rows.append(row)
                all_total_rows.append(row)
                current_row += 1
                continue

            d = periodos[per]

            # B, C, D: gratificações (fórmula auditável se houver atrasados)
            for col, base_n, base_a in (
                (COL_GRATIF, "gratif_geral_normal", "gratif_geral_atrasados"),
                (COL_GTE, "gte_normal", "gte_atrasados"),
                (COL_GAM, "gam_normal", "gam_atrasados"),
            ):
                gn = d.get(base_n, 0.0)
                ga = d.get(base_a, [])
                c = ws.cell(row=row, column=col, value=_col_formula(gn, ga))
                c.border = thin
                c.number_format = MONEY_FMT
                c.font = money_font
                c.alignment = Alignment(horizontal="right", vertical="center")
                if ga:
                    # Fundo branco (não pinta) — só o comentário explica o atraso,
                    # para não ficar trabalhoso editar/repintar à mão.
                    c.comment = _comment_atrasados(gn, ga)

            # E: Total Vantagens = SUM(B:D)
            _cell(ws, row, COL_TOTAL_V, f"=SUM(B{row}:D{row})", MONEY_FMT, fill=cinza_fill)
            # F: Quinquênios
            cq = ws.cell(row=row, column=COL_QUINQ, value=d["quinquenios"] or None)
            cq.border = thin
            cq.font = money_font
            cq.alignment = Alignment(horizontal="center", vertical="center")
            # G: Porcentagem = F*5%
            _cell(ws, row, COL_PCT, f"=F{row}*5%", PCT_FMT, fill=cinza_fill)
            # H: Diferença Quinquênios = E*G
            _cell(ws, row, COL_DQUINQ, f"=E{row}*G{row}", MONEY_FMT, fill=cinza_fill)
            # I: Tem 6ª Parte?
            ci = ws.cell(row=row, column=COL_SEXTA, value="Sim" if d["tem_sexta_parte"] else "Não")
            ci.border = thin
            ci.font = money_font
            ci.alignment = Alignment(horizontal="center", vertical="center")
            # J: Diferença 6ª Parte = IF(I="Sim",H/6,0)
            _cell(ws, row, COL_D6P, f'=IF(I{row}="Sim",(H{row})/6,0)', MONEY_FMT, fill=cinza_fill)
            # K: Total Devido = H+J
            _cell(ws, row, COL_TOTAL, f"=H{row}+J{row}", MONEY_FMT, fill=amarelo_fill, bold=True)

            year_total_rows.append(row)
            all_total_rows.append(row)
            current_row += 1

        # --- 13° Salário e 1/3 Férias (fim do ano) ---
        row_13 = current_row
        _linha_verde(ws, row_13, "13º SALÁRIO", verde_fill)
        # 13º = SOMA dos meses do ano / 12 (intervalo contíguo)
        faixa_ano = f"K{year_total_rows[0]}:K{year_total_rows[-1]}" if year_total_rows else "0"
        _cell(ws, row_13, COL_TOTAL, f"=SUM({faixa_ano})/12", MONEY_FMT, fill=verde_fill, bold=True)
        all_13_rows.append(row_13)
        current_row += 1

        row_ferias = current_row
        _linha_verde(ws, row_ferias, "1/3 FÉRIAS", verde_fill)
        _cell(ws, row_ferias, COL_TOTAL, f"=K{row_13}/3", MONEY_FMT, fill=verde_fill, bold=True)
        all_13f_rows.append(row_ferias)
        current_row += 1

    # --- TOTAL GERAL ---
    total_row = current_row + 1
    ws.merge_cells(f"A{total_row}:{get_column_letter(COL_TOTAL - 1)}{total_row}")
    ct = ws.cell(row=total_row, column=COL_DATA, value="TOTAL GERAL")
    ct.font = Font(name=FONT_NAME, size=12, bold=True, color=BRANCO)
    ct.fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")
    ct.alignment = Alignment(horizontal="right", vertical="center")
    ct.border = thin
    # TOTAL GERAL = SOMA de toda a coluna K (meses + 13º + 1/3 férias),
    # que é um intervalo contíguo da 1ª linha de dados até a última.
    ultima_linha = all_13f_rows[-1] if all_13f_rows else (all_total_rows[-1] if all_total_rows else HDR + 1)
    _cell(ws, total_row, COL_TOTAL, f"=SUM(K{HDR + 1}:K{ultima_linha})", MONEY_FMT, fill=amarelo_fill, bold=True)

    # --- Larguras ---
    widths = [14, 18, 26, 26, 18, 14, 13, 16, 12, 15, 16]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A5"
    _layout_impressao(ws)

    wb.save(output_path)
    return output_path


def _cell(ws, row, col, value, fmt, fill=None, bold=False):
    c = ws.cell(row=row, column=col, value=value)
    c.number_format = fmt
    c.border = thin
    c.font = Font(name=FONT_NAME, size=10, bold=bold)
    c.alignment = Alignment(horizontal="right", vertical="center")
    if fill:
        c.fill = fill
    return c


def _linha_verde(ws, row, rotulo, verde_fill):
    c = ws.cell(row=row, column=COL_DATA, value=rotulo)
    c.font = Font(name=FONT_NAME, size=10, bold=True)
    c.fill = verde_fill
    c.border = thin
    c.alignment = Alignment(horizontal="center", vertical="center")
    for col in range(2, COL_TOTAL + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = verde_fill
        cell.border = thin


def _layout_impressao(ws):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5
