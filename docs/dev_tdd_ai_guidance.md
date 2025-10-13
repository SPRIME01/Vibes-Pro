# AI Guidance Fabric TDD Implementation Plan

**Status**: Draft (Pre-implementation)
**Last Updated**: 2025-10-13

---

## Overview

This plan drives the TDD execution for the "AI guidance fabric" defined in DEV-ADR-018 and DEV-PRD-018. The goal is to iteratively deliver temporal pattern recommendations, performance advisories, and context scoring improvements with verifiable tests at each phase. All work must follow the Red → Green → Refactor cycle, with traceability to telemetry governance requirements.

---

## Phase 1: Temporal pattern mining foundation ☐ Planned

**Specs**: DEV-ADR-018, DEV-PRD-018, DEV-SDS-021 (to be authored)
**Focus**: Extend `ArchitecturalPatternRecognizer` to mine temporal DB snapshots and emit recommendation artifacts.

### Requirements
- Snapshot historical ADRs, work summaries, and success metrics from redb.
- Generate `pattern_recommendation` records with confidence, provenance, and temporal metadata.
- Provide CLI smoke command (`just ai-advice --dry-run`) that surfaces mock recommendations for verification.

### Test Plan (Red → Green → Refactor)
- 🔴 `tests/temporal/test_pattern_recommendations.py` fails because `pattern_recommendation` table and exporter do not exist.
- 🟢 Implement ingestion, clustering, and persistence modules; rerun tests until green.
- ♻️ Extract shared utilities for vectorization/confidence scoring; ensure lint + type checks clean.

### Exit Criteria
- All new Python unit tests pass locally and in CI.
- CLI smoke command outputs at least one high-confidence recommendation referencing source ADR.
- Temporal data retention guards verified via unit tests (`retention_days` respected).

---

## Phase 2: Performance advisory heuristics ☐ Planned

**Specs**: DEV-ADR-018, DEV-PRD-018, DEV-SDS-022 (to be authored)
**Focus**: Expand `PerformanceMonitor` to compute baseline deltas and publish advisories.

### Requirements
- Persist baseline latency metrics per workflow and compute rolling comparisons.
- Trigger `performance_advisory` artifacts when regressions exceed configured thresholds.
- Expose advisories via Node API consumed by CLI/chat surfaces.

### Test Plan (Red → Green → Refactor)
- 🔴 `tests/perf/test_performance_advisories.spec.ts` fails (missing advisory generation).
- 🟢 Implement baseline storage, delta calculations, and advisory publishing; ensure test passes.
- ♻️ Add regression coverage for percentile thresholds and serialization edge cases.

### Exit Criteria
- Advisory tests pass with deterministic fixtures.
- Telemetry sanitization validated via `tests/security/test_temporal_opt_out.py` for opt-out flows.
- Metrics exported through OpenTelemetry verified using snapshot tests.

---

## Phase 3: Context scoring integration ☐ Planned

**Specs**: DEV-ADR-018, DEV-PRD-018, DEV-SDS-021/022
**Focus**: Update `AIContextManager` to weight context sources using temporal success and confidence scores.

### Requirements
- Introduce weighting coefficients configurable via `ai_context.config.json`.
- Ensure bundle assembly respects token budget while prioritizing high-confidence assets.
- Surface rationale metadata (confidence, provenance) alongside each selected context snippet.

### Test Plan (Red → Green → Refactor)
- 🔴 `tests/context/test_context_manager_scoring.spec.ts` fails (weights not applied).
- 🟢 Implement scoring adjustments and metadata propagation; confirm test passes.
- ♻️ Refactor scoring utilities for reuse and document coefficient tuning strategy.

### Exit Criteria
- Context bundle generation tests pass with deterministic fixture sets.
- Token budget compliance validated via existing evaluation harness (DEV-SDS-009).
- Rationale metadata exposed in CLI output verified by integration test.

---

## Phase 4: Feedback loop & delivery surfaces ☐ Planned

**Specs**: DEV-ADR-018, DEV-PRD-018
**Focus**: Close the loop with developer feedback capture and multi-surface delivery (CLI, VS Code task, chat response adapters).

### Requirements
- Record accept/dismiss events from CLI/chat interactions and adjust confidence scores accordingly.
- Provide `just ai-advice` command with options to accept/dismiss suggestions.
- Ensure VS Code task + chat surfaces display confidence, provenance, and advisory text consistently.

### Test Plan (Red → Green → Refactor)
- 🔴 `tests/cli/test_ai_advice_command.sh` fails because CLI command not implemented.
- 🟢 Implement CLI, chat adapters, and feedback persistence; tests pass.
- ♻️ Harden UX (color coding, markdown tables) and add regression coverage for opt-out flows.

### Exit Criteria
- CLI/VS Code integration tests pass with mocked data providers.
- Feedback events reflected in temporal DB and observable via snapshot test.
- Documentation updated (`docs/dev_prd.md`, `docs/dev_adr.md`) to reflect delivered surfaces.

---

## Testing Strategy Summary

### Python (Temporal mining)
- Location: `temporal_db/tests/*.py`
- Framework: `pytest` with hypothesis for clustering edge cases.
- Coverage Targets: ≥90% branch coverage on recommendation generator modules.

### TypeScript / Node (Performance + Context)
- Location: `vibespro/src/**/*.spec.ts`
- Framework: `vitest` (existing harness) using fake telemetry fixtures.
- Coverage Targets: ≥85% statements/functions across scoring modules.

### Shell / CLI Integration
- Location: `tests/cli/*.sh`
- Framework: Bats-like assertions using `node --test` wrappers per DEV-SPEC-001.
- Focus: CLI exit codes, markdown output, opt-out flag behavior.

### Telemetry & Governance
- Use OpenTelemetry test collectors to validate emitted metrics/spans (`tests/perf/test_otlp_metrics.rs` TBD).
- Ensure anonymization by comparing stored payloads against hash expectations.

---

## Traceability & Governance

- **ADR**: DEV-ADR-018
- **PRD**: DEV-PRD-018
- **Design Specs**: DEV-SDS-021/022 (pending)
- **Evaluation Hooks**: DEV-SDS-009 (existing)
- **Governance**: Align with forthcoming DEV-SPEC-012 (temporal data governance) — to be authored alongside Phase 1.

---

## Operational Notes

- Phases should ship in order; do not start Phase 3 until Phase 2 telemetry is validated.
- Each phase requires update to this document reflecting completion status and linking to work summaries.
- Add CI job `just test-ai-guidance` once Phase 2 lands to aggregate suites across languages.

