"""
XLSX writer para Tese IAMSPE.
Gera planilha pivot: linhas=meses, colunas=rubricas IAMSPE, última=VALOR DEVIDO.
Formato idêntico à planilha de referência do escritório.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from src.teses.base_tese import BaseTese


def _all_months_in_range(sorted_periods: list) -> list:
    """Return every YYYY-MM month from min to max of sorted_periods, filling gaps."""
    if not sorted_periods:
        return []
    start, end = sorted_periods[0], sorted_periods[-1]
    months = []
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (y, m) <= (ey, em):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def write_iamspe_xlsx(resultado: dict, output_path: str) -> str:
    """
    Gera XLSX no formato de acúmulo IAMSPE.

    Args:
        resultado: dict de TeseIAMSPE.processar()
        output_path: caminho do arquivo de saída

    Returns:
        output_path
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Acúmulo IAMSPE"

    # --- Estilos ---
    AZUL = "1A365D"
    DOURADO = "C7A76D"
    money_fmt = '#,##0.00'

    thin = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )
    hdr_font = Font(bold=True, color="FFFFFF", size=10)
    hdr_fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")
    total_fill    = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    atrasado_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    total_font = Font(bold=True, size=10)
    title_font = Font(bold=True, size=13, color=AZUL)
    subtitle_font = Font(bold=True, size=11, color=DOURADO)

    rubricas = resultado['rubricas']       # OrderedDict {code: label}
    periodos = resultado['periodos']       # OrderedDict {period: {code: value}}
    sorted_codes = list(rubricas.keys())

    # Cálculo de colunas: DATA + rubricas + VALOR DEVIDO
    total_col = 1 + len(sorted_codes) + 1
    last_col_letter = get_column_letter(total_col)

    # --- Cabeçalho do documento ---
    ws.merge_cells(f'A1:{last_col_letter}1')
    t = ws['A1']
    t.value = "CONTRIBUIÇÃO DO IAMSPE SOBRE O SEGUNDO VÍNCULO"
    t.font = title_font
    t.alignment = Alignment(horizontal='center')

    ws.merge_cells(f'A2:{last_col_letter}2')
    s = ws['A2']
    s.value = f"REQUERENTE: {resultado['nome_cliente']}"
    s.font = subtitle_font
    s.alignment = Alignment(horizontal='center')

    # --- Linha de cabeçalho da tabela ---
    HDR = 4

    c = ws.cell(row=HDR, column=1, value="DATA DE PAGAMENTO")
    c.font = hdr_font
    c.fill = hdr_fill
    c.border = thin
    c.alignment = Alignment(horizontal='center', wrap_text=True)

    for i, code in enumerate(sorted_codes):
        col = 2 + i
        c = ws.cell(row=HDR, column=col, value=rubricas[code])
        c.font = hdr_font
        c.fill = hdr_fill
        c.border = thin
        c.alignment = Alignment(horizontal='center', wrap_text=True)

    c = ws.cell(row=HDR, column=total_col, value="VALOR DEVIDO:")
    c.font = hdr_font
    c.fill = hdr_fill
    c.border = thin
    c.alignment = Alignment(horizontal='center', wrap_text=True)

    decimo = resultado.get('decimo_terceiro', {})   # {ano: {code: {'normal','atrasados'}}}
    dec_fill = PatternFill(start_color="FDF3E0", end_color="FDF3E0", fill_type="solid")
    empty_cell = {'normal': 0.0, 'atrasados': []}

    def _write_cell(row, col, cell_data, fill=None):
        """Escreve uma célula de rubrica (valor direto ou fórmula com atrasados)."""
        normal    = cell_data['normal']
        atrasados = cell_data['atrasados']
        total     = normal + sum(v for _, v in atrasados)

        if atrasados:
            parts = []
            if normal:
                parts.append(f"{normal:.2f}")
            for _, v in atrasados:
                parts.append(f"{v:.2f}")
            cell_val = ("=" + "+".join(parts)) if parts else None
            c = ws.cell(row=row, column=col, value=cell_val)
            c.fill = atrasado_fill
            comment_lines = []
            if normal:
                comment_lines.append(f"Normal: R$ {normal:.2f}")
            for comp_pgto, val in atrasados:
                pgto_display = BaseTese.format_comp_display(BaseTese.mes_pagamento(comp_pgto))
                comment_lines.append(f"Atraso pago em {pgto_display}: R$ {val:.2f}")
            c.comment = Comment("\n".join(comment_lines), "HoleritePRO")
        else:
            total = round(total, 2)
            c = ws.cell(row=row, column=col, value=total if total != 0.0 else None)
            if fill:
                c.fill = fill
        c.number_format = money_fmt
        c.border = thin

    # --- Linhas de dados ---
    data_start = HDR + 1
    sorted_periods = sorted(periodos.keys())
    all_months = _all_months_in_range(sorted_periods)

    # Sequência de linhas: meses + linha "13º salário" após dezembro de cada ano.
    sequence = []  # ('month', 'AAAA-MM') | ('decimo', 'AAAA')
    placed_years = set()
    for i, per in enumerate(all_months):
        sequence.append(('month', per))
        year = per[:4]  # 'AAAA'
        is_last_of_year = (
            per[5:7] == '12'
            or i == len(all_months) - 1
            or all_months[i + 1][:4] != year
        )
        if is_last_of_year and year in decimo and year not in placed_years:
            sequence.append(('decimo', year))
            placed_years.add(year)
    # Anos de 13º sem mês correspondente na faixa (fallback: ao final)
    for year in sorted(decimo.keys()):
        if year not in placed_years:
            sequence.append(('decimo', year))
            placed_years.add(year)

    row = data_start
    for kind, key in sequence:
        if kind == 'month':
            per = key
            yyyy, mm = per.split('-')
            c = ws.cell(row=row, column=1, value=f"{mm}/{yyyy}")
            c.border = thin
            c.alignment = Alignment(horizontal='center')

            if per not in periodos:
                for col in range(2, total_col + 1):
                    ws.cell(row=row, column=col).border = thin
                row += 1
                continue

            for j, code in enumerate(sorted_codes):
                _write_cell(row, 2 + j, periodos[per].get(code, empty_cell))
        else:  # decimo
            year = key
            c = ws.cell(row=row, column=1, value=f"13º Salário/{year}")
            c.font = Font(bold=True, size=10)
            c.fill = dec_fill
            c.border = thin
            c.alignment = Alignment(horizontal='center')

            year_data = decimo[year]
            for j, code in enumerate(sorted_codes):
                _write_cell(row, 2 + j, year_data.get(code, empty_cell), fill=dec_fill)

        # Coluna VALOR DEVIDO = SUM(B{row}:{prev_col}{row})
        data_last_col = get_column_letter(total_col - 1)
        c = ws.cell(row=row, column=total_col)
        c.value = f"=SUM(B{row}:{data_last_col}{row})"
        c.number_format = money_fmt
        c.border = thin
        if kind == 'decimo':
            c.fill = dec_fill
        row += 1

    # --- Linha de totais ---
    last_data = row - 1
    total_row = row

    c = ws.cell(row=total_row, column=1, value="TOTAL")
    c.font = total_font
    c.fill = total_fill
    c.border = thin

    for j, code in enumerate(sorted_codes):
        col = 2 + j
        col_letter = get_column_letter(col)
        c = ws.cell(row=total_row, column=col)
        c.value = f"=SUM({col_letter}{data_start}:{col_letter}{last_data})"
        c.number_format = money_fmt
        c.font = total_font
        c.fill = total_fill
        c.border = thin

    # Total geral (coluna VALOR DEVIDO)
    total_col_letter = get_column_letter(total_col)
    c = ws.cell(row=total_row, column=total_col)
    c.value = f"=SUM({total_col_letter}{data_start}:{total_col_letter}{last_data})"
    c.number_format = money_fmt
    c.font = total_font
    c.fill = total_fill
    c.border = thin

    # --- Largura das colunas ---
    ws.column_dimensions['A'].width = 18
    for j in range(len(sorted_codes)):
        ws.column_dimensions[get_column_letter(2 + j)].width = 24
    ws.column_dimensions[get_column_letter(total_col)].width = 16

    # Altura da linha de cabeçalho (para labels longos)
    ws.row_dimensions[HDR].height = 50

    wb.save(output_path)
    return output_path
