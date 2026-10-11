from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.data_routes import _file_to_frame
from app.api.main import app


def test_api_responses_include_security_headers() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_validation_errors_do_not_echo_submitted_values() -> None:
    secret_like_input = "do-not-echo-this-value"
    response = TestClient(app).post(
        "/simulate",
        json={"base_inflation": secret_like_input, "horizon_months": 999},
    )

    assert response.status_code == 422
    assert secret_like_input not in response.text


def test_csv_upload_parser_accepts_expected_format() -> None:
    frame = _file_to_frame("series.csv", b"date,value\n2024-01-01,4.2\n")

    assert list(frame.columns) == ["date", "value"]
    assert frame.iloc[0]["value"] == 4.2


def test_excel_upload_rejects_invalid_signature_without_parser_details() -> None:
    with pytest.raises(HTTPException) as error:
        _file_to_frame("series.xlsx", b"not an excel file")

    assert error.value.status_code == 415
    assert error.value.detail == "Excel file signature is invalid."


def test_unsupported_upload_extension_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        _file_to_frame("payload.exe", b"binary")

    assert error.value.status_code == 415
    assert "CSV" in error.value.detail
