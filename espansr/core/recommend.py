"""Deterministic, local capability recommendations for discovery surfaces.

The engine ranks command-catalog entries against a structured query built from
free text, the artifact the user currently has, and the outcome they want. It
uses only local capability metadata, artifact compatibility, workflow
proximity, favorites, and recency — no LLM, no network, no hosted service —
and identical inputs always produce identical rankings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

from espansr.core.command_catalog import CommandCatalogEntry

# Weights are integers so scores are exact and rankings reproducible.
_WEIGHT_TRIGGER = 40
_WEIGHT_INTENT_TAG = 30
_WEIGHT_NAME = 20
_WEIGHT_ARTIFACT_TOKEN = 10
_WEIGHT_USE_WHEN = 8
_WEIGHT_DESCRIPTION = 6
_WEIGHT_CATEGORY_STAGE = 4
_WEIGHT_ACCEPTS_MATCH = 60
_WEIGHT_PRODUCES_MATCH = 80
_WEIGHT_BOTH_MATCH = 40
_WEIGHT_WORKFLOW_PROXIMITY = 5
_WEIGHT_FAVORITE = 15
_WEIGHT_RECENT_MAX = 10
_PREFIX_MIN_LENGTH = 4

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "easy",
    "for",
    "i",
    "in",
    "into",
    "is",
    "it",
    "make",
    "me",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


@dataclass(frozen=True)
class RecommendationQuery:
    """Structured discovery input."""

    text: str = ""
    have_artifact: str = ""
    want_artifact: str = ""


@dataclass(frozen=True)
class Recommendation:
    """One ranked result with the evidence behind its score."""

    entry: CommandCatalogEntry
    score: int
    reasons: Tuple[str, ...] = field(default_factory=tuple)


def _tokenize(text: str) -> List[str]:
    tokens = re.split(r"[^a-z0-9]+", (text or "").lower())
    return [t for t in tokens if t and t not in _STOPWORDS]


def _tokens_match(query_token: str, field_token: str) -> bool:
    if query_token == field_token:
        return True
    if len(query_token) >= _PREFIX_MIN_LENGTH and field_token.startswith(query_token):
        return True
    if len(field_token) >= _PREFIX_MIN_LENGTH and query_token.startswith(field_token):
        return True
    return False


def _field_hits(query_tokens: Sequence[str], field_text: str) -> int:
    """Count distinct query tokens matched by *field_text*'s tokens."""
    field_tokens = _tokenize(field_text)
    if not field_tokens:
        return 0
    hits = 0
    for query_token in query_tokens:
        if any(_tokens_match(query_token, ft) for ft in field_tokens):
            hits += 1
    return hits


def _text_score(entry: CommandCatalogEntry, query_tokens: Sequence[str]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    trigger_hits = _field_hits(query_tokens, entry.trigger.lstrip(":").replace("-", " "))
    if trigger_hits:
        score += trigger_hits * _WEIGHT_TRIGGER
        reasons.append(f"matches trigger {entry.trigger}")

    tag_hits = _field_hits(query_tokens, " ".join(entry.intent_tags))
    if tag_hits:
        score += tag_hits * _WEIGHT_INTENT_TAG
        reasons.append("matches intent tags")

    name_hits = _field_hits(query_tokens, entry.name)
    if name_hits:
        score += name_hits * _WEIGHT_NAME

    artifact_hits = _field_hits(query_tokens, " ".join((*entry.accepts, *entry.produces)))
    if artifact_hits:
        score += artifact_hits * _WEIGHT_ARTIFACT_TOKEN

    use_hits = _field_hits(query_tokens, entry.use_when)
    if use_hits:
        score += use_hits * _WEIGHT_USE_WHEN

    description_hits = _field_hits(query_tokens, entry.description)
    if description_hits:
        score += description_hits * _WEIGHT_DESCRIPTION

    meta_hits = _field_hits(query_tokens, f"{entry.category} {entry.stage}")
    if meta_hits:
        score += meta_hits * _WEIGHT_CATEGORY_STAGE

    return score, reasons


def _artifact_score(
    entry: CommandCatalogEntry, query: RecommendationQuery
) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    accepts_match = bool(query.have_artifact) and query.have_artifact in entry.accepts
    produces_match = bool(query.want_artifact) and query.want_artifact in entry.produces
    if accepts_match:
        score += _WEIGHT_ACCEPTS_MATCH
        reasons.append(f"accepts {query.have_artifact}")
    if produces_match:
        score += _WEIGHT_PRODUCES_MATCH
        reasons.append(f"produces {query.want_artifact}")
    if accepts_match and produces_match:
        score += _WEIGHT_BOTH_MATCH
    return score, reasons


def _workflow_proximity_score(
    entry: CommandCatalogEntry,
    query: RecommendationQuery,
    entries: Sequence[CommandCatalogEntry],
) -> Tuple[int, List[str]]:
    """Small bonus for sharing a workflow with the producer of the artifact
    the user currently has."""
    if not query.have_artifact or not entry.workflows:
        return 0, []
    producer_workflows = set()
    for other in entries:
        if query.have_artifact in other.produces:
            producer_workflows.update(other.workflows)
    if producer_workflows & set(entry.workflows):
        return _WEIGHT_WORKFLOW_PROXIMITY, ["in a shared process"]
    return 0, []


def recommend(
    entries: Iterable[CommandCatalogEntry],
    query: RecommendationQuery,
    *,
    favorites: Sequence[str] = (),
    recents: Sequence[str] = (),
    workflow_catalog: Optional[object] = None,  # Reserved; membership rides on entries
) -> List[Recommendation]:
    """Rank *entries* against *query*. Returns only entries with a positive
    score, best first; ties break on the trigger for stable output. The input
    catalog is never mutated or filtered — full-catalog access is the caller's
    view to keep."""
    entry_list = list(entries)
    query_tokens = _tokenize(query.text)
    results: List[Recommendation] = []

    for entry in entry_list:
        score = 0
        reasons: List[str] = []

        text_score, text_reasons = _text_score(entry, query_tokens)
        score += text_score
        reasons.extend(text_reasons)

        artifact_score, artifact_reasons = _artifact_score(entry, query)
        score += artifact_score
        reasons.extend(artifact_reasons)

        proximity_score, proximity_reasons = _workflow_proximity_score(entry, query, entry_list)
        score += proximity_score
        reasons.extend(proximity_reasons)

        if score <= 0:
            continue

        if entry.trigger in favorites:
            score += _WEIGHT_FAVORITE
            reasons.append("favorite")
        if entry.trigger in recents:
            score += max(0, _WEIGHT_RECENT_MAX - list(recents).index(entry.trigger))
            reasons.append("recently used")

        results.append(Recommendation(entry=entry, score=score, reasons=tuple(reasons)))

    results.sort(key=lambda r: (-r.score, r.entry.trigger))
    return results
