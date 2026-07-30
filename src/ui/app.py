"""
HoleritePRO — Interface Streamlit
Branding: Pinheiro Advocacia
"""

import re
import sys
import tempfile
from pathlib import Path

# Garantir que a raiz do projeto está no sys.path (necessário no Streamlit Cloud)
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from src.teses import TESES_DISPONIVEIS
from src.teses.tese_ir_bonus import TeseIRBonus
from src.export.xlsx_writer import write_reflexo_xlsx
from src.export.piso_writer import write_piso_xlsx
from src.export.iamspe_writer import write_iamspe_xlsx
from src.export.apeoesp_writer import write_apeoesp_xlsx
from src.export.chs_writer import write_chs_xlsx
from src.export.ir_bonus_writer import write_ir_bonus_xlsx
from src.teses.base_tese import BaseTese
from src.version import VERSION, BUILD, CHANGELOG, CHANGELOG_VISIVEL


# --- Page config ---
st.set_page_config(
    page_title="HoleritePRO",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Custom CSS (Pinheiro Advocacia branding) ---
st.markdown("""
<style>
    /* Root variables */
    :root {
        --azul-escuro: #1a365d;
        --dourado: #C7A76D;
        --branco: #FFFFFF;
        --vermelho: #E53E3E;
        --verde: #38A169;
    }

    /* Header */
    .main-header {
        background-color: #1a365d;
        padding: 1.5rem 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .main-header h1 {
        color: #C7A76D !important;
        font-size: 2rem;
        margin: 0;
        font-weight: 700;
    }
    .main-header p {
        color: #FFFFFF;
        font-size: 0.9rem;
        margin: 0.3rem 0 0 0;
        opacity: 0.85;
    }

    /* Step indicator */
    .step-bar {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
    }
    .step {
        padding: 0.4rem 1.2rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .step-active {
        background-color: #C7A76D;
        color: #1a365d;
    }
    .step-inactive {
        background-color: #E2E8F0;
        color: #718096;
    }
    .step-done {
        background-color: #38A169;
        color: #FFFFFF;
    }

    /* Client card */
    .client-card {
        background: linear-gradient(135deg, #1a365d 0%, #2a4a7f 100%);
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #C7A76D;
    }
    .client-card h3 {
        color: #C7A76D !important;
        margin: 0 0 0.2rem 0;
        font-size: 1.1rem;
    }
    .client-card p {
        color: #FFFFFF;
        margin: 0;
        font-size: 0.85rem;
    }

    /* Result card */
    .result-card {
        background: #F7FAFC;
        border: 2px solid #C7A76D;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        text-align: center;
    }
    .result-card h2 {
        color: #1a365d !important;
        margin: 0;
    }
    .result-card .big-number {
        font-size: 2.2rem;
        font-weight: 700;
        color: #C7A76D;
    }

    /* Buttons */
    .stDownloadButton > button {
        background-color: #C7A76D !important;
        color: #1a365d !important;
        font-weight: 700 !important;
        border: none !important;
        padding: 0.7rem 2rem !important;
        font-size: 1rem !important;
    }
    .stDownloadButton > button:hover {
        background-color: #b8964f !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>⚖️ HoleritePRO</h1>
        <p>Pinheiro Advocacia — Extração e Cálculo de Teses</p>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"versão {VERSION} · build {BUILD}")

    with st.expander("🆕 Últimas atualizações"):
        for versao, data, mudancas in CHANGELOG[:CHANGELOG_VISIVEL]:
            st.markdown(f"**Versão {versao}** · {data}")
            for m in mudancas:
                st.markdown(f"- {m}")
            st.markdown("")


def render_steps(current: int):
    steps = ["Upload PDF", "Escolher Tese", "Resultado"]
    html = '<div class="step-bar">'
    for i, name in enumerate(steps):
        if i < current:
            cls = "step step-done"
            icon = "✓ "
        elif i == current:
            cls = "step step-active"
            icon = ""
        else:
            cls = "step step-inactive"
            icon = ""
        html += f'<span class="{cls}">{icon}{name}</span>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def main():
    render_header()

    # Initialize state
    if 'step' not in st.session_state:
        st.session_state.step = 0
    if 'resultado' not in st.session_state:
        st.session_state.resultado = None
    if 'pdf_path' not in st.session_state:
        st.session_state.pdf_path = None
    if 'nome_cliente' not in st.session_state:
        st.session_state.nome_cliente = None

    # Determine current step
    step = st.session_state.step
    render_steps(step)

    # ========== STEP 0: Upload ==========
    if step == 0:
        st.subheader("📄 Importar Holerites")
        st.markdown("Faça upload do PDF com os holerites do cliente (formato DDPE).")

        uploaded = st.file_uploader(
            "Arraste ou clique para selecionar",
            type=["pdf"],
            accept_multiple_files=True,
            help=(
                "Aceita um ou mais PDFs do Demonstrativo de Pagamento (DDPE). "
                "Para a tese de IR sobre Bônus, envie o holerite normal E o "
                "suplementar juntos — os dois entram na mesma planilha."
            ),
        )

        if uploaded:
            # Save all uploaded files to temp; pdf_path = primeiro (compat/diagnóstico)
            paths = []
            for uf in uploaded:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                tmp.write(uf.read())
                tmp.close()
                paths.append(tmp.name)
            st.session_state.pdf_paths = paths
            st.session_state.pdf_path = paths[0]

            diag = _diagnosticar_pdf(paths[0])

            if diag['erro_leitura']:
                st.error(
                    "❌ **Não consegui abrir este arquivo.** Verifique se é um PDF "
                    "válido (não protegido por senha) e tente novamente."
                )
            elif not diag['reconhecido']:
                st.error(
                    "❌ **PDF não reconhecido.** Não encontrei holerites no formato "
                    "esperado (folha de pagamento do Estado de SP ou da "
                    "aposentadoria). Confira se enviou o arquivo certo — o mesmo PDF "
                    "que costuma abrir os demonstrativos mês a mês."
                )
            else:
                nome = diag['nome']
                st.session_state.nome_cliente = nome

                if not nome or nome == "UNKNOWN":
                    st.warning(
                        "⚠️ **Não identifiquei o nome do cliente automaticamente.** "
                        "O cálculo funciona normalmente; se precisar, ajuste o nome "
                        "no arquivo Excel gerado no final."
                    )
                    nome_display = "(nome não identificado)"
                else:
                    nome_display = nome

                arquivos = ", ".join(uf.name for uf in uploaded)
                st.markdown(f"""
                <div class="client-card">
                    <h3>Cliente Identificado</h3>
                    <p>📋 {nome_display}</p>
                    <p>📄 {len(uploaded)} arquivo(s): {arquivos}</p>
                    <p>🗓️ {diag['n_holerites']} holerites lidos (1º arquivo)</p>
                </div>
                """, unsafe_allow_html=True)

                if diag.get('ilegivel'):
                    st.error(
                        "❌ **A qualidade deste PDF está baixa demais para o "
                        "cálculo.** Os holerites foram reconhecidos, mas o texto "
                        "está tão degradado que quase nenhuma verba pôde ser lida "
                        f"(apenas {diag['verbas_por_pagina']:.1f} verbas por "
                        "holerite; o normal é 8 a 15).\n\n"
                        "Isso costuma acontecer com PDF **comprimido** ou "
                        "escaneado em baixa resolução. **Envie o arquivo "
                        "original**, sem compressão — as teses não vão encontrar "
                        "valores neste aqui."
                    )

                comps_ocr = diag.get('comps_ocr') or []
                if comps_ocr:
                    lista = ", ".join(comps_ocr[:8])
                    if len(comps_ocr) > 8:
                        lista += f" … (+{len(comps_ocr) - 8})"
                    st.warning(
                        f"⚠️ **{len(comps_ocr)} holerite(s) estão escaneados (imagem) "
                        f"e foram lidos por OCR:** {lista}.\n\n"
                        "O OCR erra dígitos com frequência. **Confira os valores "
                        "desses meses na planilha** contra o holerite original antes "
                        "de usar o cálculo."
                    )

                if st.button("Avançar →", type="primary"):
                    st.session_state.step = 1
                    st.rerun()

    # ========== STEP 1: Choose Tese ==========
    elif step == 1:
        st.subheader("📐 Escolher Tese Jurídica")

        st.markdown(f"""
        <div class="client-card">
            <h3>Cliente</h3>
            <p>📋 {st.session_state.nome_cliente}</p>
        </div>
        """, unsafe_allow_html=True)

        tese_options = {
            key: cls.nome + " — " + cls.descricao
            for key, cls in TESES_DISPONIVEIS.items()
        }

        tese_key = st.selectbox(
            "Selecione a tese:",
            options=list(tese_options.keys()),
            format_func=lambda k: TESES_DISPONIVEIS[k].nome,
        )

        if tese_key:
            tese_cls = TESES_DISPONIVEIS[tese_key]
            st.info(f"**{tese_cls.nome}:** {tese_cls.descricao}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Voltar"):
                st.session_state.step = 0
                st.rerun()
        with col2:
            if st.button("Processar →", type="primary"):
                with st.spinner("Processando holerites..."):
                    try:
                        tese = TESES_DISPONIVEIS[tese_key]()
                        # IR Bônus junta todos os PDFs (normal + suplementar);
                        # as demais teses usam o primeiro arquivo.
                        if tese_key == 'ir_bonus':
                            entrada = st.session_state.get('pdf_paths', [st.session_state.pdf_path])
                        else:
                            entrada = st.session_state.pdf_path
                        resultado = tese.processar(entrada)
                    except Exception as e:
                        st.error(
                            "❌ **Não foi possível concluir o cálculo desta tese.** "
                            "Tente novamente ou escolha outra tese. Se o erro "
                            "persistir, encaminhe o PDF para o suporte."
                        )
                        with st.expander("Detalhe técnico (para o suporte)"):
                            st.code(f"{type(e).__name__}: {e}")
                        st.stop()

                if not _tem_resultado_util(resultado):
                    st.warning(
                        "⚠️ **Nenhuma verba desta tese foi encontrada nos "
                        "holerites.** Verifique se escolheu a tese correta para "
                        "este cliente — os holerites enviados não contêm as verbas "
                        "que esta tese calcula."
                    )
                else:
                    st.session_state.resultado = resultado
                    st.session_state.tese_key = tese_key
                    st.session_state.step = 2
                    st.rerun()

    # ========== STEP 2: Result ==========
    elif step == 2:
        resultado = st.session_state.resultado
        st.subheader("📊 Resultado")

        st.markdown(f"""
        <div class="client-card">
            <h3>{resultado['nome_cliente']}</h3>
            <p>Tese: {resultado['tese_nome']}</p>
        </div>
        """, unsafe_allow_html=True)

        periodos = resultado.get('periodos', {})
        sorted_p = sorted(periodos.keys())
        n_meses = len(sorted_p)

        # ---- IR sobre Bônus: bloco RRA (BR) + bloco(s) de isenção (FUNDEB/DEJEC) ----
        if resultado.get('tese_tipo') == 'ir_bonus':
            parcelas_rra = resultado.get('rra', [])
            isencao = resultado.get('isencao', {})
            total_recuperar = resultado.get('total_recuperar', 0.0)
            n_parcelas = len(parcelas_rra) + sum(len(ps) for ps in isencao.values())
            isencao_nomes = {'FUNDEB': 'Abono FUNDEB', 'DEJEC': 'DEJEC'}

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Parcelas de Bônus", n_parcelas)
            with col2:
                st.metric("Bloco RRA (BR)", len(parcelas_rra))
            with col3:
                st.metric("Total a Recuperar", f"R$ {total_recuperar:,.2f}")

            if n_parcelas == 0:
                st.warning(
                    "Nenhuma parcela de bônus (Bonificação por Resultados, Abono "
                    "FUNDEB ou DEJEC) foi encontrada. Verifique se enviou o holerite "
                    "**suplementar** com os pagamentos retroativos."
                )
            else:
                st.caption(
                    "A planilha traz a **Bonificação por Resultados** no cálculo RRA "
                    "(imposto diluído nos meses) e o **Abono FUNDEB / DEJEC** como "
                    "isenção (restituição integral), no mesmo modelo do escritório. "
                    "O nº de dependentes é lido do holerite (ajustável na coluna H)."
                )

            if parcelas_rra:
                subtotal = sum(TeseIRBonus.diferenca_rra(p) for p in parcelas_rra)
                with st.expander(
                    f"📋 Bonificação por Resultados (RRA) — {len(parcelas_rra)} "
                    f"parcelas (R$ {subtotal:,.2f})",
                    expanded=True,
                ):
                    preview = []
                    for p in parcelas_rra:
                        meses = TeseIRBonus.meses_periodo(p['inicio'], p['fim'])
                        preview.append({
                            "Referência": f"{p['inicio'].strftime('%m/%Y')}–{p['fim'].strftime('%m/%Y')}",
                            "Meses": meses,
                            "Pagamento": p['pagamento'].strftime('%d/%m/%Y') if p['pagamento'] else "-",
                            "Bônus": f"R$ {p['bonus']:,.2f}",
                            "Dep.": p['dependentes'],
                            "IR Pago": f"R$ {p['ir_pago']:,.2f}",
                            "A Recuperar": f"R$ {TeseIRBonus.diferenca_rra(p):,.2f}",
                        })
                    st.dataframe(preview, use_container_width=True, hide_index=True)

            for tipo, parcelas in isencao.items():
                subtotal = sum(p['ir_pago'] for p in parcelas)
                with st.expander(
                    f"📋 {isencao_nomes.get(tipo, tipo)} — isenção, "
                    f"{len(parcelas)} parcelas (R$ {subtotal:,.2f} — restituição total)",
                    expanded=True,
                ):
                    preview = []
                    for p in parcelas:
                        preview.append({
                            "Referência": f"{p['inicio'].strftime('%m/%Y')}–{p['fim'].strftime('%m/%Y')}",
                            "Pagamento": p['pagamento'].strftime('%d/%m/%Y') if p['pagamento'] else "-",
                            "Valor Pago": f"R$ {p['bonus']:,.2f}",
                            "IR Pago": f"R$ {p['ir_pago']:,.2f}",
                            "A Recuperar": f"R$ {p['ir_pago']:,.2f}",
                        })
                    st.dataframe(preview, use_container_width=True, hide_index=True)

            tmp_xlsx = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            tmp_xlsx.close()
            write_ir_bonus_xlsx(resultado, tmp_xlsx.name)

        # ---- IAMSPE: layout de pivot ----
        elif resultado.get('tese_tipo') == 'iamspe':
            rubricas = resultado['rubricas']
            total_geral = resultado['total_geral']
            total_por_rubrica = resultado['total_por_rubrica']

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Meses Extraídos", n_meses)
            with col2:
                st.metric("Total a Cobrar", f"R$ {total_geral:,.2f}")

            if sorted_p:
                first = BaseTese.format_comp_display(sorted_p[0])
                last = BaseTese.format_comp_display(sorted_p[-1])
                st.caption(f"Período: {first} a {last}")

            with st.expander("📋 Preview da planilha", expanded=True):
                if rubricas:
                    preview_data = []
                    for per in sorted_p:
                        row = {"Competência": BaseTese.format_comp_display(per)}
                        linha_total = 0.0
                        for code, label in rubricas.items():
                            cell_data = periodos[per].get(code, {'normal': 0.0, 'atrasados': []})
                            val = cell_data['normal'] + sum(v for _, v in cell_data['atrasados'])
                            row[label] = f"R$ {val:,.2f}" if val else "-"
                            linha_total += val
                        row["VALOR DEVIDO"] = f"R$ {linha_total:,.2f}"
                        preview_data.append(row)
                    st.dataframe(preview_data, use_container_width=True, hide_index=True)
                else:
                    st.warning("Nenhuma rubrica IAMSPE encontrada no PDF.")

            # Totais por rubrica
            if total_por_rubrica:
                with st.expander("📊 Totais por rubrica"):
                    for code, label in rubricas.items():
                        val = total_por_rubrica.get(code, 0.0)
                        if val:
                            st.write(f"**{label}:** R$ {val:,.2f}")

            # Gerar XLSX
            tmp_xlsx = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            tmp_xlsx.close()
            write_iamspe_xlsx(resultado, tmp_xlsx.name)

        # ---- CHS: Carga Horária Suplementar sobre Piso Docente ----
        elif resultado.get('tese_tipo') == 'chs':
            vinculo = resultado.get('vinculo', 'efetivo')
            situacao = resultado.get('situacao', 'ativo')
            vinculo_label = {'efetivo': 'Efetivo', 'lei500': 'Lei 500/74'}.get(vinculo, vinculo)
            situacao_label = {'ativo': 'ATIVO', 'inativo': 'INATIVO'}.get(situacao, situacao)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Meses Extraídos", n_meses)
            with col2:
                st.metric("Vínculo", vinculo_label)
            with col3:
                st.metric("Situação Atual", situacao_label)

            if sorted_p:
                first = BaseTese.format_comp_display(sorted_p[0])
                last = BaseTese.format_comp_display(sorted_p[-1])
                st.caption(
                    f"Período: {first} a {last} — planilha será preenchida na aba "
                    f"**Cálculo {situacao_label}**"
                )

            # A jornada (coluna D) é a base do cálculo: as fórmulas de CHS
            # Recebida/Devida são =IF(D=0;0;...). Sem ela a planilha inteira sai
            # zerada. O holerite de aposentado (SPPREV) não traz a jornada, então
            # isso é comum — mas precisa ficar visível ANTES do download.
            sem_jornada = [p for p in sorted_p if not periodos[p]['jornada_horas']]
            if sem_jornada:
                meses_txt = ", ".join(
                    BaseTese.format_comp_display(p) for p in sem_jornada[:6]
                )
                if len(sem_jornada) > 6:
                    meses_txt += f" … (+{len(sem_jornada) - 6})"
                if len(sem_jornada) == len(sorted_p):
                    st.error(
                        "⚠️ **A jornada não foi encontrada em NENHUM mês — a "
                        "planilha vai sair com TOTAL BRUTO R$ 0,00.**\n\n"
                        "O holerite de aposentado (SPPREV) não informa a jornada, "
                        "que é a base do cálculo. Preencha a **coluna D (Jornada)** "
                        "na planilha — as células estão marcadas em laranja — e os "
                        "valores serão calculados automaticamente."
                    )
                else:
                    st.warning(
                        f"⚠️ **{len(sem_jornada)} de {len(sorted_p)} meses estão sem "
                        f"jornada** e ficarão zerados na planilha (células laranja na "
                        f"coluna D): {meses_txt}.\n\n"
                        "Preencha a jornada desses meses para que entrem no total."
                    )

            with st.expander("📋 Preview dos dados", expanded=False):
                preview_data = []
                for per in sorted_p:
                    d = periodos[per]
                    salario_base = d['salario_base_normal'] + sum(v for _, v in d['salario_base_atrasados'])
                    piso = d['piso_normal'] + sum(v for _, v in d['piso_atrasados'])
                    preview_data.append({
                        "Competência": BaseTese.format_comp_display(per),
                        "Salário Base": f"R$ {salario_base:,.2f}" if salario_base else "-",
                        "Piso": f"R$ {piso:,.2f}" if piso else "-",
                        "Jornada (h)": d['jornada_horas'] if d['jornada_horas'] else "-",
                        "Horas Supl.": d['horas_suplementares'] if d['horas_suplementares'] else "-",
                        "Quinq.": d['quinquenios'],
                        "6ª Parte": "Sim" if d['tem_sexta_parte'] else "Não",
                    })
                st.dataframe(preview_data, use_container_width=True, hide_index=True)

            tmp_xlsx = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            tmp_xlsx.close()
            write_chs_xlsx(resultado, tmp_xlsx.name)

        # ---- APEOESP: quinquênio + sexta parte sobre gratificações ----
        elif resultado.get('tese_tipo') == 'apeoesp':
            total_geral = resultado['total_geral']
            n_sexta = sum(1 for d in periodos.values() if d.get('tem_sexta_parte'))

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Meses Extraídos", n_meses)
            with col2:
                st.metric("Meses c/ Sexta Parte", n_sexta)
            with col3:
                st.metric("Total a Receber", f"R$ {total_geral:,.2f}")

            if sorted_p:
                first = BaseTese.format_comp_display(sorted_p[0])
                last = BaseTese.format_comp_display(sorted_p[-1])
                st.caption(f"Período: {first} a {last}")

            with st.expander("📋 Preview dos dados", expanded=False):
                preview_data = []
                for per in sorted_p:
                    d = periodos[per]
                    preview_data.append({
                        "Competência": BaseTese.format_comp_display(per),
                        "Gratif.Geral": f"R$ {d['gratif_geral']:,.2f}" if d['gratif_geral'] else "-",
                        "GTE": f"R$ {d['gte']:,.2f}" if d['gte'] else "-",
                        "GAM": f"R$ {d['gam']:,.2f}" if d['gam'] else "-",
                        "Total Vant.": f"R$ {d['total_vantagens']:,.2f}",
                        "Quinq.": d['quinquenios'],
                        "6ª Parte": "Sim" if d['tem_sexta_parte'] else "Não",
                        "Total Devido": f"R$ {d['total_devido']:,.2f}",
                    })
                st.dataframe(preview_data, use_container_width=True, hide_index=True)

            tmp_xlsx = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            tmp_xlsx.close()
            write_apeoesp_xlsx(resultado, tmp_xlsx.name)

        # ---- Teses de reflexo simples (Art133, PisoDocente, etc.) ----
        else:
            n_atrasados = sum(1 for p in periodos.values() if p['atrasados'])

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Meses Extraídos", n_meses)
            with col2:
                st.metric("Total Verba", f"R$ {resultado['total_verba']:,.2f}")
            with col3:
                st.metric("Total Reflexo", f"R$ {resultado['total_reflexo']:,.2f}")

            if n_atrasados:
                st.caption(f"⚠️ {n_atrasados} meses contêm valores de atraso consolidados (destacados em amarelo no Excel)")

            if sorted_p:
                first = BaseTese.format_comp_display(sorted_p[0])
                last = BaseTese.format_comp_display(sorted_p[-1])
                st.caption(f"Período: {first} a {last}")

            if resultado.get('tese_tipo') == 'piso':
                sits = set(resultado.get('situacao_por_periodo', {}).values())
                if sits == {'ativo'}:
                    situ_txt = "ativo (13º + 1/3 de férias por ano)"
                elif sits == {'inativo'}:
                    situ_txt = "inativo (apenas 13º por ano)"
                else:
                    situ_txt = "ativo e inativo — cada ano recebe 13º; anos ativos também 1/3 de férias"
                st.caption(
                    f"🗓️ Situação: {situ_txt}. O **TOTAL BRUTO** da planilha "
                    f"inclui os reflexos de 13º e férias, além do valor mensal."
                )
                st.caption(
                    "🔒 Planilha protegida: editáveis apenas as colunas Piso, "
                    "Qtde Quinquênios e Tem 6ª Parte."
                )

            with st.expander("📋 Preview dos dados", expanded=False):
                preview_data = []
                for per in sorted_p:
                    d = periodos[per]
                    total = d['normal'] + sum(v for _, v in d['atrasados'])
                    atr = f"({len(d['atrasados'])})" if d['atrasados'] else ""
                    preview_data.append({
                        "Competência": BaseTese.format_comp_display(per),
                        "Valor": f"R$ {total:,.2f}",
                        "Atrasos": atr,
                        "Quinq.": d['quinquenios'],
                        "%": f"{d['quinquenios'] * 5}%",
                        "Reflexo": f"R$ {d['reflexo']:,.2f}",
                    })
                st.dataframe(preview_data, use_container_width=True, hide_index=True)

            tmp_xlsx = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            tmp_xlsx.close()
            if resultado.get('tese_tipo') == 'piso':
                write_piso_xlsx(resultado, tmp_xlsx.name)
            else:
                write_reflexo_xlsx(resultado, tmp_xlsx.name)

        # ---- Download (comum para todas as teses) ----
        with open(tmp_xlsx.name, "rb") as f:
            xlsx_bytes = f.read()

        # Padrão Pinheiro uniforme (OBRIGATÓRIO para toda tese, atual ou futura):
        #   "02. PLANILHA DE CÁLCULOS_{NOME DA TESE}_{NOME DO CLIENTE}"
        # Teses novas seguem o padrão automaticamente via fallback (usa o .nome da
        # classe da tese). Só adicione uma entrada no mapa abaixo se quiser um rótulo
        # de arquivo diferente do .nome da classe.
        NOMES_TESE_ARQUIVO = {
            'piso': 'PISO DOCENTE',
            'iamspe': 'ACÚMULO IAMSPE',
            'apeoesp': 'APEOESP',
            'chs': 'CHS',
            'ir_bonus': 'IR SOBRE BÔNUS RRA',
        }
        tipo = resultado.get('tese_tipo', '')
        nome_tese = NOMES_TESE_ARQUIVO.get(tipo)
        if not nome_tese:
            # Fallback: nome da classe da tese ativa
            tese_cls = TESES_DISPONIVEIS.get(st.session_state.get('tese_key'))
            nome_tese = tese_cls.nome.upper() if tese_cls else str(tipo).upper()
        if tipo == 'chs':
            # CHS mantém ATIVO/INATIVO como parte do nome da tese
            situacao_nome = {'ativo': 'ATIVO', 'inativo': 'INATIVO'}.get(
                resultado.get('situacao', 'ativo'), 'ATIVO'
            )
            nome_tese = f"CHS - {situacao_nome}"
        nome_cliente = re.sub(r'[\\/:*?"<>|]', '', resultado['nome_cliente']).strip()
        filename = f"02. PLANILHA DE CÁLCULOS_{nome_tese}_{nome_cliente}.xlsx"

        st.download_button(
            label="⬇️ Download XLSX",
            data=xlsx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.markdown("---")
        if st.button("← Novo Processamento"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def _quick_read_first_page(pdf_path: str) -> str:
    """Read just the first page text for client name extraction."""
    from src.core.pdf_reader import PDFReader
    pages = PDFReader.read_pdf(pdf_path)
    if pages:
        return pages[0].texto
    return ""


def _diagnosticar_pdf(pdf_path: str) -> dict:
    """
    Valida o PDF antes de prosseguir, para gerar mensagens amigáveis.

    Retorna: {erro_leitura, reconhecido, nome, n_holerites}.
    - erro_leitura: o arquivo não pôde ser aberto (corrompido, protegido).
    - reconhecido: há ao menos uma página no formato de holerite conhecido.
    - nome: nome do cliente extraído (ou "UNKNOWN").
    - n_holerites: quantas páginas de holerite válido foram encontradas.
    """
    from src.core.pdf_reader import PDFReader
    from src.core.parsers.ddpe_parser import DDPEParser
    from src.core.parsers.spprev_aposentado_parser import SpprevAposentadoParser

    try:
        pages = PDFReader.read_pdf(pdf_path)
    except Exception:
        return {'erro_leitura': True, 'reconhecido': False,
                'nome': 'UNKNOWN', 'n_holerites': 0}

    ddpe = DDPEParser()
    spprev = SpprevAposentadoParser()
    validas = [
        p for p in pages
        if ddpe.detect_template(p.texto) or spprev.detect_template(p.texto)
    ]

    nome = "UNKNOWN"
    for p in validas:
        nome = BaseTese._extract_nome(p.texto)
        if nome and nome != "UNKNOWN":
            break

    # Páginas escaneadas passam por OCR, que erra dígitos (já vimos "571,74"
    # virar "71,74"). Os valores dessas competências precisam ser conferidos
    # à mão contra o holerite original.
    comps_ocr = []
    for p in validas:
        if p.metodo != "OCR":
            continue
        comp = BaseTese._extract_competencia(p.texto)
        comps_ocr.append(BaseTese.format_comp_display(comp) if comp else f"pág. {p.numero}")

    # Um holerite legível rende ~8-15 verbas por página. Quando o OCR degrada a
    # coluna de código (ex.: "001001" vira "DO100"), a página continua sendo
    # reconhecida como holerite mas quase nada é extraído — e TODAS as teses
    # dizem "nenhuma verba encontrada", fazendo o estagiário culpar a tese.
    # Medir verbas/página distingue "tese errada" de "PDF ilegível".
    verbas_por_pagina = 0.0
    if validas:
        amostra = validas[:20]
        total_verbas = 0
        for p in amostra:
            parser = ddpe if ddpe.detect_template(p.texto) else spprev
            pi = type(parser)()
            pi.paginas = [p]
            try:
                total_verbas += len(pi._extract_verbas())
            except Exception:
                pass
        verbas_por_pagina = total_verbas / len(amostra)

    return {
        'erro_leitura': False,
        'reconhecido': len(validas) > 0,
        'nome': nome,
        'n_holerites': len(validas),
        'comps_ocr': comps_ocr,
        'verbas_por_pagina': verbas_por_pagina,
        'ilegivel': bool(validas) and verbas_por_pagina < 3,
    }


def _tem_resultado_util(resultado: dict) -> bool:
    """
    True se o cálculo encontrou verbas da tese. Usado para avisar quando a
    tese escolhida não bate com o conteúdo dos holerites.
    """
    if not resultado:
        return False
    periodos = resultado.get('periodos') or {}
    if not periodos:
        # IAMSPE usa 'rubricas' em vez de valores nos períodos
        if resultado.get('tese_tipo') == 'iamspe':
            return bool(resultado.get('rubricas'))
        return False

    tipo = resultado.get('tese_tipo')
    if tipo == 'iamspe':
        return bool(resultado.get('rubricas'))
    if tipo == 'apeoesp':
        return (resultado.get('total_geral') or 0) > 0
    if tipo == 'chs':
        # Há período com alguma CHS efetivamente lida
        return any(d.get('chs_por_codigo') for d in periodos.values())
    # Teses de reflexo simples
    return (resultado.get('total_verba') or 0) > 0


if __name__ == "__main__":
    main()
