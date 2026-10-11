from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from app.evidence.schemas import RetrievedEvidence


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class PageMetric(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    value: str = Field(max_length=200)
    source: str = Field(max_length=200)


class PageAssistantContext(BaseModel):
    page: str = Field(min_length=1, max_length=200)
    mode: Literal["mock", "live", "none"]
    visibleMetrics: list[PageMetric] = Field(default_factory=list, max_length=30)
    selectedScenario: dict[str, str | int | float | bool | None] | None = None
    selectedSeries: dict[str, str | int | float | bool | None] | None = None
    warnings: list[str] = Field(default_factory=list, max_length=20)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    page: str = Field(min_length=1, max_length=200)
    page_context: str = Field(min_length=1, max_length=200)
    conversation: list[ConversationMessage] = Field(default_factory=list, max_length=20)
    page_data: PageAssistantContext | None = None
    document_evidence: list[RetrievedEvidence] | None = Field(default=None, max_length=10)
    document_evidence_run_id: str | None = Field(default=None, max_length=36)
    document_evidence_ids: list[str] | None = Field(default=None, max_length=100)

    @field_validator("document_evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, values: list[str] | None) -> list[str] | None:
        if values is not None and any(not re.fullmatch(r"[0-9a-f]{32}", item) for item in values):
            raise ValueError("Invalid evidence ID")
        return values


class AssistantChatResponse(BaseModel):
    answer: str
    page_context: str
    model: str
    warnings: list[str] = Field(default_factory=list)
