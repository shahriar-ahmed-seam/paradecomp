"""Critic-gated verification and cross-source consensus evaluation."""

from paradecomp.critic.verifier import (
    CriticGatedVerifier,
    deduplicate_evidence,
)

__all__ = [
    "CriticGatedVerifier",
    "deduplicate_evidence",
]
