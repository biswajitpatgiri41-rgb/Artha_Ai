"""Metadata contract for a future verified official policy-document library."""
from datetime import date
from pydantic import BaseModel, Field, HttpUrl


class OfficialPolicyDocument(BaseModel):
    publisher: str = Field(min_length=1, max_length=200)
    document_title: str = Field(min_length=1, max_length=500)
    publication_date: date
    source_url: HttpUrl
    document_version: str = Field(min_length=1, max_length=100)
    checksum: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
