# ParaDecomp System Architecture

This document provides the formal architecture specification for the ParaDecomp runtime, decomposition engine, and critic verification harness.

---

## 1. Architectural Philosophy: Task-Orthogonal Concurrency

ParaDecomp rejects the human roleplay model (Planner -> Coder -> QA) in favor of task-orthogonal concurrency:

```mermaid
flowchart TD
    subgraph ANTIPATTERN["Role-Specialization Antipattern (Sequential Chat)"]
        P["Planner Persona"] -->|"Lossy Summary"| C["Coder Persona"]
        C -->|"Lossy Diff"| Q["QA Reviewer Persona"]
        Q -->|"Retry Loop"| P
    end

    subgraph INVARIANT["ParaDecomp Invariant (Parallel Orthogonality)"]
        M["Master Agent"] -->|"Orthogonal Contracts"| W1["Sub-Agent 1"]
        M -->|"Orthogonal Contracts"| W2["Sub-Agent 2"]
        M -->|"Orthogonal Contracts"| W3["Sub-Agent 3"]
        W1 & W2 & W3 --> RED["Structured Reducer"]
        RED --> CRIT["Independent Critic"]
    end
```

---

## 2. Subsystem Dataflow

The execution cycle moves through four deterministic stages:

```mermaid
sequenceDiagram
    participant User as Orchestrator / User
    participant Analyzer as IndependenceAnalyzer
    participant Runtime as ElasticRuntime
    participant Workers as N Concurrent Workers
    participant Critic as CriticGatedVerifier

    User->>Analyzer: Submit TaskObjective + Facets
    Analyzer->>Analyzer: Compute S_overlap, C(Ti, Tj), O(P)
    alt Orthogonality >= 0.70
        Analyzer-->>Runtime: Gated as PARALLEL_FAN_OUT
        Runtime->>Workers: Dispatch N SubtaskContracts (async)
        Workers-->>Runtime: SubtaskExecutionResults (~300 sources)
        Runtime->>Critic: AggregatedOutput Reduction
        Critic->>Critic: Deduplicate URIs & Detect Contradictions
        Critic-->>User: Verified Synthesis & Confidence Score
    else Orthogonality < 0.70
        Analyzer-->>Runtime: Gated as MONOLITHIC_SERIAL
        Runtime-->>User: Execute in unified single-agent context
    end
```

---

## 3. Failure Mode Analysis and Mitigation Matrix

| Failure Mode | Root Cause Mechanism | Runtime Detection | Mitigation Strategy |
|---|---|---|---|
| **Cyclic Dependency Deadlock** | Misconfigured subtask dependency declarations ($T_a \to T_b \to T_a$) | `topological_sort_waves` in-degree cycle detection | Rejects plan with `ValueError`, triggers immediate fallback to serial monolith. |
| **Worker I/O Timeout** | Downstream HTTP endpoint or web crawler hang | `asyncio.wait_for` timeout threshold | Worker isolates error into `SubtaskExecutionResult(status="FAILED")` without crashing the swarm. |
| **Provider Rate Limiting** | Sudden burst of $N$ sub-agents triggering API 429 | Upstream request spike | Token bucket `RateLimiter` enforces strict requests-per-minute throttle and smooths burst intervals. |
| **Hallucinated Citations** | Sub-agent generating unsupported citations or non-existent URLs | Cross-source citation consistency check in Critic | Critic marks verdict as `REJECTED_HALLUCINATION` or `FLAGGED_DISCREPANCY` and lowers confidence. |
| **Semantic Duplication** | Overlapping research queries retrieving identical documents | Token Jaccard overlap on evidence snippets | `deduplicate_evidence` canonicalizes URIs and collapses snippets with $\ge 0.85$ token overlap. |
