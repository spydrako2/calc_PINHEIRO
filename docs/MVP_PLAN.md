# HoleritePRO MVP — Plano de Implementação

**Data:** 2026-02-24
**Objetivo:** App funcional que lê holerites DDPE, aplica tese jurídica e gera XLSX auditável

---

## Escopo do MVP

### IN
- Parser DDPE (já funciona)
- Sistema de Teses (classes Python simples)
- Interface Streamlit com branding Pinheiro Advocacia
- Exportação XLSX com fórmulas auditáveis e rastreio de atrasados
- Nome do cliente visível em toda extração

### OUT (futuro)
- Parsers SPPREV (Aposentado/Pensionista)
- CPF no cabeçalho DDPE (formato real diferente do esperado)
- Pipeline automatizado (pipeline.py)
- Módulo de aprendizado de verbas (FR-20)

---

## Arquitetura

```
src/
├── core/                    # Já existe
│   ├── pdf_reader.py        # ✅ Lê PDFs
│   ├── parsers/
│   │   └── ddpe_parser.py   # ✅ Extrai verbas DDPE
│   ├── data_model.py        # ✅ Modelos de dados
│   └── normalizer.py        # ✅ Normalização
│
├── teses/                   # NOVO
│   ├── __init__.py
│   ├── base_tese.py         # Classe base abstrata
│   ├── tese_art133.py       # Art.133 CE-PRO LAB + Quinquênios
│   └── tese_piso_docente.py # Piso Sal.Docente + Quinquênios
│
├── export/                  # NOVO
│   ├── __init__.py
│   └── xlsx_writer.py       # Gerador XLSX auditável (unificado)
│
└── ui/                      # NOVO
    └── app.py               # Streamlit app
```

---

## Módulo de Teses

### BaseTese (classe abstrata)
```python
class BaseTese:
    nome: str                    # "Art. 133 CE-PRO LAB"
    descricao: str               # Descrição da tese
    verba_alvo: str              # Código da verba principal ("003007")
    verba_quinquenio: str        # "009001"

    def extrair(pdf_path) -> dict      # Extrai dados do PDF
    def calcular(dados) -> dict        # Aplica fórmula da tese
    def exportar(dados, output) -> str  # Gera XLSX
```

### Teses Iniciais
| Tese | Verba Alvo | Cálculo |
|------|-----------|---------|
| Art.133 CE-PRO LAB | 003007 | valor × (quinquênios × 5%) |
| Piso Sal.Docente Dec.62500 | 001035 | valor × (quinquênios × 5%) |

---

## Interface Streamlit

### Branding Pinheiro Advocacia
- **Azul Escuro** #1a365d — fundo sidebar, headers
- **Dourado** #C7A76D — botões CTA, acentos, progresso
- **Branco** #FFFFFF — texto, backgrounds
- **Vermelho** #E53E3E — erros
- **Verde** #38A169 — sucesso

### Fluxo (3 etapas simplificadas)
1. **Upload** — Arrasta PDF(s) + exibe nome do cliente extraído
2. **Tese** — Escolhe qual tese aplicar (dropdown)
3. **Resultado** — Preview dos dados + botão Download XLSX

---

## Regras de Negócio

1. **Pagamento real = competência + 1 mês** (sempre)
2. **Atrasados** são alocados ao período de referência (periodo_fim), não ao mês de pagamento
3. **Células com atrasados** → fórmula auditável (=normal+atraso1+atraso2) + comentário com detalhamento
4. **Células com atrasados** → destaque visual (fundo amarelo)
5. **Nome do cliente** extraído do PDF e exibido na UI e no XLSX
6. **Quinquênios** → extrair de código 009001 (campo QTDE ou parsear denominação)

---

## Tarefas de Implementação

### Etapa 1: Sistema de Teses (~2h)
- [ ] Criar `src/teses/base_tese.py` — classe base
- [ ] Criar `src/teses/tese_art133.py` — consolidar lógica do extract_reflexo.py
- [ ] Criar `src/teses/tese_piso_docente.py` — consolidar lógica do extract_piso_docente.py
- [ ] Criar `src/export/xlsx_writer.py` — writer unificado
- [ ] Corrigir comentário pagamento (comp+1)

### Etapa 2: Interface Streamlit (~2h)
- [ ] Criar `src/ui/app.py` com branding Pinheiro
- [ ] Upload de PDF com preview (nome do cliente)
- [ ] Seleção de tese
- [ ] Processamento e download XLSX
- [ ] Responsivo e profissional

### Etapa 3: Polimento (~1h)
- [ ] Testes das teses
- [ ] requirements.txt com streamlit + openpyxl
- [ ] README com instruções de uso
- [ ] Testar com todos os PDFs DDPE disponíveis
