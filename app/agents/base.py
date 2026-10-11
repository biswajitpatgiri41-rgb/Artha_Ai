"""Base LLM agent.

The :class:`BaseAgent` provides a reusable foundation for all future
agents.  It encapsulates the common pattern of:

1. Building a chat prompt.
2. Sending the request to the NVIDIA OpenAI‑compatible endpoint.
3. Extracting a JSON payload from the response.
4. Validating the payload against a Pydantic model.
5. Returning a structured result that includes execution metadata.

The agent deliberately avoids exposing chain‑of‑thought or any
intermediate reasoning.  It only returns the final structured output
along with a status flag and any errors.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from ..core.llm import request_model
from ..core.config import get_settings

T = TypeVar("T", bound=BaseModel)


class AgentResult(BaseModel):
    """Standardised result returned by all agents.

    Attributes
    ----------
    status:
        ``SUCCESS`` or ``FAIL``.
    data:
        The parsed Pydantic model instance or ``None`` on failure.
    errors:
        List of error messages.
    model_name:
        The model used for the request.
    duration:
        Execution time in seconds.
    tool_calls:
        Placeholder for future tool call metadata.
    summary:
        A concise textual summary of the operation.
    """

    status: str
    data: Optional[Any] = None
    errors: List[str] = []
    model_name: Optional[str] = None
    duration: Optional[float] = None
    tool_calls: List[Dict[str, Any]] = []
    summary: Optional[str] = None


class BaseAgent(Generic[T]):
    """Base class for all LLM agents.

    Parameters
    ----------
    schema:
        Pydantic model class that the agent should return.
    system_prompt:
        System message to guide the LLM.
    model_name:
        Optional override of the default reasoning model.
    """

    def __init__(self, schema: Type[T], system_prompt: str, model_name: Optional[str] = None):
        self.schema = schema
        self.system_prompt = system_prompt
        self.model_name = model_name or get_settings().nvidia_reasoning_model

    def _build_prompt(self, user_input: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]

    def _extract_json(self, text: str) -> Dict[str, Any]:
        # Strip code fences
        text = re.sub(r"```.*?\n", "", text, flags=re.S)
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError("No JSON object found in LLM response")
        return json.loads(match.group(0))

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        return request_model(
            model=self.model_name,
            messages=messages,
            temperature=0.0,
            max_tokens=800,
        )

    def run(self, user_input: str) -> AgentResult:
        start = time.time()
        result = AgentResult(status="FAIL", model_name=self.model_name)
        try:
            messages = self._build_prompt(user_input)
            raw = self._call_llm(messages)
            data_dict = self._extract_json(raw)
            data_obj = self.schema(**data_dict)
            result.status = "SUCCESS"
            result.data = data_obj
            result.summary = f"Generated {self.schema.__name__}"
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            result.errors.append(str(exc))
        finally:
            result.duration = time.time() - start
        return result
