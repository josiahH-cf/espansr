"""Deterministic recommendation acceptance checks (ARCH-05, BEH-05, BEH-06, BEH-07).

Recommendations are local, deterministic, and metadata-driven. The required
natural-language searches and artifact combinations below are the acceptance
contract: they must surface the correct capability without the trigger
appearing in the query, using only the real bundled metadata.
"""

from pathlib import Path

from espansr.core.command_catalog import build_command_catalog
from espansr.core.config import Config
from espansr.core.templates import TemplateManager

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"


def _bundled_entries():
    manager = TemplateManager(templates_dir=TEMPLATES_DIR)
    return build_command_catalog(template_manager=manager, config=Config())


def _top_trigger(entries, query, **kwargs):
    from espansr.core.recommend import RecommendationQuery, recommend

    results = recommend(entries, RecommendationQuery(**query), **kwargs)
    assert results, f"no recommendations for {query}"
    return results[0].entry.trigger


# ── BEH-05: recognition over recall ──────────────────────────────────────────


def test_search_challenge_completed_research_surfaces_gaps():
    entries = _bundled_entries()
    assert _top_trigger(entries, {"text": "challenge research that is already complete"}) == ":gaps"


def test_search_visualize_existing_report_surfaces_visual():
    entries = _bundled_entries()
    assert _top_trigger(entries, {"text": "visualize an existing report"}) == ":visual"


def test_search_navigate_research_in_html_surfaces_html_help_doc():
    entries = _bundled_entries()
    assert (
        _top_trigger(entries, {"text": "make this research easy to navigate in HTML"})
        == ":html-help-doc"
    )


def test_search_rough_intent_to_handoff_surfaces_feature():
    entries = _bundled_entries()
    assert (
        _top_trigger(entries, {"text": "turn rough feature intent into an implementation handoff"})
        == ":feature"
    )


# ── BEH-06: artifact compatibility ───────────────────────────────────────────


def test_artifact_evidence_report_to_visual_artifact_surfaces_visual():
    entries = _bundled_entries()
    assert (
        _top_trigger(
            entries, {"have_artifact": "evidence-report", "want_artifact": "visual-artifact"}
        )
        == ":visual"
    )


def test_artifact_evidence_report_to_interactive_html_surfaces_html_help_doc():
    entries = _bundled_entries()
    assert (
        _top_trigger(
            entries, {"have_artifact": "evidence-report", "want_artifact": "interactive-html"}
        )
        == ":html-help-doc"
    )


def test_artifact_gap_review_to_implementation_handoff_surfaces_feature():
    entries = _bundled_entries()
    assert (
        _top_trigger(
            entries,
            {"have_artifact": "gap-review", "want_artifact": "implementation-handoff"},
        )
        == ":feature"
    )


def test_artifact_implemented_feature_to_verification_report_surfaces_verify():
    entries = _bundled_entries()
    assert (
        _top_trigger(
            entries,
            {"have_artifact": "implemented-feature", "want_artifact": "verification-report"},
        )
        == ":verify"
    )


# ── BEH-03: branching recommendations from one artifact ──────────────────────


def test_evidence_report_branches_to_review_visual_and_html():
    """One artifact yields several optional directions, none mandatory."""
    from espansr.core.recommend import RecommendationQuery, recommend

    entries = _bundled_entries()
    results = recommend(entries, RecommendationQuery(have_artifact="evidence-report"))
    triggers = [r.entry.trigger for r in results]
    for expected in (":gaps", ":visual", ":html-help-doc"):
        assert expected in triggers, f"{expected} missing from branch options"


# ── ARCH-05: determinism ─────────────────────────────────────────────────────


def test_identical_inputs_produce_identical_rankings():
    from espansr.core.recommend import RecommendationQuery, recommend

    entries = _bundled_entries()
    query = RecommendationQuery(text="challenge research that is already complete")
    first = [(r.entry.trigger, r.score) for r in recommend(entries, query)]
    second = [(r.entry.trigger, r.score) for r in recommend(entries, query)]
    assert first == second
    # Order-independence of catalog input.
    third = [(r.entry.trigger, r.score) for r in recommend(list(reversed(entries)), query)]
    assert first == third


def test_recommendation_requires_no_network_or_llm():
    """The engine is importable pure-Python with no network client modules."""
    import importlib

    module = importlib.import_module("espansr.core.recommend")
    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("requests", "urllib", "http.client", "socket", "openai", "anthropic"):
        assert forbidden not in source


def test_favorites_and_recents_break_ties_deterministically():
    from espansr.core.recommend import RecommendationQuery, recommend

    entries = _bundled_entries()
    query = RecommendationQuery(have_artifact="context-packet")
    plain = recommend(entries, query)
    boosted = recommend(entries, query, favorites=(":research",))
    assert [r.entry.trigger for r in boosted].index(":research") <= [
        r.entry.trigger for r in plain
    ].index(":research")


# ── BEH-07: full catalog access ──────────────────────────────────────────────


def test_recommendations_never_remove_catalog_entries():
    """Recommendation is a ranking over the catalog, not a gate in front of it."""
    entries = _bundled_entries()
    # The full catalog stays available regardless of any query results.
    triggers = {e.trigger for e in entries}
    assert ":coms" in triggers and ":feature" in triggers
    from espansr.core.recommend import RecommendationQuery, recommend

    results = recommend(entries, RecommendationQuery(text="zzzqqqxyzzy"))
    # A no-match query yields an empty ranking, never an error, and the
    # caller's catalog list is untouched.
    assert results == []
    assert {e.trigger for e in entries} == triggers
