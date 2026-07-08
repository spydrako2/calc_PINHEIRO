# Model Selection Rules — AIOS Framework

## MANDATORY: Auto-Switch Model on Agent Activation

**Severity: MUST**

When ANY agent is activated (via slash command or `@agent` syntax), the system MUST:

1. **Check the current model** against the recommended model for that agent
2. **If mismatch detected**: Display a prominent warning banner BEFORE the greeting:

```
==============================================================
  MODEL MISMATCH DETECTED
  Current: {current_model} | Required: {required_model}
  Please switch: /model {required_model}
==============================================================
```

3. **Always display the recommended model** in the agent greeting footer:

```
Model: {required_model} | /model {required_model}
```

This ensures the user is NEVER operating with the wrong model for an agent.

### Auto-Switch via Task Tool (Orchestration)

When using the `Task` tool to delegate work to subagents, the `model` parameter MUST be set according to the Agent-to-Model Mapping below. This is **fully automatic** and requires no user action.

```javascript
// MANDATORY: Always set model parameter in Task tool calls
Task(subagent_type="Bash", model="haiku")             // @dev work
Task(subagent_type="general-purpose", model="sonnet")  // @qa work
Task(subagent_type="Plan", model="opus")               // @architect work
Task(subagent_type="Explore", model="haiku")           // Quick searches
```

---

## Model Tiers

| Model | Strengths | Cost | Speed |
|-------|-----------|------|-------|
| **Opus** (claude-opus-4-6) | Advanced reasoning, strategic thinking, problem prediction, architectural decisions | High | Slow |
| **Sonnet** (claude-sonnet-4-6) | Balanced analysis, thorough review, good reasoning | Medium | Medium |
| **Haiku** (claude-haiku-4-5) | Fast execution, direct coding, repetitive tasks | Low | Fast |

---

## Agent-to-Model Mapping

### Lookup Table (Canonical Reference)

| Agent ID | Agent Name | Required Model | Model ID |
|----------|-----------|----------------|----------|
| `architect` | Aria | **opus** | claude-opus-4-6 |
| `pm` | Morgan | **opus** | claude-opus-4-6 |
| `po` | Pax | **opus** | claude-opus-4-6 |
| `sm` | River | **opus** | claude-opus-4-6 |
| `aios-master` | Orion | **opus** | claude-opus-4-6 |
| `analyst` | — | **opus** | claude-opus-4-6 |
| `mvp-cutter` | Razor | **opus** | claude-opus-4-6 |
| `qa` | Quinn | **sonnet** | claude-sonnet-4-6 |
| `ux-design-expert` | — | **sonnet** | claude-sonnet-4-6 |
| `data-engineer` | Dara | **sonnet** | claude-sonnet-4-6 |
| `dev` | Dex | **haiku** | claude-haiku-4-5 |
| `devops` | Gage | **haiku** | claude-haiku-4-5 |
| `squad-creator` | — | **sonnet** | claude-sonnet-4-6 |

### Opus — Strategic & Critical Reasoning

| Agent | Justification |
|-------|--------------|
| **@architect (Aria)** | Architectural decisions require deep reasoning and foresight |
| **@pm (Morgan)** | Epic planning, requirements gathering, strategic alignment |
| **@po (Pax)** | Story validation (10-point checklist), acceptance criteria quality |
| **@sm (River)** | Story creation — well-crafted stories prevent rework downstream |
| **@aios-master (Orion)** | Framework governance, cross-agent orchestration, complex decisions |
| **@analyst** | Research analysis, market assessment, complexity evaluation |
| **@mvp-cutter (Razor)** | Diagnosing waste requires full context understanding; cutting scope requires judgment |

### Sonnet — Analytical & Review Tasks

| Agent | Justification |
|-------|--------------|
| **@qa (Quinn)** | Code review, test analysis, quality gate execution |
| **@ux-design-expert** | UX analysis, design review, accessibility checks |
| **@data-engineer (Dara)** | Schema review, query optimization, migration planning |
| **@squad-creator** | Squad design requires analysis but not deep strategy |

### Haiku — Implementation & Execution

| Agent | Justification |
|-------|--------------|
| **@dev (Dex)** | Direct coding, line-by-line implementation, test writing |
| **@devops (Gage)** | Git operations, CI/CD execution, deployment scripts |

---

## Task-Based Overrides

Some tasks within an agent's scope may require a different model than the agent's default:

### Escalation to Opus (regardless of agent default)

- QA Gate **verdict decisions** (PASS/FAIL/CONCERNS) — architectural implications
- Any task involving **design decisions** or **pattern selection**
- **Spec Pipeline** critique phase (Phase 5)
- **Brownfield Discovery** architectural assessment (Phase 1)
- Bug triage when root cause is **architectural**
- Story creation from PRD (complex requirements interpretation)

### Downgrade to Haiku (regardless of agent default)

- File operations (read, write, search)
- Running test suites
- Git status checks and simple commits
- Formatting and linting fixes
- Boilerplate code generation
- Documentation formatting (not content creation)

---

## Implementation: Agent Activation Protocol

### Step 1: Model Detection

On agent activation, determine the current model. The model in use is stated in the system prompt (e.g., "You are powered by the model named Haiku 4.5").

### Step 2: Compare Against Mapping

Look up the agent ID in the Lookup Table above and compare with current model.

### Step 3: Display Warning or Confirmation

**If model matches:**
```
Model: opus (recommended) ✓
```

**If model DOES NOT match:**
```
==============================================================
  MODEL MISMATCH DETECTED
  Current: haiku | Required: opus
  Please switch: /model opus
==============================================================
```

### Step 4: Proceed with Greeting

Display the standard agent greeting AFTER the model check.

---

## Implementation: Workflow Orchestration

When @aios-master or any orchestrator manages multi-agent workflows:

1. **Start workflow planning** in Opus (orchestrator's own model)
2. **Delegate implementation tasks** to subagents with `model: "haiku"`
3. **Delegate review tasks** to subagents with `model: "sonnet"`
4. **Return to Opus** for verdict decisions and next-step planning

### Example Orchestration Pattern

```
# Phase 1: Planning (Opus - orchestrator)
→ Read story, analyze requirements, plan approach

# Phase 2: Implementation (Haiku - via Task tool)
Task(prompt="implement feature X", model="haiku", subagent_type="Bash")

# Phase 3: Review (Sonnet - via Task tool)
Task(prompt="review implementation", model="sonnet", subagent_type="general-purpose")

# Phase 4: Verdict (Opus - orchestrator returns)
→ Analyze review results, make PASS/FAIL decision
```

---

## Cost Optimization Guide

| Scenario | Model | Rationale |
|----------|-------|-----------|
| Quick bug fix (known solution) | Haiku | No reasoning needed, just execution |
| Feature implementation (story tasks) | Haiku | Coding is mechanical when story is well-defined |
| Code review (patterns, quality) | Sonnet | Needs analysis but not deep strategy |
| QA Gate verdict | Opus | Critical decision with downstream impact |
| Story creation | Opus | Prevents rework — investment upfront saves time |
| Architecture decision | Opus | Wrong decisions here are expensive to fix |
| Simple refactoring | Haiku | Mechanical transformation |
| Complex refactoring | Sonnet | Needs understanding of impact |
| Exploring codebase | Haiku | Fast searches, no deep reasoning needed |
| Writing documentation content | Sonnet | Needs good writing quality |
| Formatting documentation | Haiku | Mechanical task |

---

## Anti-Patterns

- **DON'T** use Opus for writing boilerplate code (waste of capability and budget)
- **DON'T** use Haiku for QA verdicts (may miss architectural issues — costs more in rework)
- **DON'T** use Haiku for story creation (poorly written stories cause rework downstream)
- **DON'T** use Opus for running tests or git operations (overkill)
- **DON'T** ignore the model mismatch warning (leads to suboptimal results)
- **DON'T** skip the `model` parameter in Task tool calls (defeats the optimization)

---

## Technical Limitations

### What IS Automatic
- Task tool `model` parameter — fully automatic when orchestrating
- Model mismatch detection and warning banner — automatic on activation
- Model recommendation in agent greeting footer — always displayed

### What Requires User Action
- Switching model via `/model {name}` command — Claude Code limitation
- Claude Code does not expose a programmatic model-switching API within a conversation
- The agent greeting prominently reminds the user, but cannot force the switch

---

*AIOS Model Selection Rules v1.1 — 2026-02-24*
