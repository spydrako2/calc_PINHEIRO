# Análise Estratégica: Gargalos e Otimizações do Framework AIOS
**Data:** 2026-02-24
**Autor:** Orion (aios-master) — Modelo Opus
**Solicitado por:** Usuário (Product Owner / Stakeholder)
**Status:** Para revisão do usuário

---

## Contexto do Usuário

O usuário é advogado, com conhecimentos iniciais em IA e desenvolvimento. Este projeto (HoleritePRO) é estratégico para sua carreira. A maior dificuldade relatada: **problemas que não consegue antecipar ou se adiantar**. O framework AIOS deve funcionar como escudo contra esses problemas imprevistos.

---

## A Pergunta Central

> "O que poderia ter evitado as horas de debugging no core do projeto? O framework está muito pesado?"

**Resposta curta:** O framework não é pesado demais — ele está faltando **gates preventivos**. O QA Gate no final é excelente para DETECTAR problemas, mas o framework precisa de mecanismos para **PREVENIR** problemas antes que eles aconteçam.

---

## 1. O Que Realmente Aconteceu (Linha do Tempo)

| Etapa | Tempo | Tokens | Resultado |
|-------|-------|--------|-----------|
| Sessão 1: Dev (1.4 + 1.5 juntos) | 90 min | 200K | 1150 linhas, 104 testes, **53% passando** |
| Sessão 1: QA Gate | (incluso) | (incluso) | **FAIL + FAIL** |
| Sessão 2: Fixes (estimado) | 3-5h | ~200K | Correções pendentes |
| Sessão 3: QA Re-review (estimado) | 30-60min | ~50K | Re-validação |
| **Total projetado** | **~6-7h** | **~450K tokens** | 2 parsers funcionando |

**Contraste com Story 1.3 (DDPE):**
- Implementado em múltiplas sessões focadas
- 60 testes, **100% passando**
- 88% coverage
- **Zero retrabalho**

A questão é: por que o DDPE saiu perfeito e os SPPREV não?

---

## 2. As 7 Causas-Raiz Identificadas

### Causa 1: Modelo Errado para a Tarefa

**O que aconteceu:** Stories 1.4 e 1.5 foram implementadas com **Haiku** (modelo rápido e barato).

**O problema:** Parsers regex-heavy NÃO são "programação mecânica". Eles exigem:
- Raciocínio sobre estrutura de documento
- Antecipação de edge cases (formato BR vs US, primeira vs última ocorrência)
- Design de template detection que diferencia documentos similares

**O que teria evitado:** A regra de model-selection que acabamos de criar. Haiku é para código mecânico onde a lógica já está clara. Para parsers, Sonnet ou Opus teria previsto que `detect_template()` da Story 1.5 aceitaria documentos de APOSENTADO como PENSIONISTA.

**Impacto estimado:** Economia de 3-5 horas de debugging.

**Status:** ✅ CORRIGIDO — Regra de model-selection implementada em `.claude/rules/model-selection.md`

---

### Causa 2: Duas Stories Complexas na Mesma Sessão

**O que aconteceu:** Stories 1.4 e 1.5 (ambas complexity=HIGH, 500+ linhas cada) foram feitas em uma única sessão de 90 minutos com 200K tokens.

**O problema:**
- 200K tokens / 2 stories = ~100K cada
- 100K tokens para 550 linhas de parser + 50 testes + documentação = **orçamento apertado**
- O dev provavelmente apressou no final, sem tempo para validar padrões
- Contexto poluído: padrões do parser 1.4 vazam para 1.5

**O que teria evitado:** Uma sessão por story. O DDPE (Story 1.3) teve sua própria sessão focada e saiu perfeito.

**Regra sugerida:** `MAX_COMPLEXITY_PER_SESSION: HIGH = 1 story, MEDIUM = 2 stories`

**Status:** ⏳ PENDENTE — Precisa implementar como regra no framework

---

### Causa 3: Sem Revisão Arquitetural Pré-Implementação

**O que aconteceu:** @dev implementou diretamente, sem @architect revisar a estratégia de template detection.

**O problema crítico:** O bug ARQUITETURAL da Story 1.5 (template detection aceita APOSENTADO como PENSIONISTA) é um erro de **design**, não de **código**. Se @architect tivesse analisado "como diferenciar 3 templates SPPREV?" por 15 minutos ANTES da implementação, o bug nunca teria existido.

**O que teria evitado:** Um "Architect Gate" para stories HIGH complexity:

```
Story complexity >= HIGH?
  → @architect review design approach (15-30 min)
  → Then @dev implements
```

**Impacto:** 15 minutos de design = economia de 2-3 horas de debugging + retrabalho.

**Status:** ⏳ PENDENTE — Precisa adicionar ao workflow SDC

---

### Causa 4: Testes com Fixtures Artificiais (Não de PDFs Reais)

**O que aconteceu:** Testes usam strings hardcoded como fixtures. Os bugs aparecem quando o texto REAL do PDF não bate com o padrão esperado.

**O problema:**
- `_extract_totals()` falha porque o texto real tem "BASE IR" ANTES de "TOTAL LÍQUIDO"
- `_parse_valor()` falha porque o formato real é "5604.34" (não "5.604,34")
- Fixtures artificiais não capturam a realidade do documento

**O que teria evitado:** **Test-First com dados reais.**

```
ANTES de escrever código:
1. Pegar UM PDF real de SPPREV Aposentado
2. Extrair o texto com pdfplumber
3. Usar ESSE texto como fixture de teste
4. Então escrever regex para casar COM ESSE texto
```

Isso é TDD real: fixture real → teste que falha → código que passa.

**Status:** ⏳ PENDENTE — Precisa adicionar como regra para stories de parsing

---

### Causa 5: Código Duplicado Entre Parsers

**O que aconteceu:** `_parse_valor()` existe em **3 parsers** com implementações ligeiramente diferentes. O bug de formato (×100) existe na versão do Pensionista mas não no DDPE.

**O problema:** Violação de DRY. A mesma lógica (parsear valor monetário BR/US) é reimplementada 3 vezes, com bugs diferentes.

**O que teria evitado:** Extrair `_parse_valor()` para `BaseParser` ou para um utility:

```python
# src/core/parsers/base_parser.py
class BaseParser:
    @staticmethod
    def parse_valor(valor_str: str) -> float:
        """Implementação ÚNICA, testada UMA vez, usada por todos."""
        ...
```

**Impacto:** Bug corrigido uma vez, corrigido em todos os parsers.

**Status:** ⏳ PENDENTE — Refactoring técnico para próxima sessão de dev

---

### Causa 6: Validação Tardia (Tudo no Final)

**O que aconteceu:** O @dev implementou todos os 5 tasks (header, verbas, totals, detection, E2E) e só rodou testes no final.

**O problema:** Se tivesse rodado testes após **cada task**, teria pego o bug de template detection ANTES de escrever 400 linhas de código que dependem dele.

**O que teria evitado:** Validação progressiva:

```
Task 1: Template detection → pytest -k "test_detect" → PASS? → Continue
Task 2: Header extraction  → pytest -k "test_cabecalho" → PASS? → Continue
Task 3: Verba extraction   → pytest -k "test_verbas" → PASS? → Continue
Task 4: Totals extraction  → pytest -k "test_totals" → PASS? → Continue
Task 5: E2E integration    → pytest -v → ALL PASS? → Submit to QA
```

**Status:** ⏳ PENDENTE — Precisa adicionar como regra mandatória no dev workflow

---

### Causa 7: Modo de Execução Errado

**O que aconteceu:** As stories aparentemente foram executadas em modo **YOLO** (autônomo, 0-1 prompts).

**O problema:** Para parsers com complexidade HIGH e padrões de regex que precisam de interpretação de documento, YOLO é arriscado. O modo **Pre-Flight** teria levantado todas as questões ANTES:

- "O texto real do SPPREV Aposentado contém quais keywords?"
- "Como diferenciar APOSENTADO de PENSIONISTA se ambos têm SPPREV?"
- "O valor monetário vem em formato BR ou US?"

**O que teria evitado:** Pre-Flight → 15 perguntas → plano claro → execução sem ambiguidade.

**Status:** ⏳ PENDENTE — Considerar tornar Pre-Flight obrigatório para stories HIGH

---

## 3. O Framework é Pesado Demais?

**Resposta: Não.** Mas precisa de ajustes.

### O que o framework fez BEM:
- ✅ O QA Gate **pegou todos os bugs** antes de merge (proteção funcionou)
- ✅ A documentação gerada é excelente (4 relatórios QA detalhados)
- ✅ A regressão foi verificada (DDPE continua funcionando)
- ✅ O decision log cria audit trail valioso
- ✅ O story-driven development mantém foco e rastreabilidade

### O que está faltando no framework:

| Gap | Impacto | Solução Proposta |
|-----|---------|-----------------|
| Sem "Architect Gate" pré-implementação | Bugs de design passam para código | Adicionar gate para stories HIGH+ |
| Sem regra de 1 story/sessão para HIGH | Sessões sobrecarregadas | Adicionar constraint no workflow |
| Sem mandato de fixtures reais | Testes não refletem realidade | Exigir TDD com dados reais |
| Sem utility compartilhado | Bugs duplicados em 3 parsers | Extrair para BaseParser |
| Sem validação progressiva | Bugs descobertos tarde | Testar após cada task |
| Sem model-selection | Modelo fraco para tarefas complexas | ✅ Já implementado |

---

## 4. Proposta: 6 Melhorias ao Framework

### Melhoria 1: Architect Pre-Review Gate (NOVO)

**Regra:** Stories com complexity >= HIGH passam por @architect antes de @dev.

```
Story complexity >= HIGH?
  → @architect: "Revise a abordagem técnica em 15 min"
  → Output: design-brief com padrões, edge cases, diferenciação
  → @dev implementa com design-brief como referência
```

**Custo:** 15-30 min extra por story HIGH
**Economia:** 2-5 horas de debugging evitado
**Para o usuário:** Isso é como ter um engenheiro revisando a planta antes de construir.

---

### Melhoria 2: Session Budget Rules (NOVO)

| Complexity | Max Stories/Session | Min Tokens/Story |
|-----------|-------------------|-----------------|
| LOW | 3 | 50K |
| MEDIUM | 2 | 100K |
| HIGH | **1** | **150K** |
| VERY HIGH | 1 | 200K+ |

**Para o usuário:** Não tente fazer muito de uma vez. Uma story complexa bem feita vale mais que duas apressadas.

---

### Melhoria 3: Progressive Validation (NOVO)

**Regra:** @dev DEVE rodar testes após cada task, não só no final.

```
Task N complete → pytest -k "task_N" → PASS? → Continue
                                      → FAIL? → Fix ANTES de avançar
```

**Para o usuário:** É como verificar cada andar de um prédio antes de construir o próximo.

---

### Melhoria 4: Real Fixture Mandate (NOVO)

**Regra:** Para stories que envolvem parsing de documentos:

```
ANTES de escrever código:
1. Extrair texto de ≥1 documento real
2. Salvar como fixture em tests/fixtures/
3. Escrever testes usando essas fixtures
4. ENTÃO implementar parser
```

**Para o usuário:** Usar os seus PDFs reais como base de teste, não textos inventados.

---

### Melhoria 5: Shared Utility Extraction (TÉCNICO)

Extrair funções duplicadas para `BaseParser`:
- `parse_valor()` → uma implementação para todos os parsers
- `detect_section()` → padrão reutilizável
- `search_backwards()` → utility para busca reversa

**Para o usuário:** Corrigir um bug uma vez em vez de três vezes.

---

### Melhoria 6: Model Selection (✅ JÁ IMPLEMENTADO)

A regra que criamos hoje resolve o problema de usar o modelo errado para cada tarefa.

- **Opus** → Decisões estratégicas, criação de stories, arquitetura
- **Sonnet** → QA, revisão de código, análise
- **Haiku** → Programação direta, operações simples

---

## 5. Impacto Projetado

### Se essas melhorias existissem ANTES das Stories 1.4 & 1.5:

| Etapa | Sem Melhorias (atual) | Com Melhorias (projetado) |
|-------|----------------------|--------------------------|
| Architect review | 0 min | 15 min |
| Dev implementation | 90 min (2 stories) | 90 min (1 story) + 60 min (1 story) |
| Testes passando | 53% | >90% (fixtures reais + validação progressiva) |
| QA Gate | FAIL + FAIL | PASS ou CONCERNS |
| Fix cycle | 3-5 horas | 0-30 min |
| Re-QA | 30-60 min | Não necessário |
| **Total** | **~7 horas** | **~3 horas** |
| **Tokens** | **~450K** | **~200K** |

**Economia projetada: ~57% em tempo, ~55% em tokens.**

---

## 6. Analogia para o Usuário (Advogado)

Pense no framework AIOS como um escritório de advocacia:

- **O QA Gate** é o revisor que lê a petição antes de protocolar → **funciona bem, pegou os erros**
- **O que faltava** é o planejamento da tese antes de redigir → gastar 15 min pensando na estratégia evita horas reescrevendo a peça
- **Stories complexas em paralelo** é como redigir duas peças complexas ao mesmo tempo → a qualidade de ambas cai
- **Fixtures reais** são como usar a jurisprudência real na pesquisa, não inventar precedentes
- **Model selection** é como escolher o advogado certo para cada tipo de causa → não colocar um estagiário para fazer uma peça de alta complexidade

**A metáfora central:** O framework tem um excelente inspetor (QA Gate) que verifica DEPOIS da construção. O que falta é o engenheiro estrutural (Architect Gate) que revisa a planta ANTES de construir.

---

## 7. Próximos Passos (Checklist para Revisão)

- [ ] Revisar esta análise e decidir quais melhorias implementar
- [ ] Implementar Melhoria 1 (Architect Gate) como regra no workflow
- [ ] Implementar Melhoria 2 (Session Budget) como regra
- [ ] Implementar Melhoria 3 (Progressive Validation) como regra do @dev
- [ ] Implementar Melhoria 4 (Real Fixtures) como mandato para stories de parsing
- [ ] Agendar sessão @dev para fixes das Stories 1.4 & 1.5 (com model correto)
- [ ] Extrair `_parse_valor()` para BaseParser (Melhoria 5) durante os fixes

---

## 8. Status das Regras Já Implementadas Hoje

| Regra | Arquivo | Status |
|-------|---------|--------|
| Model Selection | `.claude/rules/model-selection.md` | ✅ Implementado |
| Model Config | `.aios-core/core-config.yaml` (seção modelSelection) | ✅ Implementado |

---

*Relatório gerado por Orion (aios-master) — Modelo Opus*
*Projeto: HoleritePRO — Core Engine Development*
*Data: 2026-02-24*
