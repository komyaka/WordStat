# STATUS.md — Task Tracking

> This file is the **single source of truth** for the current task.
> All agents read from and write to designated sections only.
> Orchestrator maintains the top-level log and makes all routing decisions.

---

## Task

**Description:** Провести глубокий анализ приложения WordStat, исправить визуальные и UX-недочёты, убедиться в работоспособности всех функций и кнопок, улучшить внешний вид и устранить утечки/ошибки.

**Started:** 2026-02-26T11:40:30.350Z

**Branch:** copilot/fix-code-quality-issues

---

## Active Agent Chain

Fast path not applicable. Routing via bug/UX investigation → design → implementation → audit.

```
[x] Orchestrator
[x] Issue Analyst      — trigger: unclear failures/UX issues
[ ] Architect          — trigger: multi-area UX/design changes
[ ] Coder
[ ] QA                 — trigger: behaviour change needs regression tests
[ ] Security           — trigger: none
[ ] Performance        — trigger: none
[ ] DX-CI              — trigger: none
[ ] Docs               — trigger: none
[ ] Refactor           — trigger: none
[x] Auditor            — always last
```

---

## SCOPE

_[Filled by Architect or Orchestrator for Fast-path]_

**In scope:**
- Анализ UX/дизайна и исправление выявленных проблем
- Проверка и починка неработающих кнопок/функций
- Улучшения внешнего вида в рамках имеющегося UI

**Out of scope:**
- Добавление новых крупных функций или внешних зависимостей
- Изменения производительности вне UX-задач

**Affected modules/files:**
- app.py (threading, config save)
- ui/main_window.py (UI callbacks, settings, export)
- engine/parser.py (UI callback threading)
- engine/export/excel_exporter.py (export modes reachability)

---

## DESIGN

_[Filled by Architect]_

### Architecture
_[Description + diagrams]_

### Acceptance Criteria
- [ ] AC-01: 
- [ ] AC-02: 

### Run / Test Commands
```bash
# Build
# Test
```

### Design Status
```
STATUS: IN_PROGRESS
AGENT: architect
PHASE: design
TIMESTAMP: 
```

---

## TEST PLAN

_[Filled by QA agent if triggered]_

### Acceptance Criteria → Test Mapping
| AC | Test ID | Test Name | Type |
|---|---|---|---|
| | | | |

### Edge Cases
| Scenario | Expected Behaviour |
|---|---|
| | |

### Test Plan Status
```
STATUS: IN_PROGRESS
AGENT: qa
PHASE: test-plan
TIMESTAMP: 
```

---

## IMPLEMENTATION

_[Filled by Coder]_

### Changes Made
| File | Change Type | Description |
|---|---|---|
| | | |

### Test Results
```
(paste test output)
```

### Acceptance Criteria Status
- [ ] AC-01: 
- [ ] AC-02: 

### Implementation Status
```
STATUS: IN_PROGRESS
AGENT: coder
PHASE: implementation
TIMESTAMP: 
```

---

## SECURITY REVIEW

_[Filled by Security agent if triggered]_

### Findings
_None_

### Security Review Status
```
STATUS: IN_PROGRESS
AGENT: security
PHASE: security-review
TIMESTAMP: 
```

---

## PERF REVIEW

_[Filled by Performance agent if triggered]_

### Findings
_None_

### Perf Review Status
```
STATUS: IN_PROGRESS
AGENT: performance
PHASE: perf-review
TIMESTAMP: 
```

---

## BUILD/CI

_[Filled by DX-CI agent if triggered]_

### Changes Made
| File | Change | Reason |
|---|---|---|
| | | |

### Build/CI Status
```
STATUS: IN_PROGRESS
AGENT: dx-ci
PHASE: build-ci
TIMESTAMP: 
```

---

## DOCS

_[Filled by Docs agent if triggered]_

### Changes Made
| File | Change | Description |
|---|---|---|
| | | |

### Docs Status
```
STATUS: IN_PROGRESS
AGENT: docs
PHASE: documentation
TIMESTAMP: 
```

---

## REFACTOR

_[Filled by Refactor agent if triggered]_

### Changes Made
| File | Pattern Applied | Description |
|---|---|---|
| | | |

### Refactor Status
```
STATUS: IN_PROGRESS
AGENT: refactor
PHASE: refactor
TIMESTAMP: 
```

---

## REPRO

### Environment
- OS: Linux (container)
- Language version: Python 3.12.3
- Dependency versions: customtkinter 5.2.0, requests 2.31.0, pandas 2.1.4, numpy 1.24.3, scikit-learn 1.3.2, openpyxl 3.1.2 (others from requirements.txt as needed)
- Config: GUI app launched via `python main.py` (requires display)

### Steps to Reproduce
1. Launch UI: `python main.py`.
2. Issue A (cache settings): open ⚙️ Настройки → change “Режим кэша” to `off` and “TTL кэша” to `1`, start/close the app, re-open config — values revert to defaults and cache stays enabled.
3. Issue B (parsing run): enter any seeds (e.g., `test\nexample`), click “▶ Запуск”; parsing thread starts and immediately pushes UI updates from the background thread → Tkinter throws cross-thread errors/hangs; status/stat cards freeze.
4. Issue C (exports): after parsing, try to export PPC/content variants — only one “📊 Экспорт” button exists and always writes SEO-core; PPC/content exporters are unreachable.

### Expected Behaviour
- Cache mode/TTL fields persist to config and affect `WordstatCache`/request behaviour.
- UI updates (status, stats, tables, AI results) run safely without Tkinter thread errors; parsing/AI threads should not crash or freeze UI.
- Export controls allow choosing SEO/PPC/Content outputs matching `ExcelExporter` modes.

### Actual Behaviour
- Cache UI fields are ignored: `config.json` keeps default `cache.mode=on`/`ttl_days=7`, cache never toggles.
- Parsing/AI threads call Tk widgets directly from worker threads, causing `_tkinter.TclError`/frozen UI during status/stat updates.
- Export button always calls SEO export; PPC/content functions in `ExcelExporter` are dead code from the UI.

### Repro Confidence
CONFIRMED

---

## ROOT CAUSE

### Primary Hypothesis
- **File:** `app.py` (thread start around lines 271-294) → `engine/parser.py` (`start()` UI callback around lines 399-412) → `ui/main_window.py` (`update_stats` around lines 735-749)
- **Mechanism:** Parser/AI threads invoke UI callbacks from background threads; Tkinter widgets are mutated outside the main thread, which is not thread-safe, leading to Tk errors or frozen UI during parsing/AI updates.
- **Evidence:** `_parser_thread_wrapper` spawns a non-daemon thread that calls `parser.start()`, which calls `ui_callback` inside the worker loop; `update_stats` performs direct Tk widget updates. Tkinter documentation requires all widget calls on the main loop thread.

### Alternative Hypotheses
| # | Location | Mechanism | Probability |
|---|---|---|---|
| 1 | `ui/main_window.py` get/set_settings (~lines 833-929) & `app.py` `_save_config_from_ui` (lines 202-225) | Cache controls (`settings_cache_mode`, `settings_cache_ttl`) are never read/saved/applied, so cache mode/TTL UI is inert. | HIGH |
| 2 | `ui/main_window.py` `_on_export` (lines 665-675) & button setup (lines 213-223) vs `app.py` `_on_ui_export` (lines 356-373) | UI always passes mode `'seo'`; there is no selector/button for PPC/Content, leaving two exporter modes unreachable (dead feature). | HIGH |

### Fix Strategy
- Route all UI updates through the Tk main thread (e.g., `MainWindow.after` callbacks or thread-safe queue) for parser/AI status/table/stat updates; remove direct widget calls from worker threads.
- Persist cache settings: include cache mode/TTL in `get_settings`/`set_settings`, write them into config in `_save_config_from_ui`, and propagate to `WordstatCache`/API behaviour.
- Add explicit export mode selection (separate buttons or dropdown) to pass `'seo' | 'ppc' | 'content'` into `_on_ui_export`.

### Root Cause Status
STATUS: VERIFIED
AGENT: issue-analyst
PHASE: root-cause
TIMESTAMP: 2026-02-26T11:46:07+00:00
DETAILS: UI updated from background threads, cache settings ignored, PPC/content export unreachable.

---

## RUN/TEST COMMANDS
- Run UI: `python main.py` (GUI, requires display)
- Smoke tests: `python tests/comprehensive_verification.py`
- Parameter parsing tests: `python tests/test_safe_parsing.py`
- Clipboard/filter/UI wiring tests: `python tests/test_fixes.py`
- Final UX fixes verification: `python tests/final_verification.py`

---

## RISKS
- Moving UI updates to the main thread may require refactoring async flows; ensure parser/AI progress indicators stay responsive.
- Enabling cache toggles/TTL could change API load behaviour; validate defaults and backward compatibility of `config.json`.
- Adding export mode selection impacts UX layout; ensure existing SEO export remains one-click.

---

## AUDIT

_[Filled by Auditor — always last]_

### Summary
| Category | Result | Notes |
|---|---|---|
| Acceptance Criteria Coverage | IN_PROGRESS | |
| Test Quality | IN_PROGRESS | |
| Code Correctness | IN_PROGRESS | |
| Security Basics | IN_PROGRESS | |
| Build & Test Execution | IN_PROGRESS | |
| Write-Zone Compliance | IN_PROGRESS | |
| STATUS.md Integrity | IN_PROGRESS | |

### Defects
_None yet_

### Audit Status
```
STATUS: IN_PROGRESS
AGENT: auditor
PHASE: audit
TIMESTAMP: 
```

---

## Orchestrator Log

| Timestamp | Event |
|---|---|
| 2026-02-26T11:40:30.350Z | Task started |
| 2026-02-26T11:46:07+00:00 | Issue Analyst completed root-cause analysis |
