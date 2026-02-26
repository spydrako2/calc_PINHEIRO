# Workflow Completo: HoleritePRO — Do Zero ao Produto Final

**Data:** 2026-02-24
**Autor:** Orion (aios-master) — Modelo Opus
**Objetivo:** Documentar o fluxo completo de desenvolvimento, ANTES e DEPOIS das melhorias

---

## Visão Geral do Projeto

```
Epic 1: Core Engine (Extração de PDFs + Modelo de Dados)
  └── Stories 1.1 → 1.6

Epic 2: Sistema de Teses + Exportação XLSX
  └── Stories 2.1 → 2.7

Epic 3: Interface Desktop + Empacotamento (.exe)
  └── Stories 3.1 → 3.6

TOTAL: 3 Epics, ~19 Stories
```

---

## PARTE 1: FLUXO ANTES (Como era feito)

### Fase 0: Planejamento Inicial (feita uma vez)

```
Usuário escreve briefing do projeto
        ↓
@pm (Morgan) → Cria PRD (docs/prd/prd.md)
        ↓
@architect (Aria) → Cria Arquitetura (docs/architecture.md)
        ↓
@po (Pax) → Valida documentos (checklist de alinhamento)
        ↓
Documentos prontos → Shard para docs/prd/ e docs/architecture/
```

### Fase 1: Ciclo por Story (repetido N vezes)

```
┌─────────────────────────────────────────────────────┐
│  CICLO ANTIGO (sem melhorias)                       │
│                                                     │
│  @sm (River) → Cria story draft                     │
│       ↓                                             │
│  @po (Pax) → Valida story (10 pontos)               │
│       ↓ GO                                          │
│  @dev (Dex) → Implementa TUDO de uma vez            │
│       ↓ (roda testes só no final)                   │
│  @qa (Quinn) → QA Gate (7 checks)                   │
│       ↓                                             │
│  PASS? → @devops push                               │
│  FAIL? → Volta para @dev (fix cycle)                │
│       ↓                                             │
│  @dev fix → @qa re-review → Loop até PASS           │
│       ↓                                             │
│  Próxima story...                                   │
└─────────────────────────────────────────────────────┘
```

### Problemas Desse Fluxo

| Problema | Consequência |
|----------|-------------|
| Sem revisão arquitetural antes do dev | Bugs de design vão para o código |
| Dev implementa tudo e testa no final | Bugs acumulam e cascateiam |
| Modelo único (Haiku) para tudo | Tarefas complexas ficam mal feitas |
| Múltiplas stories por sessão | Contexto poluído, pressa |
| QA pega bugs DEPOIS (reativo) | Retrabalho de 3-5 horas |

---

## PARTE 2: FLUXO DEPOIS (Com Melhorias 1, 3 e Model Selection)

### Fase 0: Planejamento Inicial (igual, mas com modelo certo)

```
Usuário escreve briefing do projeto
        ↓
┌──────────────────────────────────────────────┐
│ @pm (Morgan) — MODELO: OPUS                 │
│ Cria PRD completo                            │
│ Output: docs/prd/prd.md                      │
│                                              │
│ Por que Opus? PRD define TODO o projeto.     │
│ Um PRD mal feito = retrabalho em cascata.    │
│ Opus antecipa requisitos que você não pensou.│
└──────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│ @architect (Aria) — MODELO: OPUS             │
│ Cria Arquitetura + Decisões Técnicas         │
│ Output: docs/architecture.md                 │
│                                              │
│ Por que Opus? Decisões arquiteturais erradas │
│ custam semanas para corrigir depois.         │
└──────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│ @po (Pax) — MODELO: OPUS                    │
│ Valida alinhamento PRD ↔ Arquitetura         │
│ Garante que nada foi esquecido               │
│                                              │
│ Por que Opus? Validação estratégica exige    │
│ visão ampla e capacidade de comparação.      │
└──────────────────────────────────────────────┘
        ↓
Shard documentos → docs/prd/ e docs/architecture/
```

### Fase 1: Ciclo por Story (NOVO — com melhorias)

```
┌─────────────────────────────────────────────────────────────────┐
│  CICLO NOVO (com Architect Gate + Progressive Validation)       │
│                                                                 │
│  ┌───────────────────────────────────────┐                      │
│  │ ETAPA 1: CRIAR STORY                  │                      │
│  │ @sm (River) — MODELO: OPUS            │                      │
│  │ • Lê PRD sharded + epic context       │                      │
│  │ • Cria story com ACs claros           │                      │
│  │ • Output: docs/stories/X.Y.story.md   │                      │
│  │                                       │                      │
│  │ Por que Opus? Story bem escrita =      │                      │
│  │ zero ambiguidade para o dev.           │                      │
│  │ Story mal escrita = dev inventa.       │                      │
│  └───────────────┬───────────────────────┘                      │
│                  ↓                                              │
│  ┌───────────────────────────────────────┐                      │
│  │ ETAPA 2: VALIDAR STORY                │                      │
│  │ @po (Pax) — MODELO: OPUS             │                      │
│  │ • Checklist 10 pontos                 │                      │
│  │ • Verifica ACs testáveis              │                      │
│  │ • GO (≥7/10) ou NO-GO                 │                      │
│  │ • Se GO → Status: Ready               │                      │
│  │                                       │                      │
│  │ Por que Opus? PO precisa visão        │                      │
│  │ estratégica para validar se a story   │                      │
│  │ realmente resolve o problema.         │                      │
│  └───────────────┬───────────────────────┘                      │
│                  ↓                                              │
│  ┌───────────────────────────────────────┐                      │
│  │ ★ ETAPA 2.5: ARCHITECT GATE (NOVO!)  │                      │
│  │ @architect (Aria) — MODELO: OPUS      │                      │
│  │                                       │                      │
│  │ SÓ para stories com complexity HIGH+  │                      │
│  │                                       │                      │
│  │ • Revisa abordagem técnica (15-30min) │                      │
│  │ • Identifica edge cases antecipados   │                      │
│  │ • Define padrões a seguir             │                      │
│  │ • Lista armadilhas a evitar           │                      │
│  │ • Output: design-brief anexo à story  │                      │
│  │                                       │                      │
│  │ EXEMPLO (Story 1.5):                  │                      │
│  │ "SPPREV Pensionista e Aposentado      │                      │
│  │  compartilham keywords SPPREV e       │                      │
│  │  DEMONSTRATIVO. A detecção DEVE       │                      │
│  │  exigir PENSÃO como keyword           │                      │
│  │  obrigatória para diferenciar."       │                      │
│  │                                       │                      │
│  │ → Esse parágrafo teria evitado        │                      │
│  │   o bug arquitetural da Story 1.5.    │                      │
│  └───────────────┬───────────────────────┘                      │
│                  ↓                                              │
│  ┌───────────────────────────────────────┐                      │
│  │ ETAPA 3: IMPLEMENTAR                  │                      │
│  │ @dev (Dex) — MODELO: HAIKU            │                      │
│  │                                       │                      │
│  │ ★ PROGRESSIVE VALIDATION (NOVO!)      │                      │
│  │                                       │                      │
│  │ Task 1 → código → testes → PASS? ──┐  │                      │
│  │ Task 2 → código → testes → PASS? ──┤  │                      │
│  │ Task 3 → código → testes → PASS? ──┤  │                      │
│  │ Task 4 → código → testes → PASS? ──┤  │                      │
│  │ Task 5 → código → testes → PASS? ──┤  │                      │
│  │                                  ALL PASS                    │
│  │                                    ↓  │                      │
│  │ Status: InProgress → InReview         │                      │
│  │                                       │                      │
│  │ Se FAIL em qualquer task:             │                      │
│  │ → Fix ANTES de avançar para próxima   │                      │
│  │ → Nunca acumular bugs para o final    │                      │
│  │                                       │                      │
│  │ Por que Haiku? Com design-brief do    │                      │
│  │ architect + fixtures reais + validação │                      │
│  │ por task, o código é mecânico.        │                      │
│  └───────────────┬───────────────────────┘                      │
│                  ↓                                              │
│  ┌───────────────────────────────────────┐                      │
│  │ ETAPA 4: QA GATE                      │                      │
│  │ @qa (Quinn) — MODELO: SONNET          │                      │
│  │                                       │                      │
│  │ 7 checks:                             │                      │
│  │ 1. Code review                        │                      │
│  │ 2. Unit tests (todos passando)        │                      │
│  │ 3. Acceptance criteria                │                      │
│  │ 4. No regressions                     │                      │
│  │ 5. Performance                        │                      │
│  │ 6. Security                           │                      │
│  │ 7. Documentation                      │                      │
│  │                                       │                      │
│  │ Verdict: PASS / CONCERNS / FAIL       │                      │
│  │                                       │                      │
│  │ Por que Sonnet? Code review precisa   │                      │
│  │ de análise detalhada mas não de       │                      │
│  │ raciocínio estratégico profundo.      │                      │
│  └───────────────┬───────────────────────┘                      │
│                  ↓                                              │
│         PASS?────────────FAIL?                                  │
│           ↓                 ↓                                   │
│  ┌────────────────┐  ┌────────────────────┐                     │
│  │ @devops (Gage) │  │ QA LOOP            │                     │
│  │ MODELO: HAIKU  │  │ @dev fix (HAIKU)   │                     │
│  │                │  │     ↓              │                     │
│  │ • git push     │  │ @qa re-review      │                     │
│  │ • PR create    │  │   (SONNET)         │                     │
│  │ • Status: Done │  │     ↓              │                     │
│  │                │  │ Loop max 5x        │                     │
│  └────────────────┘  └────────────────────┘                     │
│                                                                 │
│  ════════════════════════════════════════════                    │
│  PRÓXIMA STORY → Volta para Etapa 1                             │
│  ════════════════════════════════════════════                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## PARTE 3: FLUXO COMPLETO DO HOLERITEPRO (19 Stories)

### Epic 1: Core Engine (Você está AQUI)

```
Story 1.1 ✅ Setup + Data Model ─────────────────── DONE
Story 1.2 ✅ PDF Reader + OCR Híbrido ────────────── DONE
Story 1.3 ✅ Parser DDPE ─────────────────────────── DONE
Story 1.4 🚫 Parser SPPREV Aposentados ────────────── BLOCKED (bugs)
Story 1.5 🚫 Parser SPPREV Pensionistas ───────────── BLOCKED (bugs)
Story 1.6 ⏳ Pipeline Lote (orquestração) ─────────── WAITING (depende 1.4+1.5)
```

**Fluxo para completar Epic 1:**

```
SESSÃO A (Opus → Haiku → Sonnet):
  @architect (Opus) → Design-brief para fixes 1.4 & 1.5
  @dev (Haiku) → Fix Story 1.4 (progressive validation)
  @qa (Sonnet) → Re-review 1.4
  → PASS? → Continue

SESSÃO B:
  @dev (Haiku) → Fix Story 1.5 (progressive validation)
  @qa (Sonnet) → Re-review 1.5
  → PASS? → Continue

SESSÃO C:
  @sm (Opus) → Criar Story 1.6
  @po (Opus) → Validar Story 1.6
  @architect (Opus) → Architect Gate (complexity=HIGH)
  @dev (Haiku) → Implementar Story 1.6
  @qa (Sonnet) → QA Gate
  → PASS? → Epic 1 DONE ✅
```

### Epic 2: Teses + XLSX (Próxima fase)

```
Story 2.1: Sistema de Módulos de Teses (plugin architecture)
  Complexity: VERY HIGH → Architect Gate obrigatório
  Modelo: Opus (architect) → Haiku (dev) → Sonnet (QA)

Story 2.2: Módulo IAMSPE
  Complexity: HIGH → Architect Gate obrigatório
  Requer: fixtures reais de cálculos IAMSPE

Story 2.3: Módulo Diferença de Classe
  Complexity: HIGH → Architect Gate

Story 2.4: Módulo Quinquênio
  Complexity: MEDIUM → Sem Architect Gate

Story 2.5: Exportador XLSX com Fórmulas
  Complexity: HIGH → Architect Gate
  CRÍTICO: Fórmulas decompostas (FR-13a do PRD)

Story 2.6: Registro de Aprendizado de Verbas
  Complexity: MEDIUM → Sem Architect Gate

Story 2.7: Normalização e Aliases de Verbas
  Complexity: MEDIUM → Sem Architect Gate
```

**Fluxo do Epic 2:**

```
Para CADA story (2.1 → 2.7):

  ┌─────── NOVA SESSÃO / CONTEXTO LIMPO ───────┐
  │                                              │
  │  @sm (Opus) → Cria story                     │
  │  @po (Opus) → Valida story                   │
  │  @architect (Opus) → Gate (se HIGH+)          │
  │  @dev (Haiku) → Implementa (progressivo)     │
  │  @qa (Sonnet) → QA Gate                      │
  │  @devops (Haiku) → Push se PASS              │
  │                                              │
  └──────────────────────────────────────────────┘

  UMA story por sessão para HIGH+
  Até duas stories por sessão para MEDIUM
```

### Epic 3: Interface + Empacotamento (Fase final)

```
Story 3.1: Setup CustomTkinter + Tela Principal
  Complexity: MEDIUM
  Agente especial: @ux-design-expert (Sonnet) para wireframes

Story 3.2: Wizard Passo 1 — Seleção de Tese
  Complexity: LOW

Story 3.3: Wizard Passo 2 — Importação de PDFs (drag & drop)
  Complexity: MEDIUM

Story 3.4: Wizard Passo 3 — Revisão de Dados Extraídos
  Complexity: HIGH → Architect Gate
  CRÍTICO: Tabela editável com dados extraídos

Story 3.5: Wizard Passo 4 — Exportação XLSX
  Complexity: MEDIUM

Story 3.6: Empacotamento PyInstaller (.exe)
  Complexity: HIGH → Architect Gate
  CRÍTICO: Incluir Tesseract OCR, ≤200MB
```

**Fluxo do Epic 3:**

```
Para stories de UI, adicionar @ux-design-expert:

  @sm (Opus) → Cria story
  @po (Opus) → Valida story
  @ux-design-expert (Sonnet) → Wireframe / Layout     ← NOVO
  @architect (Opus) → Gate (se HIGH+)
  @dev (Haiku) → Implementa
  @qa (Sonnet) → QA Gate
  @devops (Haiku) → Push

Para Story 3.6 (empacotamento):
  @devops (Haiku) → Configura PyInstaller
  @qa (Sonnet) → Testa .exe em Windows limpo
```

---

## PARTE 4: DIAGRAMA VISUAL COMPLETO

### Fluxo de Uma Story (Versão Final)

```
                    ┌─────────────┐
                    │  PRD + Arch  │  (feito uma vez)
                    │  Opus        │
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │  @sm cria story (Opus)  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  @po valida (Opus)      │
              │  GO? ──── NO-GO? ───┐   │
              └────┬────────────────│───┘
                   │                │
                   │         volta para @sm
                   ↓
         ┌─────────────────────┐
         │  Complexity HIGH+?  │
         └──┬──────────────┬───┘
          SIM             NÃO
            ↓               ↓
  ┌─────────────────┐       │
  │ ★ ARCHITECT     │       │
  │   GATE (Opus)   │       │
  │                 │       │
  │ • Design brief  │       │
  │ • Edge cases    │       │
  │ • Armadilhas    │       │
  └────────┬────────┘       │
           │                │
           ↓                ↓
  ┌────────────────────────────────┐
  │  @dev implementa (Haiku)       │
  │                                │
  │  ★ PROGRESSIVE VALIDATION:     │
  │                                │
  │  Task 1 → test → ✓            │
  │  Task 2 → test → ✓            │
  │  Task 3 → test → ✓            │
  │  Task 4 → test → ✓            │
  │  Task 5 → test → ✓            │
  │           ↓                    │
  │     ALL PASS                   │
  └────────────┬───────────────────┘
               ↓
  ┌────────────────────────┐
  │  @qa QA Gate (Sonnet)  │
  │  7 checks              │
  └────┬───────────┬───────┘
       │           │
     PASS        FAIL
       ↓           ↓
  ┌─────────┐  ┌──────────────┐
  │ @devops │  │  QA LOOP     │
  │ push    │  │  @dev fix    │
  │ (Haiku) │  │  (Haiku)     │
  │         │  │     ↓        │
  │  DONE ✅ │  │  @qa review  │
  │         │  │  (Sonnet)    │
  └─────────┘  │     ↓        │
               │  max 5 loops │
               └──────────────┘
```

### Fluxo do Projeto Inteiro

```
════════════════════════════════════════════════════
           PLANEJAMENTO (uma vez)
════════════════════════════════════════════════════

  Briefing → @pm (Opus) → PRD
                ↓
           @architect (Opus) → Arquitetura
                ↓
           @po (Opus) → Validação cruzada
                ↓
           Shard documentos

════════════════════════════════════════════════════
           EPIC 1: CORE ENGINE
════════════════════════════════════════════════════

  Story 1.1 ✅ ──── Setup ──────────────── DONE
  Story 1.2 ✅ ──── PDF Reader ─────────── DONE
  Story 1.3 ✅ ──── Parser DDPE ────────── DONE
  Story 1.4 🔧 ──── Fix SPPREV Apos. ──── NEXT (Sessão A)
  Story 1.5 🔧 ──── Fix SPPREV Pens. ──── NEXT (Sessão B)
  Story 1.6 ⏳ ──── Pipeline Lote ──────── NEXT (Sessão C)
        ↓
  ★ CHECKPOINT: Rodar TODOS os testes do Epic 1
  ★ Verificar: >95% pass rate, >80% coverage

════════════════════════════════════════════════════
           EPIC 2: TESES + XLSX
════════════════════════════════════════════════════

  Story 2.1 ──── Plugin Architecture ──── Sessão D
  Story 2.2 ──── Módulo IAMSPE ─────────── Sessão E
  Story 2.3 ──── Diferença de Classe ───── Sessão F
  Story 2.4 ──── Quinquênio ────────────── Sessão F (MEDIUM, pode combinar)
  Story 2.5 ──── XLSX com Fórmulas ─────── Sessão G
  Story 2.6 ──── Aprendizado Verbas ────── Sessão H
  Story 2.7 ──── Normalização/Aliases ──── Sessão H (MEDIUM, pode combinar)
        ↓
  ★ CHECKPOINT: Teste integrado Epic 1 + Epic 2
  ★ Testar com PDFs reais do escritório

════════════════════════════════════════════════════
           EPIC 3: UI + EMPACOTAMENTO
════════════════════════════════════════════════════

  Story 3.1 ──── Setup CustomTkinter ──── Sessão I
  Story 3.2 ──── Wizard Step 1 ─────────── Sessão I (LOW, combina)
  Story 3.3 ──── Wizard Step 2 (drag&drop) Sessão J
  Story 3.4 ──── Wizard Step 3 (tabela) ── Sessão K
  Story 3.5 ──── Wizard Step 4 (export) ── Sessão L
  Story 3.6 ──── PyInstaller .exe ──────── Sessão M
        ↓
  ★ CHECKPOINT FINAL:
  ★ Teste completo: PDF → Extração → Edição → XLSX
  ★ Teste com estagiário real (usabilidade)
  ★ Empacotamento final

════════════════════════════════════════════════════
           ENTREGA 🎉
════════════════════════════════════════════════════
```

---

## PARTE 5: MAPA DE MODELOS POR SESSÃO

### Legenda

```
🔴 OPUS    = Decisões críticas, estratégia, criação
🟡 SONNET  = Análise, revisão, QA
🟢 HAIKU   = Código, execução, operações
```

### Tabela Completa

| Sessão | Story | Agentes + Modelos | Duração Est. |
|--------|-------|-------------------|-------------|
| **Planejamento** | — | 🔴 @pm + 🔴 @architect + 🔴 @po | 2-3h |
| A | 1.4 fix | 🔴 @architect (brief) → 🟢 @dev (fix) → 🟡 @qa | 1-2h |
| B | 1.5 fix | 🔴 @architect (brief) → 🟢 @dev (fix) → 🟡 @qa | 2-3h |
| C | 1.6 | 🔴 @sm → 🔴 @po → 🔴 @architect → 🟢 @dev → 🟡 @qa | 2-3h |
| D | 2.1 | 🔴 @sm → 🔴 @po → 🔴 @architect → 🟢 @dev → 🟡 @qa | 3-4h |
| E | 2.2 | 🔴 @sm → 🔴 @po → 🔴 @architect → 🟢 @dev → 🟡 @qa | 2-3h |
| F | 2.3+2.4 | 🔴 @sm → 🔴 @po → 🟢 @dev → 🟡 @qa | 2-3h |
| G | 2.5 | 🔴 @sm → 🔴 @po → 🔴 @architect → 🟢 @dev → 🟡 @qa | 3-4h |
| H | 2.6+2.7 | 🔴 @sm → 🔴 @po → 🟢 @dev → 🟡 @qa | 2-3h |
| I | 3.1+3.2 | 🔴 @sm → 🟡 @ux → 🟢 @dev → 🟡 @qa | 2-3h |
| J | 3.3 | 🔴 @sm → 🟡 @ux → 🟢 @dev → 🟡 @qa | 2-3h |
| K | 3.4 | 🔴 @sm → 🟡 @ux → 🔴 @architect → 🟢 @dev → 🟡 @qa | 3-4h |
| L | 3.5 | 🔴 @sm → 🟡 @ux → 🟢 @dev → 🟡 @qa | 2-3h |
| M | 3.6 | 🔴 @sm → 🔴 @architect → 🟢 @devops → 🟡 @qa | 3-4h |
| **TOTAL** | | | **~30-40h** |

---

## PARTE 6: ANTES vs DEPOIS — COMPARAÇÃO DIRETA

### Para uma Story de Complexidade HIGH

```
╔══════════════════════════════════════════════════════════════╗
║  ANTES (sem melhorias)                                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  @sm cria ──→ @po valida ──→ @dev implementa TUDO ──→ @qa   ║
║  (qualquer     (qualquer      (Haiku, tudo de uma    (review ║
║   modelo)       modelo)        vez, testa no final)   final) ║
║                                                              ║
║  Resultado típico: QA FAIL → Fix 3-5h → Re-QA → PASS       ║
║  Tempo total: ~7 horas                                       ║
║  Tokens: ~450K                                               ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  DEPOIS (com melhorias 1, 3 + model selection)               ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  @sm cria ──→ @po valida ──→ ★ @architect ──→ @dev ──→ @qa  ║
║  (Opus)       (Opus)          GATE (Opus)    (Haiku)  (Sonnet)║
║                                15 min design  valida         ║
║                                brief          task por       ║
║                                               task           ║
║                                                              ║
║  Resultado típico: QA PASS (ou CONCERNS menores)             ║
║  Tempo total: ~3 horas                                       ║
║  Tokens: ~200K                                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

ECONOMIA: ~57% tempo, ~55% tokens
```

---

## PARTE 7: REGRAS PARA O USUÁRIO (Resumo Simples)

### 5 Regras de Ouro

**1. Uma story complexa por sessão**
> Não apresse. Dê tempo e tokens para o trabalho ser bem feito.

**2. Sempre use o modelo certo**
> Quando ativar um agente, veja o aviso de modelo e troque se necessário.
> - Decisões → Opus
> - Revisão → Sonnet
> - Código → Haiku

**3. Para stories difíceis, peça ao Architect primeiro**
> Antes de mandar o Dev implementar, peça ao Architect para revisar a abordagem.
> "Quais são as armadilhas dessa story?" — 15 minutos que salvam horas.

**4. Teste após cada pedaço, não no final**
> Peça ao Dev para rodar testes após cada task.
> Bug pego cedo = 5 minutos de fix. Bug pego tarde = 2 horas.

**5. Use seus PDFs reais como base de teste**
> Coloque PDFs reais em docs/referencias/ e peça ao Dev para extrair texto deles como fixture.

### Quando Algo Dá Errado

```
QA deu FAIL?
  ↓
Não entre em pânico.
  ↓
1. Leia o relatório QA (ele diz EXATAMENTE o que está errado)
2. Chame @architect (Opus) se o bug for de design
3. Chame @dev (Haiku) se o bug for de código
4. Chame @qa (Sonnet) para re-verificar
5. Loop até PASS (máximo 5 tentativas)
```

---

## PARTE 8: SEQUÊNCIA RECOMENDADA PARA AMANHÃ

### Plano de Ação Imediato

```
SESSÃO 1 (amanhã):
  1. Revisar esta análise ← VOCÊ ESTÁ AQUI
  2. Decidir quais melhorias implementar
  3. @architect (Opus): design-brief para fixes 1.4 & 1.5
  4. @dev (Haiku): Fix Story 1.4 (progressive validation)
  5. @qa (Sonnet): Re-review 1.4

SESSÃO 2:
  1. @dev (Haiku): Fix Story 1.5
  2. @qa (Sonnet): Re-review 1.5

SESSÃO 3:
  1. @sm (Opus): Criar Story 1.6
  2. @po (Opus): Validar
  3. @architect (Opus): Gate
  4. @dev (Haiku): Implementar
  5. @qa (Sonnet): Gate
  → Epic 1 COMPLETO ✅

DEPOIS:
  Seguir para Epic 2 (Teses + XLSX)
```

---

*Documento gerado por Orion (aios-master) — Modelo Opus*
*Projeto: HoleritePRO — Workflow Completo*
*Data: 2026-02-24*
