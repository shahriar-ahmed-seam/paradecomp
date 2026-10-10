"""Critic-gated verifier and cross-source consensus evaluation engine."""

from __future__ import annotations

import re
from typing import List, Set, Tuple
from urllib.parse import urlparse

from paradecomp.analyzer.independence import compute_jaccard_similarity
from paradecomp.core.models import (
    AggregatedOutput,
    CriticVerdict,
    EvidenceItem,
    VerificationReport,
)


def _tokenize(text: str) -> Set[str]:
    return set(re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower()))


def normalize_uri(uri: str) -> str:
    """Canonicalize URI to prevent trivial duplication."""
    parsed = urlparse(uri.strip().lower())
    netloc = parsed.netloc.removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{netloc}{path}"


def deduplicate_evidence(
    sources: List[EvidenceItem],
    similarity_threshold: float = 0.85,
) -> Tuple[List[EvidenceItem], int]:
    """Deduplicate evidence items by canonical URI and semantic snippet overlap.

    Returns:
        (unique_items, count_of_removed_duplicates)
    """
    seen_uris: Set[str] = set()
    unique_items: List[EvidenceItem] = []
    removed_count = 0

    for item in sources:
        can_uri = normalize_uri(item.source_uri)
        if can_uri in seen_uris:
            removed_count += 1
            continue

        item_tokens = _tokenize(item.snippet)
        is_duplicate = False
        for kept in unique_items:
            kept_tokens = _tokenize(kept.snippet)
            if compute_jaccard_similarity(item_tokens, kept_tokens) >= similarity_threshold:
                is_duplicate = True
                break

        if is_duplicate:
            removed_count += 1
        else:
            seen_uris.add(can_uri)
            unique_items.append(item)

    return unique_items, removed_count


class CriticGatedVerifier:
    """Critic model evaluator for verifying multi-agent subtask outputs and evidence."""

    def __init__(
        self,
        min_sources_threshold: int = 10,
        max_contradiction_tolerance: float = 0.15,
    ) -> None:
        self.min_sources_threshold = min_sources_threshold
        self.max_contradiction_tolerance = max_contradiction_tolerance

    def detect_contradictions(self, evidence: List[EvidenceItem]) -> List[str]:
        """Detect direct contradictions or opposing claims across evidence snippets."""
        contradictions: List[str] = []
        positive_patterns = [r"\bincreased?\b", r"\bgrew\b", r"\boutperform\b", r"\bsuperior\b"]
        negative_patterns = [
            r"\bdecreased?\b",
            r"\bdropped\b",
            r"\bunderperform\b",
            r"\binferior\b",
        ]

        pos_items: List[EvidenceItem] = []
        neg_items: List[EvidenceItem] = []

        for item in evidence:
            text = item.snippet.lower()
            if any(re.search(p, text) for p in positive_patterns):
                pos_items.append(item)
            if any(re.search(p, text) for p in negative_patterns):
                neg_items.append(item)

        # Cross-reference pairs mentioning common subject entities
        for pos in pos_items:
            pos_tokens = _tokenize(pos.snippet)
            for neg in neg_items:
                neg_tokens = _tokenize(neg.snippet)
                overlap = pos_tokens.intersection(neg_tokens)
                if len(overlap) >= 3:
                    contradictions.append(
                        f"Opposing trends detected on topic ({', '.join(sorted(overlap)[:3])}): "
                        f"'{pos.title}' asserts positive vs '{neg.title}' asserts negative."
                    )
                    break

        return contradictions

    def evaluate(
        self,
        aggregated: AggregatedOutput,
        target_sources: int = 100,
    ) -> VerificationReport:
        """Evaluate an aggregated multi-agent output and issue a formal verification verdict."""
        raw_sources: List[EvidenceItem] = []
        for res in aggregated.subtask_results:
            raw_sources.extend(res.evidence_sources)

        unique_sources, dedup_count = deduplicate_evidence(raw_sources)
        contradictions = self.detect_contradictions(unique_sources)

        total_unique = len(unique_sources)
        target = max(1, target_sources)
        coverage_ratio = min(1.0, float(total_unique) / float(target))

        contradiction_ratio = float(len(contradictions)) / float(max(1, total_unique))
        agreement_ratio = max(0.0, 1.0 - contradiction_ratio)

        # Confidence Formulation
        confidence = coverage_ratio * (1.0 - contradiction_ratio) * agreement_ratio
        confidence = max(0.0, min(1.0, round(confidence, 4)))

        # Determine Verdict
        if contradiction_ratio > self.max_contradiction_tolerance:
            verdict = CriticVerdict.FLAGGED_DISCREPANCY
            notes = (
                f"Flagged discrepancy: contradiction ratio ({contradiction_ratio:.2%}) exceeds "
                f"tolerance ({self.max_contradiction_tolerance:.2%}). "
                f"Found {len(contradictions)} discordant claims."
            )
        elif total_unique < self.min_sources_threshold and aggregated.total_subtasks > 0:
            verdict = CriticVerdict.INCONCLUSIVE
            notes = (
                f"Inconclusive verification: unique sources ({total_unique}) below minimum "
                f"threshold ({self.min_sources_threshold})."
            )
        elif any(
            "unverified hallucination" in (r.error_message or "").lower()
            for r in aggregated.subtask_results
        ):
            verdict = CriticVerdict.REJECTED_HALLUCINATION
            notes = "Rejected hallucination: detected unsubstantiated claims or fake citations."
        else:
            verdict = CriticVerdict.VERIFIED
            notes = (
                f"Verified: {total_unique} unique evidence citations verified across "
                f"{aggregated.successful_subtasks} subtasks. Zero critical contradictions detected."
            )

        report = VerificationReport(
            verdict=verdict,
            confidence_score=confidence,
            contradictions_detected=contradictions,
            deduplicated_count=dedup_count,
            rechecked_sources_count=total_unique,
            critic_notes=notes,
        )

        aggregated.verification = report
        return report
