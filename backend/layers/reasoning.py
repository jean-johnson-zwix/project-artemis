"""
Layer 3 — Reasoning + Explanation

Blocked on Azure keys. Cannot run without AZURE_OPENAI_API_KEY.

Takes a Detection + DetectionContext, calls Azure OpenAI (gpt-4o-mini),
and parses the structured response into an Insight via Pydantic.

After producing the Insight:
  1. Write it to the insights table via db.write_insight()
  2. Call notifications.send_teams_alert(detection, insight)

Prompt engineering notes (see tasks.md for full output schema):
  - System prompt should instruct the model to respond in JSON matching
    the Insight schema: what, why, evidence[], confidence,
    remaining_life_years, recommended_actions[]
  - Pass the full DetectionContext (sensor trend summary, doc snippets,
    parsed inspection values, work order history) as user content
  - Parse response with Insight.model_validate_json() — fail loudly on
    schema mismatch so we catch prompt regressions early
"""

from __future__ import annotations

from models import Detection, DetectionContext, Insight  # noqa: F401


def run_reasoning(detection: Detection, context: DetectionContext) -> Insight:
    """
    Call Azure OpenAI and return a structured Insight.

    Writes the insight to DB and fires the Teams notification before returning.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Sub-task stubs
# ---------------------------------------------------------------------------


def _build_prompt(detection: Detection, context: DetectionContext) -> str:
    """Assemble the user message content for the LLM call."""
    raise NotImplementedError


def _call_azure_openai(prompt: str) -> str:
    """POST to Azure OpenAI chat completion endpoint, return raw text."""
    raise NotImplementedError


def _parse_insight(raw_json: str, detection_id) -> Insight:
    """Parse and validate the LLM response into an Insight model."""
    raise NotImplementedError
