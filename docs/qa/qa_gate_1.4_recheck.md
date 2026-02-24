# QA Gate Report — Story 1.4 Re-check
## SPPREV Aposentado Parser

| Field | Value |
|-------|-------|
| **Story ID** | 1.4 |
| **Date** | 2026-02-24 |
| **Reviewer** | @qa (Quinn) |
| **Review Type** | Re-check after FAIL verdict (bugs fixed by @dev) |
| **Previous Verdict** | FAIL |
| **This Verdict** | **CONCERNS** |

---

## Context

Story 1.4 received a FAIL verdict in the previous QA Gate for four bugs:
1. `_extract_verbas()` premature termination on "BASE"/"TOTAL" keywords
2. `_extract_totals()` wrong values with two-line format
3. `_parse_valor()` American format detection error
4. Valor regex capturing partial Brazilian numbers

The developer (@dev / Dex) fixed all four reported bugs. This re-check evaluates the fixes and the overall quality of the implementation.

---

## Check 1: Code Review — Patterns, Readability, Maintainability

**Result: PASS with observations**

### Positive findings

- Parser correctly inherits from `BaseParser` (ABC), implementing all abstract methods: `detect_template()`, `parse()`, `_extract_cabecalho()`, `_extract_verbas()`, `_extract_totals()`.
- `_parse_valor()` fix is correct: uses `len(parts[1]) <= 2` to distinguish American decimal (1-2 digits) from Brazilian thousands (3 digits). Logic is clean and well-commented.
- `_extract_totals()` two-line rewrite is functionally correct: detects header line containing "VENCTO" + "DESCONTO" + "QUIDO", reads next non-empty line, extracts last 3 monetary values positionally. Handles both two-line and single-line formats.
- `_extract_verbas()` fix correctly removed the overly broad "BASE"/"TOTAL" keyword filters; now only skips empty lines and header-column lines ("CÓDIGO").
- Error handling in `_extract_verbas()` silently skips malformed lines (ValueError, AttributeError, IndexError) without crashing — appropriate for a batch-processing parser.
- Code is well-documented with docstrings on every method.
- `detect_template()` requires 2+ keyword matches — a sound design that reduces false positives.

### Issues found

**MEDIUM — Dead code: `PATTERNS` dict and `_extract_field()` method are unused**

The class defines a `PATTERNS` dict (lines 40-53) with patterns for nome, entidade, cargo, etc. and a `_extract_field()` helper method (lines 435-458) that reads from `PATTERNS`. However, `_extract_cabecalho()` never calls `_extract_field()` — it uses inline `re.search()` calls instead. The `PATTERNS` dict is dead code that adds cognitive overhead and will confuse future maintainers.

**LOW — Semantic inconsistency: `NaturezaVerba.DEBITO` mapping for NAT='D'**

In `_extract_verbas()` (lines 343-346), the parser maps NAT marker `'D'` to `NaturezaVerba.DEBITO`. However, in `data_model.py`, `DEBITO` has enum value `'DB'` (not `'D'`), and `'D'` is the value for `NaturezaVerba.DEVOLUCAO`. This is a semantic mismatch: the parser treats SPPREV's 'D' (Debito) as `NaturezaVerba.DEBITO`, but the enum's 'D' value belongs to `DEVOLUCAO`. The intent appears correct (SPPREV D = debit transaction), but the relationship between the NAT marker and the enum value is inconsistent with how the enum was designed. No tests exercise the D-marker path, so this latent inconsistency has not caused test failures.

**LOW — `cargo` not extracted from the realistic test fixture**

The `sample_spprev_page` fixture has `"CARCEREIRO DE 1A CLASSE 100,00 NORMAL"` on the line following `CARGO % APOSENTADORIA TIPO FOLHA`. The cargo regex `r"CARGO\s+([A-ZÁÉÍÓÚÂÃÕÊÔ\w\s\d\/\-]+?)\s+%"` does not match across lines, so `cargo` is `None` in E2E tests. The story requires cargo extraction (AC2), and the fixture text shows the data is present but parsed to `None`. The test `test_extract_cargo` explicitly ignores the result to avoid the failure, making the gap invisible.

---

## Check 2: Unit Tests — Coverage and Quality

**Result: PASS**

### Quantitative summary

| Test module | Tests | Result |
|-------------|-------|--------|
| `test_spprev_aposentado_parser_cabecalho.py` | 21 | 21 PASS |
| `test_spprev_aposentado_parser_proventos.py` | 11 | 11 PASS |
| `test_spprev_aposentado_parser_totals.py` | 9 | 9 PASS |
| `test_spprev_aposentado_parser_e2e.py` | 17 | 17 PASS |
| **TOTAL** | **58** | **58 PASS (100%)** |

Coverage for `spprev_aposentado_parser.py`: **84%** (199 stmts, 31 missed)

Coverage target per story: >= 80%. **Target met: 84%.**

### Qualitative notes

- Tests are well-structured using pytest fixtures and class-based organization.
- Good test naming (descriptive, follows `test_<what>_<expected>` pattern).
- Edge cases covered: zero descontos, multi-page holerite, totals not found, CPF/Nome missing (raises ValueError).
- `test_extract_cargo` is written to deliberately catch `ValueError` and pass regardless — this masks the fact that cargo extraction does not work in the standard layout.
- No tests exercise the NAT='C' (CREDITO) or NAT='D' (DEBITO) code paths in `_extract_verbas()` — the 'D' semantic issue identified in Check 1 has no test coverage.
- `test_extract_cpf_format_normalized` (line 75-80) passes without actually asserting anything — it is effectively a no-op test.

---

## Check 3: Acceptance Criteria Coverage

**Result: CONCERNS**

### AC1 — Parser implements BaseParser interface
**PASS.** `SpprevAposentadoParser` inherits from `BaseParser`. All abstract methods implemented. Verified in tests and by inspection.

### AC2 — Extracts specific cabecalho fields
**PARTIAL.** Story requires extraction of: nome, entidade, cargo, competencia, regime retribuicao, beneficio, percentual aposentadoria, CPF, numero beneficio, tipo folha, banco/agencia/conta, nivel.

| Field | Extracted | Stored in data model | Notes |
|-------|-----------|----------------------|-------|
| nome | YES | YES (cabecalho.nome) | OK |
| CPF | YES | YES (cabecalho.cpf) | OK |
| entidade | YES | YES (cabecalho.unidade) | Stored as `unidade` |
| cargo | YES (pattern) | YES (cabecalho.cargo) | Parser regex fails on multi-line layout |
| competencia | YES | YES (cabecalho.competencia) | OK |
| tipo_folha | YES | YES (cabecalho.tipo_folha) | OK |
| regime retribuicao | Parsed | NOT STORED | Parsed but discarded |
| beneficio | Parsed | NOT STORED | Parsed but discarded |
| percentual_aposentadoria | Parsed | NOT STORED | Parsed but discarded |
| numero_beneficio | Parsed | NOT STORED | Parsed but discarded |
| banco | Parsed | NOT STORED | Parsed but discarded |
| agencia | Parsed | NOT STORED | Parsed but discarded |
| conta | Parsed | NOT STORED | Parsed but discarded |
| nivel | Parsed | NOT STORED | Parsed but discarded |

The `CabecalhoHolerite` data model does not have fields for the SPPREV-specific attributes (beneficio, percentual_aposentadoria, banco, agencia, conta, nivel). The parser extracts these values internally but discards them because the data model has no place to store them. This may be an intentional architectural decision (shared data model across templates) documented in Dev Notes, or it may indicate the data model needs extension for SPPREV-specific fields.

Note: This limitation exists at the data model layer, not the parser layer. If the PRD requires these fields to be accessible to consumers, the data model must be extended. This is a pre-existing architectural constraint, not a regression introduced in this story.

### AC3 — Extracts verbas with: codigo, denominacao, natureza, quantidade, unidade, periodo, vencimento, descontos
**PARTIAL.** Extraction verified for:

| Field | Extracted | Notes |
|-------|-----------|-------|
| codigo | YES (6-digit) | OK |
| denominacao | YES | OK |
| natureza | YES (N/C/D) | D marker has semantic issue (Check 1) |
| quantidade | PARTIAL | Parsed from position but unreliable; no tests validate quantity values |
| unidade | NO | Always `None` — parser hardcodes `unidade=None` |
| periodo | NO | `periodo_inicio` and `periodo_fim` always `None`; the period string (e.g., "11/2025") is present in the line but not parsed into the Verba |
| valor (vencimento) | YES | OK |
| descontos separation | NO | Descontos are not distinguished from vencimentos in the Verba (no separate field) |

The story AC3 explicitly requires "valores separados em colunas Vencimento e Descontos" — this means a verba should indicate whether it is a vencimento or desconto. Currently, all verbas get the same field `valor`, with no column attribution. This is consistent with DDPE's approach but the AC explicitly calls for column separation.

### AC4 — Extracts totals: base_ir, base_redutor, base_contrib_prev, total_vencimentos, total_descontos, total_liquido
**PARTIAL.** The two-line format fix correctly extracts the last 3 values (vencimentos, descontos, liquido). However:

- `base_ir`, `base_redutor`, and `base_contrib_prev` are present in the SPPREV totals line but are NOT extracted or stored anywhere.
- The `Holerite` data model has no fields for these three base values.
- This is consistent with the data model design but the AC explicitly names all 6 fields.

Same architectural constraint as AC2: the shared data model does not accommodate SPPREV-specific fields.

### AC5 — Template detector identifies by "DIRETORIA DE BENEFICIOS SERVIDORES"
**PASS with observation.** `detect_template()` uses regex keyword matching (requires 2+ of 3 keywords), not fuzzy string matching as specified in the story ("fuzzy match: score >= 0.75"). Regex-based detection is functionally equivalent and arguably more robust for the stated purpose. The detection correctly identifies SPPREV documents in all tests. This is an acceptable implementation choice.

### AC6 — Tests with real SPPREV aposentado holerites
**PARTIAL.** The E2E tests use realistic mock data based on the real Fernando Pedroso Rocha holerite structure. There are no tests that load and parse actual PDF files from `docs/referencias/`. The story's implementation plan (Task 5) calls for "Testes com holerites SPPREV reais (3+)". The E2E tests simulate real data accurately but do not test the full pipeline including PDF reading.

---

## Check 4: No Regressions

**Result: PASS**

Full regression suite executed against all existing tests:

| Test module | Tests | Result |
|-------------|-------|--------|
| `test_base_parser.py` | 7 | 7 PASS |
| `test_data_model.py` | 8 | 8 PASS |
| `test_ddpe_parser_cabecalho.py` | 16 | 16 PASS |
| `test_ddpe_parser_verbas.py` | 11 | 11 PASS |
| `test_ddpe_parser_totals.py` | 7 | 7 PASS |
| `test_ddpe_parser_e2e.py` | 21 | 19 PASS, 2 SKIP (real PDFs) |
| All 1.4 tests | 58 | 58 PASS |
| **TOTAL** | **128** | **128 PASS, 2 SKIP, 0 FAIL** |

The `data_model.py` change (adding `CREDITO` and `DEBITO` to `NaturezaVerba`) did not break any existing tests. The DDPE parser, base parser, and data model tests all pass without modification.

---

## Check 5: Performance

**Result: PASS**

Benchmark: 10 consecutive parse operations on a realistic SPPREV holerite page.

| Metric | Value | Threshold |
|--------|-------|-----------|
| Average parse time | 0.0007 seconds | < 5 seconds |
| Status | PASS | |

Performance is well within the 5-second requirement. Regex-based extraction with no I/O operations in the parse path is efficient.

---

## Check 6: Security

**Result: PASS**

### Regex safety

All regex patterns tested for ReDoS (catastrophic backtracking) with 1000-character adversarial strings. All patterns returned in < 0.001 seconds:

| Pattern | Result |
|---------|--------|
| `COMPET[ENCIA]?.*?\s+(\d{1,2}[/\-]\d{4})` | SAFE |
| `ENTIDADE\s+BENEF.*?\n\s*([A-Z\w\s\/\-]+?)\s+(?:APOSENTADORIA\|PENS)` | SAFE |
| `^(\d{6})\s+` | SAFE |
| `([-]?[\d.,]+)\s*$` | SAFE |
| `[-]?[\d.,]+` | SAFE |

### File handling

- Parser receives pre-extracted text from `PaginaExtraida` objects — no direct file I/O in the parser itself.
- No `eval()`, `exec()`, or dynamic code execution.
- No subprocess calls.
- No SQL construction.
- No external network calls.

### Input validation

- `_parse_valor()` uses try/except for all float conversions — safe against malformed input.
- `_extract_verbas()` wraps line parsing in try/except — safe against unexpected line formats.
- `_extract_cabecalho()` raises `ValueError` for missing required fields (CPF, Nome) rather than returning partial data — appropriate defensive behavior.

---

## Check 7: Documentation

**Result: PASS**

- Story file (`docs/stories/1.4.story.md`) updated with Fix notes in File List section.
- All task checkboxes marked complete.
- Change Log entry added (version 0.3) with description of fixes and test results.
- Parser class has a comprehensive docstring describing the template and all extraction categories.
- All methods have docstrings with Args/Returns/Raises sections.
- Dev Notes section in story references architectural decisions (reuse BaseParser, formato XXXXXX, normalizer).
- Story status correctly set to `InReview`.

---

## Issues Summary

| ID | Severity | Category | Description | Recommendation |
|----|----------|----------|-------------|----------------|
| I-1 | MEDIUM | Code | Dead code: `PATTERNS` dict and `_extract_field()` method defined but never called from `_extract_cabecalho()` | Remove dead code or refactor `_extract_cabecalho()` to use `_extract_field()` |
| I-2 | MEDIUM | Requirements | AC2: 8 SPPREV-specific header fields parsed but discarded (data model has no storage for them) | Document as architectural constraint or extend `CabecalhoHolerite` with SPPREV-specific fields |
| I-3 | MEDIUM | Requirements | AC3: `periodo_inicio`/`periodo_fim` and `unidade` fields in Verba always `None` despite period data being available in the source text | Implement period parsing in `_extract_verbas()` |
| I-4 | MEDIUM | Requirements | AC4: `base_ir`, `base_redutor`, `base_contrib_prev` not extracted or stored despite being present in the SPPREV totals row | Document as architectural constraint or extend `Holerite` with SPPREV-specific totals |
| I-5 | LOW | Code | `NaturezaVerba.DEBITO` (value='DB') used for SPPREV NAT='D' marker, but `NaturezaVerba.DEVOLUCAO` has value='D' — semantic mismatch | Clarify SPPREV's D marker semantic and align with enum values; add test for D-marker verbas |
| I-6 | LOW | Tests | `test_extract_cpf_format_normalized` makes no assertions — no-op test providing false confidence | Add assertion or remove the test |
| I-7 | LOW | Tests | `test_extract_cargo` silently catches ValueError — masks the fact that cargo regex fails on the standard multi-line layout | Fix cargo regex to match across lines, then update test to assert the value |
| I-8 | LOW | Requirements | AC6: No tests run against actual PDF files from `docs/referencias/` — real PDF pipeline not validated | Add at least one integration test loading a real SPPREV aposentado PDF |

---

## Previous Bugs — Fix Verification

| Bug | Previous Status | Fix Applied | Verified |
|-----|----------------|-------------|----------|
| `_extract_verbas()` premature termination on "BASE"/"TOTAL" | FAIL | Removed keyword filter, only skips empty lines and column headers | VERIFIED: `test_extract_multiple_verbas` passes with 8+ verbas |
| `_extract_totals()` wrong values with two-line format | FAIL | Rewritten with positional parsing (last 3 values = venc/desc/liq) | VERIFIED: `test_extract_vencimentos_normal`, `test_extract_descontos_normal`, `test_extract_liquido_normal` all pass with correct values |
| `_parse_valor()` American format detection | FAIL | Fixed: uses `len(parts[1]) <= 2` for decimal detection | VERIFIED: `test_parse_valor_american_format` passes (5000.00 -> 5000.0) |
| Valor regex capturing partial numbers | FAIL | Fixed: broader `[\d.,]+` pattern in `valor_pattern` | VERIFIED: All valor extraction tests pass |

All four previously reported bugs are confirmed fixed.

---

## Final Verdict

### CONCERNS

All four bugs from the previous FAIL verdict are confirmed fixed. The 58 Aposentado tests pass at 100% (84% coverage, above the 80% target). Zero regressions against the existing test suite (128 tests pass).

The CONCERNS verdict is warranted because multiple acceptance criteria are partially met:

- **AC2** (header fields) and **AC4** (6 totals fields) are limited by the shared `CabecalhoHolerite`/`Holerite` data model which has no SPPREV-specific fields. This is an architectural constraint, not a parser bug.
- **AC3** (verba fields) leaves `periodo_inicio`, `periodo_fim`, and `unidade` as always-`None`, even though the source data contains period information.
- **AC6** (real PDFs) is not tested end-to-end against actual PDF files.

These issues are not blocking for a CONCERNS verdict because:
1. The data model limitation is a pre-existing architectural decision shared across all parsers.
2. The core functionality (header, verbas, totals) works correctly and is tested.
3. The period extraction gap does not cause incorrect data — it is missing data.
4. The parser is functionally usable for its primary purpose.

**Recommended actions before Done:**
- (MEDIUM priority) Address I-3: implement period parsing in `_extract_verbas()` so `periodo_inicio` is populated.
- (MEDIUM priority) Address I-1: remove dead `PATTERNS` dict and `_extract_field()` method.
- (LOW priority) Fix `test_extract_cpf_format_normalized` (I-6) and `test_extract_cargo` (I-7).
- (LOW priority) Document I-2 and I-4 as known architectural constraints in Dev Notes if intentional.

The implementation is approved to proceed to @devops for push with the above observations documented. The CONCERNS issues should be addressed in a follow-up task or the next story iteration.

---

*QA Gate report generated by @qa (Quinn) — 2026-02-24*
*Model: claude-sonnet-4-6 (required model for @qa)*
