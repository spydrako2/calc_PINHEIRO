"""
XLSX writer para a tese CHS (Carga Horária Suplementar sobre Piso Docente).

Layout reproduz a planilha modelo Pinheiro:
- 2 abas: "Cálculo ATIVO" e "Cálculo INATIVO"
- Só a aba correspondente à situação atual é preenchida
- 21 colunas (A–U), cabeçalho na linha 3, dados a partir da 4
- Blocos anuais fecham com "13 SALARIO" (+ "1/3 de férias" se ATIVO)
- Última linha: TOTAL BRUTO
- Cores: azul escuro #0D1525 (títulos), dourado #B38642 (requerente),
  cinza #F2F2F2 (colunas cálculo temporal), amarelo #FFF2CC (destaques)
"""

from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

from src.teses.tese_chs import CHS_LABELS
from src.teses.base_tese import BaseTese


AZUL = "0D1525"
DOURADO = "B38642"
CINZA = "F2F2F2"
AMARELO = "FFF2CC"
BRANCO = "FFFFFF"

FONT_NAME = "Lato"
MONEY_FMT = '_-"R$"\\ * #,##0.00_-;\\-"R$"\\ * #,##0.00_-;_-"R$"\\ * "-"??_-;_-@_-'
PCT_FMT = '0%'
DATE_FMT = 'mmm-yy'

thin = Border(
    left=Side(style='thin', color="D0D0D0"),
    right=Side(style='thin', color="D0D0D0"),
    top=Side(style='thin', color="D0D0D0"),
    bottom=Side(style='thin', color="D0D0D0"),
)


def write_chs_xlsx(resultado: dict, output_path: str) -> str:
    wb = Workbook()
    ws_ativo = wb.active
    ws_ativo.title = "Cálculo ATIVO"
    ws_inativo = wb.create_sheet("Cálculo INATIVO")

    situacao = resultado.get('situacao', 'ativo')
    vinculo = resultado.get('vinculo', 'efetivo')
    codigos_chs = resultado.get('codigos_chs_colunas', [])

    # Só preenche a aba da situação atual; a outra fica com estrutura básica
    if situacao == 'ativo':
        _preencher_aba(ws_ativo, resultado, codigos_chs, vinculo, aba_ativa=True)
        _preencher_aba(ws_inativo, resultado, codigos_chs, vinculo, aba_ativa=False, apenas_estrutura=True)
    else:
        _preencher_aba(ws_inativo, resultado, codigos_chs, vinculo, aba_ativa=False)
        _preencher_aba(ws_ativo, resultado, codigos_chs, vinculo, aba_ativa=True, apenas_estrutura=True)

    wb.save(output_path)
    return output_path


def _all_months(sorted_periods: list) -> list:
    if not sorted_periods:
        return []
    y, m = int(sorted_periods[0][:4]), int(sorted_periods[0][5:7])
    ey, em = int(sorted_periods[-1][:4]), int(sorted_periods[-1][5:7])
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _preencher_aba(ws, resultado, codigos_chs, vinculo, aba_ativa: bool, apenas_estrutura: bool = False):
    nome_cliente = resultado['nome_cliente']
    periodos = resultado.get('periodos', {})

    # Última coluna sempre S (fixo, como no modelo)
    last_col = 'S'

    # --- Título (linha 1) ---
    ws.merge_cells(f'A1:{last_col}1')
    c = ws['A1']
    c.value = "RECÁLCULO CARGA HORÁRIA SUPLEMENTAR SOBRE PISO SALARIAL DO MAGISTÉRIO"
    c.font = Font(name=FONT_NAME, size=16, bold=True, color=BRANCO)
    c.fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")
    c.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 29.25

    # --- Requerente (linha 2) ---
    ws.merge_cells(f'A2:{last_col}2')
    c = ws['A2']
    c.value = f"REQUERENTE: {nome_cliente}"
    c.font = Font(name=FONT_NAME, size=12, bold=True, color=BRANCO)
    c.fill = PatternFill(start_color=DOURADO, end_color=DOURADO, fill_type="solid")
    c.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[2].height = 21

    # --- Cabeçalhos (linha 3) ---
    label_col_b = "Cargas Suplementares" if vinculo == 'lei500' and aba_ativa else (
        "Salário Base/\nValor de Referência" if not aba_ativa else "Salário Base"
    )
    headers = {
        1:  ("DATA DE\nPAGAMENTO", None),
        2:  (label_col_b, None),
        3:  ("Piso Salarial\nDocente", None),
        4:  ("Jornada\n(horas)", None),
        5:  ("Horas\nSuplementares", None),
        11: ("CHS Recebida", None),
        12: ("CHS Devida\n(com Piso)", None),
        13: ("Diferença\nCHS Mensal", None),
        14: ("QTDE.\nQUINQUÊNIOS", None),
        15: ("PORCENTAGEM", CINZA),
        16: ("DIFERENÇA\nQUINQUÊNIOS", CINZA),
        17: ("TEM\n6ª PARTE?", None),
        18: ("DIFERENÇA\n6ª PARTE", CINZA),
        19: ("TOTAL DEVIDO", AMARELO),
    }
    # Colunas 6-10: CHS por código (dinâmico)
    for i, codigo in enumerate(codigos_chs):
        headers[6 + i] = (CHS_LABELS.get(codigo, codigo), None)
    # Vazios F-J restantes
    for j in range(6 + len(codigos_chs), 11):
        headers[j] = ("", None)

    hdr_font = Font(name=FONT_NAME, size=9, bold=True, color=BRANCO)
    hdr_fill = PatternFill(start_color=AZUL, end_color=AZUL, fill_type="solid")

    for col in range(1, 20):
        cell = ws.cell(row=3, column=col)
        text, _ = headers.get(col, ("", None))
        cell.value = text
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin
    ws.row_dimensions[3].height = 60

    # --- Column widths ---
    widths = {1: 14, 2: 18, 3: 15, 4: 12, 5: 14, 6: 14, 7: 14, 8: 14, 9: 14, 10: 14,
              11: 15, 12: 16, 13: 15, 14: 13, 15: 14, 16: 15, 17: 12, 18: 14, 19: 16}
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    if apenas_estrutura:
        # Só cabeçalho — aba em branco
        return

    # --- Dados ---
    sorted_p = sorted(periodos.keys())
    all_months = _all_months(sorted_p)
    if not all_months:
        return

    row = 4
    ano_atual = None
    linha_inicio_ano = row
    ultima_linha_dados = row
    linhas_ano_encerrado = []

    money_side = Font(name=FONT_NAME, size=10)
    cinza_fill = PatternFill(start_color=CINZA, end_color=CINZA, fill_type="solid")
    amarelo_fill = PatternFill(start_color=AMARELO, end_color=AMARELO, fill_type="solid")

    for mes in all_months:
        ano = int(mes[:4])

        # Fechamento do ano anterior
        if ano_atual is not None and ano != ano_atual:
            row = _emitir_fechamento_ano(
                ws, row, linha_inicio_ano, ultima_linha_dados, aba_ativa
            )
            linhas_ano_encerrado.append(row - 1)
            linha_inicio_ano = row
            ano_atual = ano
        elif ano_atual is None:
            ano_atual = ano
            linha_inicio_ano = row

        # Linha de dados do mês
        y, m = int(mes[:4]), int(mes[5:7])
        data_pgto = datetime(y, m, 1)

        cell_a = ws.cell(row=row, column=1, value=data_pgto)
        cell_a.number_format = DATE_FMT
        cell_a.font = Font(name=FONT_NAME, size=10, bold=True)
        cell_a.alignment = Alignment(horizontal='center', vertical='center')
        cell_a.border = thin

        if mes in periodos:
            d = periodos[mes]

            # B: Salário Base — fórmula auditável se houver atrasados
            _cell_money_auditavel(
                ws, row, 2, d['salario_base_normal'], d['salario_base_atrasados']
            )
            # C: Piso Salarial Docente — fórmula auditável se houver atrasados
            _cell_money_auditavel(
                ws, row, 3, d['piso_normal'], d['piso_atrasados']
            )

            _cell_num(ws, row, 4, d['jornada_horas'])
            _cell_num(ws, row, 5, d['horas_suplementares'])

            # CHS por código (F-J) — fórmula auditável se houver atrasados
            for i, codigo in enumerate(codigos_chs):
                comp = d['chs_por_codigo'].get(codigo)
                if comp:
                    _cell_money_auditavel(
                        ws, row, 6 + i, comp['normal'], comp['atrasados']
                    )
                else:
                    ws.cell(row=row, column=6 + i).border = thin

            # Preenche colunas vazias F-J com só borda
            for j in range(6 + len(codigos_chs), 11):
                ws.cell(row=row, column=j).border = thin

            # K: CHS Recebida = IF(D=0,0,(B/D)*E)
            _cell_formula(ws, row, 11, f'=IF(D{row}=0,0,(B{row}/D{row})*E{row})')
            # L: CHS Devida (com Piso) = IF(D=0,0,(B+C)/D*E)
            _cell_formula(ws, row, 12, f'=IF(D{row}=0,0,(B{row}+C{row})/D{row}*E{row})')
            # M: Diferença = L-K
            _cell_formula(ws, row, 13, f'=L{row}-K{row}')

            # N: Qtde Quinquênios
            cell_n = ws.cell(row=row, column=14, value=d['quinquenios'] or 0)
            cell_n.font = money_side
            cell_n.alignment = Alignment(horizontal='center', vertical='center')
            cell_n.border = thin

            # O: Porcentagem = N*5%
            _cell_formula(ws, row, 15, f'=N{row}*5%', fill=cinza_fill, fmt=PCT_FMT)
            # P: Diferença Quinq = M*O
            _cell_formula(ws, row, 16, f'=M{row}*O{row}', fill=cinza_fill)

            # Q: Tem 6ª Parte
            cell_q = ws.cell(row=row, column=17, value="Sim" if d['tem_sexta_parte'] else "Não")
            cell_q.font = money_side
            cell_q.alignment = Alignment(horizontal='center', vertical='center')
            cell_q.border = thin

            # R: Diferença 6ª Parte = IF(Q="Sim",(M+P)/6,0)
            _cell_formula(ws, row, 18, f'=IF(Q{row}="Sim",(M{row}+P{row})/6,0)', fill=cinza_fill)
            # S: TOTAL DEVIDO = M+P+R
            _cell_formula(ws, row, 19, f'=M{row}+P{row}+R{row}', fill=amarelo_fill, bold=True)
        else:
            # Mês sem dados — só bordas
            for col in range(2, 20):
                cell = ws.cell(row=row, column=col)
                cell.border = thin
                if col == 15 or col == 16 or col == 18:
                    cell.fill = cinza_fill
                elif col == 19:
                    cell.fill = amarelo_fill

        ultima_linha_dados = row
        row += 1

    # Fecha o último ano
    row = _emitir_fechamento_ano(
        ws, row, linha_inicio_ano, ultima_linha_dados, aba_ativa
    )

    # --- TOTAL BRUTO ---
    _emitir_total_bruto(ws, row, 4, row - 1)


def _cell_money(ws, row, col, value):
    cell = ws.cell(row=row, column=col, value=value)
    cell.number_format = MONEY_FMT
    cell.font = Font(name=FONT_NAME, size=10)
    cell.border = thin
    cell.alignment = Alignment(horizontal='right', vertical='center')
    return cell


def _cell_money_auditavel(ws, row, col, normal, atrasados):
    """
    Emite valor monetário com rastreabilidade de atrasados.

    Sem atrasados: valor normal simples (célula comum).
    Com atrasados: fórmula =normal+atraso1+... em célula amarela + comentário
    detalhando o valor normal e cada atraso (por mês de pagamento). Mesma
    convenção auditável da tese de quinquênios (xlsx_writer).
    """
    if not atrasados:
        return _cell_money(ws, row, col, normal if normal else None)

    parts = []
    if normal:
        parts.append(f"{normal:.2f}")
    for _, val in atrasados:
        parts.append(f"{val:.2f}")
    formula = "+".join(parts) if parts else "0"

    cell = ws.cell(row=row, column=col, value=f"={formula}")
    cell.number_format = MONEY_FMT
    cell.font = Font(name=FONT_NAME, size=10)
    cell.border = thin
    cell.alignment = Alignment(horizontal='right', vertical='center')
    cell.fill = PatternFill(start_color=AMARELO, end_color=AMARELO, fill_type="solid")

    comment_lines = []
    if normal:
        comment_lines.append(f"Normal: R$ {normal:.2f}")
    for comp_pgto, val in atrasados:
        pgto = BaseTese.format_comp_display(BaseTese.mes_pagamento(comp_pgto))
        comment_lines.append(f"Atraso pago em {pgto}: R$ {val:.2f}")
    cell.comment = Comment("\n".join(comment_lines), "HoleritePRO")
    return cell


def _cell_num(ws, row, col, value):
    cell = ws.cell(row=row, column=col, value=value)
    cell.number_format = '0'
    cell.font = Font(name=FONT_NAME, size=10)
    cell.border = thin
    cell.alignment = Alignment(horizontal='center', vertical='center')
    return cell


def _cell_formula(ws, row, col, formula, fill=None, fmt=None, bold=False):
    cell = ws.cell(row=row, column=col, value=formula)
    cell.number_format = fmt or MONEY_FMT
    cell.font = Font(name=FONT_NAME, size=10, bold=bold)
    cell.border = thin
    cell.alignment = Alignment(horizontal='right', vertical='center')
    if fill:
        cell.fill = fill
    return cell


def _emitir_fechamento_ano(ws, row, linha_inicio, linha_fim, aba_ativa: bool) -> int:
    """Emite linha 13 SALARIO (e 1/3 de férias se ATIVO)."""
    amarelo_fill = PatternFill(start_color=AMARELO, end_color=AMARELO, fill_type="solid")
    label_font = Font(name=FONT_NAME, size=10, bold=True)

    # 13 SALARIO
    cell_a = ws.cell(row=row, column=1, value="13 SALARIO")
    cell_a.font = label_font
    cell_a.alignment = Alignment(horizontal='center', vertical='center')
    cell_a.fill = amarelo_fill
    cell_a.border = thin
    for col in range(2, 19):
        c = ws.cell(row=row, column=col)
        c.border = thin
        c.fill = amarelo_fill
    cell_s = ws.cell(
        row=row, column=19,
        value=f'=SUM(S{linha_inicio}:S{linha_fim})/12'
    )
    cell_s.number_format = MONEY_FMT
    cell_s.font = label_font
    cell_s.fill = amarelo_fill
    cell_s.border = thin
    cell_s.alignment = Alignment(horizontal='right', vertical='center')
    linha_13 = row
    row += 1

    # 1/3 de férias (só ATIVO)
    if aba_ativa:
        cell_a = ws.cell(row=row, column=1, value="1/3 de férias")
        cell_a.font = label_font
        cell_a.alignment = Alignment(horizontal='center', vertical='center')
        cell_a.fill = amarelo_fill
        cell_a.border = thin
        for col in range(2, 19):
            c = ws.cell(row=row, column=col)
            c.border = thin
            c.fill = amarelo_fill
        cell_s = ws.cell(row=row, column=19, value=f'=S{linha_13}/3')
        cell_s.number_format = MONEY_FMT
        cell_s.font = label_font
        cell_s.fill = amarelo_fill
        cell_s.border = thin
        cell_s.alignment = Alignment(horizontal='right', vertical='center')
        row += 1

    return row


def _emitir_total_bruto(ws, row, primeira_linha_dados, ultima_linha):
    amarelo_fill = PatternFill(start_color=AMARELO, end_color=AMARELO, fill_type="solid")
    total_font = Font(name=FONT_NAME, size=11, bold=True)

    ws.merge_cells(start_row=row, start_column=17, end_row=row, end_column=18)
    cell_lbl = ws.cell(row=row, column=17, value="TOTAL BRUTO:")
    cell_lbl.font = total_font
    cell_lbl.fill = amarelo_fill
    cell_lbl.alignment = Alignment(horizontal='right', vertical='center')
    cell_lbl.border = thin

    cell_total = ws.cell(
        row=row, column=19,
        value=f'=SUM(S{primeira_linha_dados}:S{ultima_linha})'
    )
    cell_total.number_format = MONEY_FMT
    cell_total.font = total_font
    cell_total.fill = amarelo_fill
    cell_total.border = thin
    cell_total.alignment = Alignment(horizontal='right', vertical='center')
