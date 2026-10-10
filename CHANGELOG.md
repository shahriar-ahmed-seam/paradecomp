# Changelog

All notable changes to ParaDecomp are documented in this file in adherence to Keep a Changelog standards.

---

## [0.1.0] - 2026-10-10

### Added
- RFC canonical data models (`TaskObjective`, `SubtaskContract`, `DecompositionPlan`, `AggregatedOutput`, `CriticVerdict`).
- Subtask independence analyzer with Jaccard overlap, coupling coefficient, and topological wave levelizer.
- Elastic scatter-gather runtime with token bucket rate limiter, worker timeout isolation, and asynchronous event bus.
- Critic-gated verifier with evidence deduplication, contradiction detector, and confidence scoring.
- Deep Research workload engine scaling from ~30 sources to ~300+ sources.
- Empirical benchmark runner comparing serial agent baseline against N-worker ParaDecomp swarm.
- Ecosystem provider adapters for OpenAI, Anthropic, Gemini, Ollama, and LangChain tool bridge.
- Typer and Rich telemetry CLI suite (`version`, `analyze`, `research`, `benchmark`, `serve`).
- Anti-AI-slop developer telemetry workbench with dark neutral canvas, slim scrollbars, and live SVG chart.
- Publication-grade documentation, Mermaid blueprints, and formal RFC specifications.
