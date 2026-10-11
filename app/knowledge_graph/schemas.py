from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field, model_validator


class RelationshipEvidenceType(StrEnum):
    HYPOTHESIZED = "hypothesized"
    DOCUMENT_SUPPORTED = "document-supported"
    MODEL_ESTIMATED = "model-estimated"
    CAUSALLY_IDENTIFIED = "causally identified"


class KnowledgeGraphEvidence(BaseModel):
    source_title: str = Field(min_length=1, max_length=300)
    source_url: str = Field(min_length=1, max_length=2000)
    citation: str = Field(min_length=1, max_length=500)
    checksum: str | None = None


class EconomicRelationship(BaseModel):
    source_entity: str = Field(min_length=1, max_length=150)
    relation: str = Field(min_length=1, max_length=200)
    target_entity: str = Field(min_length=1, max_length=150)
    evidence_type: RelationshipEvidenceType
    evidence: list[KnowledgeGraphEvidence] = Field(min_length=1)
    coefficient: float | None = None
    model_version: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_claim_level(self) -> "EconomicRelationship":
        if self.evidence_type != RelationshipEvidenceType.MODEL_ESTIMATED and self.coefficient is not None:
            raise ValueError("Numerical coefficients are only valid for model-estimated relationships")
        if self.evidence_type == RelationshipEvidenceType.CAUSALLY_IDENTIFIED and not self.model_version:
            raise ValueError("Causally identified relationships require a model/version reference")
        return self
