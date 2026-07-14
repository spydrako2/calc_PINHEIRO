"""
Writer da planilha de IR sobre Bônus (RRA) — reproduz a planilha modelo do
escritório, com as FÓRMULAS de cálculo e a aba "Dados" (tabelas IRPF) que elas
referenciam. O programa só lança os inputs (período, data de pagamento, bônus,
dependentes, IR pago); o Excel faz o cálculo e permite auditoria/ajuste.

Uma aba "Cálculo - {TIPO}" por tipo de bônus presente (BR, FUNDEB, DEJEC).
DEJEC é isenção do período todo → IR devido = 0 (recupera todo o IR pago).
"""

from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

from src.core.irpf_rra_tables import TABELAS, DEDUCAO_POR_DEPENDENTE

AZUL = "0D1525"
DOURADO = "B38642"
CINZA = "F2F2F2"
AMARELO = "FFF2CC"
LARANJA = "FCE4D6"
BRANCO = "FFFFFF"

FONT_NAME = "Lato"
MONEY_FMT = '_-"R$"\\ * #,##0.00_-;\\-"R$"\\ * #,##0.00_-;_-"R$"\\ * "-"??_-;_-@_-'
PCT_FMT = "0.0%"
DATE_FMT = "dd/mm/yyyy"

thin = Border(
    left=Side(style="thin", color="D0D0D0"),
    right=Side(style="thin", color="D0D0D0"),
    top=Side(style="thin", color="D0D0D0"),
    bottom=Side(style="thin", color="D0D0D0"),
)

TIPO_LABEL = {
    "BR": "BONIFICAÇÃO POR RESULTADOS (RRA)",
    "FUNDEB": "ABONO FUNDEB (RRA)",
    "DEJEC": "DEJEC — ISENÇÃO",
}

# Colunas A..P (16), como na planilha modelo.
HEADERS = [
    ("A", "PERÍODO DE\nREFERÊNCIA\n(INÍCIO)"),
    ("B", "PERÍODO DE\nREFERÊNCIA\n(FIM)"),
    ("C", "QTD.\nMESES"),
    ("D", "DATA DE\nPAGAMENTO"),
    ("E", "ANO-\nCALENDÁRIO"),
    ("F", "BÔNUS PAGO\nEM FOLHA"),
    ("G", "BASE RRA\nBRUTA"),
    ("H", "Nº DE\nDEPENDENTES"),
    ("I", "DEDUÇÃO POR\nDEPENDENTE"),
    ("J", "BASE DE\nCÁLCULO RRA"),
    ("K", "FAIXA SALARIAL\nTABELA IRPF-RRA"),
    ("L", "ALÍQUOTA\nEFETIVA"),
    ("M", "PARCELA\nDEDUZÍVEL"),
    ("N", "IR DEVIDO"),
    ("O", "IR PAGO\nEM FOLHA"),
    ("P", "DIF.\nAPURADA"),
]


def write_ir_bonus_xlsx(resultado: dict, output_path: str) -> str:
    wb = Workbook()
    wb.remove(wb.active)

    parcelas_por_tipo = resultado.get("parcelas_por_tipo", {})
    nome_cliente = resultado.get("nome_cliente", "")

    if not parcelas_por_tipo:
        # nenhuma parcela — cria aba vazia informativa
        ws = wb.create_sheet("Cálculo")
        ws["A1"] = "Nenhuma parcela de bônus (RRA) encontrada nos holerites."
        _dados_sheet(wb)
        wb.save(output_path)
        return output_path

    for tipo, parcelas in parcelas_por_tipo.items():
        ws = wb.create_sheet(f"Cálculo - {tipo}")
        _preencher_aba(ws, nome_cliente, tipo, parcelas)

    _dados_sheet(wb)
    wb.save(output_path)
    return output_path


def _preencher_aba(ws, nome_cliente, tipo, parcelas):
    is_dejec = tipo == "DEJEC"

    # Título (linha 1)
    ws.merge_cells("A1:P1")
    c = ws["A1"]
    c.value = f"RECÁLCULO DE IR SOBRE {TIPO_LABEL.get(tipo, tipo)}"
    c.font = Font(name=FONT_NAME, size=15, bold=True, color=BRANCO)
    c.fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # Requerente (linha 2)
    ws.merge_cells("A2:P2")
    c = ws["A2"]
    c.value = f"REQUERENTE: {nome_cliente}"
    c.font = Font(name=FONT_NAME, size=12, bold=True, color=BRANCO)
    c.fill = PatternFill(start_color=DOURADO, end_color=DOURADO, fill_type="solid")
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 20

    # Cabeçalho das colunas (linha 3)
    hdr_fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")
    for col, titulo in HEADERS:
        cell = ws[f"{col}3"]
        cell.value = titulo
        cell.font = Font(name=FONT_NAME, size=9, bold=True, color=BRANCO)
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin
    ws.row_dimensions[3].height = 42

    cinza_fill = PatternFill(start_color=CINZA, end_color=CINZA, fill_type="solid")
    amarelo_fill = PatternFill(start_color=AMARELO, end_color=AMARELO, fill_type="solid")

    row = 4
    for p in parcelas:
        _linha_dados(ws, row, p, is_dejec, cinza_fill, amarelo_fill)
        row += 1

    # Linha de TOTAL (soma da coluna P — diferença apurada = valor a recuperar)
    ultima = row - 1
    ws.merge_cells(f"A{row}:O{row}")
    c = ws[f"A{row}"]
    c.value = "TOTAL A RECUPERAR"
    c.font = Font(name=FONT_NAME, size=11, bold=True)
    c.alignment = Alignment(horizontal="right", vertical="center")
    c.fill = amarelo_fill
    c.border = thin
    ct = ws[f"P{row}"]
    ct.value = f"=SUM(P4:P{ultima})" if ultima >= 4 else 0
    ct.number_format = MONEY_FMT
    ct.font = Font(name=FONT_NAME, size=11, bold=True)
    ct.fill = amarelo_fill
    ct.border = thin
    ct.alignment = Alignment(horizontal="right", vertical="center")

    _larguras(ws)
    _layout_impressao(ws)
    ws.freeze_panes = "A4"


def _linha_dados(ws, r, p, is_dejec, cinza_fill, amarelo_fill):
    money = Font(name=FONT_NAME, size=10)

    # A, B — período (datas, input)
    for col, val in (("A", p["inicio"]), ("B", p["fim"])):
        cell = ws[f"{col}{r}"]
        cell.value = val
        cell.number_format = DATE_FMT
        cell.font = money
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin

    # C — qtd meses (fórmula)
    _formula(ws, r, "C", f'=IF(OR(A{r}="",B{r}=""),"",(YEAR(B{r})-YEAR(A{r}))*12+MONTH(B{r})-MONTH(A{r})+1)', fmt="0", center=True)

    # D — data de pagamento (input)
    cell = ws[f"D{r}"]
    cell.value = p["pagamento"]
    cell.number_format = DATE_FMT
    cell.font = money
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = thin

    # E — ano-calendário (fórmula pela data de pagamento)
    _formula(ws, r, "E",
             f'=IF(D{r}="","",IF(D{r}<DATE(2023,5,1),"Ano_2015",IF(D{r}<DATE(2024,2,1),"Ano_2023",IF(D{r}<DATE(2025,5,1),"Ano_2024","Ano_2025"))))',
             fmt="General", center=True)

    # F — bônus pago em folha (input)
    _money(ws, r, "F", p["bonus"])

    # G — base RRA bruta (fórmula)
    _formula(ws, r, "G", f'=IF(OR(F{r}="",C{r}="",C{r}=0),"",F{r}/C{r})')

    # H — nº dependentes (input, default 0)
    cell = ws[f"H{r}"]
    cell.value = p.get("dependentes", 0)
    cell.number_format = "0"
    cell.font = money
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = thin

    # I — dedução por dependente (fórmula → Dados!K3)
    _formula(ws, r, "I", f'=IF(OR(H{r}="",H{r}=0),0,H{r}*Dados!$K$3)')

    # J — base de cálculo RRA (fórmula)
    _formula(ws, r, "J", f'=IF(G{r}="","",G{r}-I{r})')

    # K, L, M — lookup na tabela IRPF (Dados) por ano + faixa
    _formula(ws, r, "K", _lookup_formula(r, "P"), fmt="General")
    _formula(ws, r, "L", _lookup_formula(r, "Q"), fmt=PCT_FMT, fill=cinza_fill)
    _formula(ws, r, "M", _lookup_formula(r, "R"), fill=cinza_fill)

    # N — IR devido. DEJEC: isenção → 0. Demais: fórmula RRA.
    if is_dejec:
        cell = ws[f"N{r}"]
        cell.value = 0
        cell.number_format = MONEY_FMT
        cell.font = money
        cell.alignment = Alignment(horizontal="right", vertical="center")
        cell.border = thin
    else:
        _formula(ws, r, "N", f'=IF(OR(J{r}="",L{r}="",L{r}=0,C{r}=""),0,MAX(0,(J{r}*L{r}-M{r})*C{r}))')

    # O — IR pago em folha (input)
    _money(ws, r, "O", p["ir_pago"])

    # P — diferença apurada = IR pago − IR devido (a recuperar)
    _formula(ws, r, "P", f'=IF(OR(O{r}="",N{r}=""),"",O{r}-N{r})', fill=amarelo_fill, bold=True)


def _lookup_formula(r, col_dados):
    """INDEX/SUMPRODUCT: casa ano-calendário (E) + faixa (J entre LIMITE_INF/SUP)."""
    return (
        f'=IF(OR(J{r}="",E{r}=""),"",IFERROR(INDEX(Dados!${col_dados}$2:${col_dados}$21,'
        f'SUMPRODUCT(--(Dados!$M$2:$M$21=E{r})*--(Dados!$N$2:$N$21<=J{r})*'
        f'--(Dados!$O$2:$O$21>=J{r})*ROW(Dados!$M$2:$M$21))-1),""))'
    )


def _money(ws, r, col, value):
    cell = ws[f"{col}{r}"]
    cell.value = value
    cell.number_format = MONEY_FMT
    cell.font = Font(name=FONT_NAME, size=10)
    cell.alignment = Alignment(horizontal="right", vertical="center")
    cell.border = thin
    return cell


def _formula(ws, r, col, formula, fmt=MONEY_FMT, fill=None, bold=False, center=False):
    cell = ws[f"{col}{r}"]
    cell.value = formula
    cell.number_format = fmt
    cell.font = Font(name=FONT_NAME, size=10, bold=bold)
    cell.border = thin
    cell.alignment = Alignment(
        horizontal="center" if center else "right", vertical="center"
    )
    if fill:
        cell.fill = fill
    return cell


def _larguras(ws):
    widths = {
        "A": 13, "B": 13, "C": 7, "D": 13, "E": 12, "F": 13, "G": 12, "H": 11,
        "I": 12, "J": 13, "K": 22, "L": 10, "M": 12, "N": 13, "O": 13, "P": 14,
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def _dados_sheet(wb):
    """Aba Dados: tabelas IRPF-RRA no layout que as fórmulas referenciam
    (M2:R21) + dedução por dependente em K3."""
    ws = wb.create_sheet("Dados")

    hdr = Font(name=FONT_NAME, size=10, bold=True, color=BRANCO)
    hdr_fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")

    # Dedução por dependente (K2 label, K3 value) — referenciado por Dados!$K$3
    ws["K2"] = "DED. DEP"
    ws["K2"].font = hdr
    ws["K2"].fill = hdr_fill
    ws["K3"] = DEDUCAO_POR_DEPENDENTE
    ws["K3"].number_format = MONEY_FMT

    # Cabeçalho da tabela de lookup (linha 1: M..R)
    for col, titulo in (("M", "ANO_KEY"), ("N", "LIMITE_INF"), ("O", "LIMITE_SUP"),
                        ("P", "FAIXA_DESCR"), ("Q", "ALÍQUOTA"), ("R", "DEDUÇÃO")):
        ws[f"{col}1"] = titulo
        ws[f"{col}1"].font = hdr
        ws[f"{col}1"].fill = hdr_fill

    # Linhas 2..21: 4 anos × 5 faixas
    r = 2
    for ano in ("Ano_2015", "Ano_2023", "Ano_2024", "Ano_2025"):
        for faixa in TABELAS[ano]:
            ws[f"M{r}"] = ano
            ws[f"N{r}"] = faixa.limite_inf
            ws[f"O{r}"] = faixa.limite_sup
            ws[f"P{r}"] = faixa.descricao
            ws[f"Q{r}"] = faixa.aliquota
            ws[f"Q{r}"].number_format = PCT_FMT
            ws[f"R{r}"] = faixa.parcela_deduzir
            ws[f"R{r}"].number_format = MONEY_FMT
            r += 1

    for col in ("K", "M", "N", "O", "P", "Q", "R"):
        ws.column_dimensions[col].width = 16
    ws.column_dimensions["P"].width = 32
    return ws


def _layout_impressao(ws):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins.left = ws.page_margins.right = 0.3
    ws.page_margins.top = ws.page_margins.bottom = 0.5
