"""
HoleritePRO — Interface Streamlit
Branding: Pinheiro Advocacia
"""

import tempfile
import streamlit as st
from pathlib import Path

from src.teses import TESES_DISPONIVEIS
from src.export.xlsx_writer import write_reflexo_xlsx
from src.export.iamspe_writer import write_iamspe_xlsx
from src.export.apeoesp_writer import write_apeoesp_xlsx
from src.teses.base_tese import BaseTese


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
            help="Aceita PDFs do Demonstrativo de Pagamento (DDPE) do Estado de SP",
        )

        if uploaded:
            # Save to temp file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(uploaded.read())
            tmp.close()
            st.session_state.pdf_path = tmp.name

            # Quick extraction of client name
            nome = BaseTese._extract_nome(
                _quick_read_first_page(tmp.name)
            )
            st.session_state.nome_cliente = nome

            st.markdown(f"""
            <div class="client-card">
                <h3>Cliente Identificado</h3>
                <p>📋 {nome}</p>
                <p>📄 {uploaded.name}</p>
            </div>
            """, unsafe_allow_html=True)

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
                    tese = TESES_DISPONIVEIS[tese_key]()
                    resultado = tese.processar(st.session_state.pdf_path)
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

        periodos = resultado['periodos']
        sorted_p = sorted(periodos.keys())
        n_meses = len(sorted_p)

        # ---- IAMSPE: layout de pivot ----
        if resultado.get('tese_tipo') == 'iamspe':
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
                            val = periodos[per].get(code, 0.0)
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
            write_reflexo_xlsx(resultado, tmp_xlsx.name)

        # ---- Download (comum para todas as teses) ----
        with open(tmp_xlsx.name, "rb") as f:
            xlsx_bytes = f.read()

        nome_safe = resultado['nome_cliente'].replace(' ', '_')[:30]
        tese_safe = st.session_state.tese_key
        filename = f"HoleritePRO_{nome_safe}_{tese_safe}.xlsx"

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


if __name__ == "__main__":
    main()
