"""Planner agent.

The planner converts a user question into a :class:`ResearchPlan`.  It uses
the NVIDIA reasoning model to generate the plan.  The planner does not
answer the question – it only produces a structured plan that can be fed
to downstream agents.

The implementation is intentionally lightweight: it builds a prompt that
asks the LLM to output JSON matching the :class:`ResearchPlan` schema.
The function validates the output and returns the parsed model.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict

from pydantic import ValidationError

from ..core.llm import request_model
from .schemas import ResearchPlan

# The model name is taken from the environment via the llm module.
from ..core.config import get_settings

_REASONING_MODEL = get_settings().nvidia_reasoning_model


def _build_prompt(question: str) -> list[dict[str, str]]:
    """Return a chat prompt that asks for a ResearchPlan JSON.

    The system message instructs the model to output only the JSON object
    without any additional text.  The user message contains the question.
    """

    system = (
        "You are a research planner for monetary policy.  Convert the user"
        " question into a JSON object that matches the ResearchPlan schema."
        " Do not provide any explanation or additional text."
    )
    user = f"Question: {question}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _parse_json(text: str) -> Dict[str, Any]:
    """Extract JSON from the LLM response.

    The LLM may wrap the JSON in code fences or add stray text.  This
    helper attempts to locate the first JSON object and parse it.
    """

    # Remove code fences if present
    text = re.sub(r"```.*?\n", "", text, flags=re.S)
    # Find the first { ... } block
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(match.group(0))


async def run_planner(question: str) -> ResearchPlan:
    """Generate a :class:`ResearchPlan` for the given question.

    The function validates the output against the schema and raises a
    :class:`ValueError` if validation fails.
    """

    messages = _build_prompt(question)
    start = time.time()
    raw = request_model(
        model=_REASONING_MODEL,
        messages=messages,
        temperature=0.0,
        max_tokens=800,
    )
    duration = time.time() - start
    try:
        data = _parse_json(raw)
        plan = ResearchPlan(**data)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:  # pragma: no cover - LLM failure
        raise ValueError(f"Planner failed to produce valid plan: {exc}") from exc
    # Attach execution metadata if needed – not required by spec
    return plan
