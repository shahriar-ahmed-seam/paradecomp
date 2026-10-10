"""Unit tests for CriticGatedVerifier and deduplication logic."""

from paradecomp.core.models import (
    AggregatedOutput,
    CriticVerdict,
    EvidenceItem,
    ExecutionStrategy,
    SubtaskExecutionResult,
)
from paradecomp.critic.verifier import (
    CriticGatedVerifier,
    deduplicate_evidence,
    normalize_uri,
)


def test_normalize_uri():
    assert (
        normalize_uri("https://WWW.Arxiv.org/abs/2401.0001/") == "https://arxiv.org/abs/2401.0001"
    )


def test_deduplicate_evidence():
    item1 = EvidenceItem(
        source_uri="https://arxiv.org/abs/1",
        title="Paper A",
        snippet="Semiconductor packaging advancements using chiplet interconnects.",
    )
    item2 = EvidenceItem(
        source_uri="https://arxiv.org/abs/1",  # duplicate URI
        title="Paper A duplicate",
        snippet="Semiconductor packaging advancements using chiplet interconnects.",
    )
    item3 = EvidenceItem(
        source_uri="https://arxiv.org/abs/2",
        title="Paper B",
        snippet="Sub-nanometer gate oxide scaling limits in FinFETs.",
    )

    unique, removed = deduplicate_evidence([item1, item2, item3])
    assert len(unique) == 2
    assert removed == 1


def test_critic_verifier_verified():
    verifier = CriticGatedVerifier(min_sources_threshold=2)

    topics = [
        "EUV optical train numerical aperture reaches 0.55 in High-NA tools.",
        "Gate-all-around nanosheet architectures replace FinFET transistors at 2nm.",
        "Backside power delivery networks decouple signal routing from power rails.",
        "Direct bonded copper hybrid bonding enables 10um pitch 3D stacking.",
        "Atomic layer deposition of ruthenium liners mitigates electromigration.",
        "Stochastic defect reduction through high-dose chemical amplification resists.",
        "Anamorphic magnification preserves reticle mask compatibility for EUV.",
        "Sub-surface laser annealing optimizes source/drain dopant activation.",
        "Low-k dielectric breakdown prevention via self-assembled monolayers.",
        "Wafer warpage compensation algorithms in advanced packaging lithography.",
        "Dry photoresist processing reduces solvent consumption and line edge roughness.",
        "Cobalt contact metallization lowers series resistance in GAA source-drain.",
        "Through-silicon via aspect ratios scaled to 20:1 for interposer integration.",
        "Cryogenic etch profiles achieve vertical sidewalls in high-aspect oxide holes.",
        "Multi-die interposer testing strategies utilizing built-in self-test circuits.",
    ]
    evidence = [
        EvidenceItem(
            source_uri=f"https://source.org/{i}",
            title=f"Source {i}",
            snippet=topics[i],
        )
        for i in range(15)
    ]
    res = SubtaskExecutionResult(
        subtask_id="st_1",
        worker_id="w_0",
        status="SUCCESS",
        evidence_sources=evidence,
    )
    agg = AggregatedOutput(
        task_id="t1",
        plan_id="p1",
        strategy_used=ExecutionStrategy.PARALLEL_FAN_OUT,
        total_subtasks=1,
        successful_subtasks=1,
        total_sources_gathered=15,
        wall_clock_duration_ms=100.0,
        synthesized_content="Summary of nodes.",
        subtask_results=[res],
    )

    report = verifier.evaluate(agg, target_sources=15)
    assert report.verdict == CriticVerdict.VERIFIED
    assert report.confidence_score > 0.80
    assert report.deduplicated_count == 0


def test_critic_verifier_discrepancy():
    verifier = CriticGatedVerifier(min_sources_threshold=2, max_contradiction_tolerance=0.05)

    ev_pos = EvidenceItem(
        source_uri="https://source.org/pos",
        title="Yield Report 2026",
        snippet="TSMC wafer yield significantly increased for N3P node architectures.",
    )
    ev_neg = EvidenceItem(
        source_uri="https://source.org/neg",
        title="Defect Report 2026",
        snippet="TSMC wafer yield significantly decreased for N3P node architectures.",
    )

    res = SubtaskExecutionResult(
        subtask_id="st_1",
        worker_id="w_0",
        status="SUCCESS",
        evidence_sources=[ev_pos, ev_neg],
    )
    agg = AggregatedOutput(
        task_id="t1",
        plan_id="p1",
        strategy_used=ExecutionStrategy.PARALLEL_FAN_OUT,
        total_subtasks=1,
        successful_subtasks=1,
        total_sources_gathered=2,
        wall_clock_duration_ms=100.0,
        synthesized_content="Summary.",
        subtask_results=[res],
    )

    report = verifier.evaluate(agg, target_sources=2)
    assert report.verdict == CriticVerdict.FLAGGED_DISCREPANCY
    assert len(report.contradictions_detected) > 0
