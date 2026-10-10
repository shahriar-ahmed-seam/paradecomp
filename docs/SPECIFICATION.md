# ParaDecomp Schema Specification (RFC-PD-001)

This document specifies the canonical data contracts, schema types, and validation invariants governing the ParaDecomp engine.

---

## 1. TaskObjective Schema

Defines the top-level operational mandate dispatched to the orchestrator:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TaskObjective",
  "type": "object",
  "properties": {
    "task_id": { "type": "string", "pattern": "^task_[a-f0-9]+$" },
    "title": { "type": "string", "minLength": 3 },
    "description": { "type": "string", "minLength": 10 },
    "priority": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
    "max_concurrency": { "type": "integer", "minimum": 1, "maximum": 100 },
    "timeout_seconds": { "type": "number", "exclusiveMinimum": 0 },
    "target_sources_count": { "type": "integer", "minimum": 1 }
  },
  "required": ["title", "description"]
}
```

---

## 2. SubtaskContract Schema

Strictly typed operational boundary for worker sub-agents:

```json
{
  "title": "SubtaskContract",
  "type": "object",
  "properties": {
    "subtask_id": { "type": "string" },
    "parent_task_id": { "type": "string" },
    "title": { "type": "string" },
    "query_or_instruction": { "type": "string" },
    "dependencies": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Antecedent subtask IDs. Must be empty for independent scatter-gather tasks."
    },
    "timeout_seconds": { "type": "number", "exclusiveMinimum": 0 },
    "orthogonality_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
    "allocated_tokens": { "type": "integer", "minimum": 1 }
  },
  "required": ["parent_task_id", "title", "query_or_instruction"]
}
```

---

## 3. EvidenceItem Schema

Unit of retrieved empirical evidence:

```json
{
  "title": "EvidenceItem",
  "type": "object",
  "properties": {
    "source_id": { "type": "string" },
    "source_uri": { "type": "string", "format": "uri" },
    "title": { "type": "string" },
    "snippet": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "reliability_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
  },
  "required": ["source_uri", "title", "snippet"]
}
```

---

## 4. Gating Invariants

1. **Orthogonality Invariant**: If $\bar{O}(P) < 0.70$, the orchestrator MUST NOT authorize `PARALLEL_FAN_OUT`.
2. **Acyclicity Invariant**: If directed dependency cycles are detected in topological wave levelization, execution MUST halt and trigger serial recovery.
3. **Consensus Invariant**: Evidence items with canonical URI collision or snippet Jaccard similarity $\ge 0.85$ MUST be collapsed into a single deduplicated entry.
