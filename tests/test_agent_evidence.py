from app.agents.critic_agent import run_critic
from app.agents.report_agent import run_report
from app.agents.schemas import AgentAnalysis, AgentEvidence, PolicyAnalysis
from app.evidence.schemas import EvidenceFormat, RetrievedEvidence, RetrievedEvidenceLocation


def _analysis() -> AgentAnalysis:
    return AgentAnalysis(
        summary="Analysis",
        findings=[],
        evidence=[],
        uncertainties=[],
        missing_data=[],
        recommended_next_steps=[],
    )


def _policy() -> PolicyAnalysis:
    return PolicyAnalysis(
        stance="hold",
        options=[],
        confidence=0.5,
        evidence=[AgentEvidence(claim="Headline CPI informs the policy stance", source="MoSPI")],
        assumptions=[],
        warnings=[],
    )


def test_critic_accepts_boolean_plan_flag_and_cpi_policy_evidence() -> None:
    result = run_critic(
        planner_output={"requires_scenario": False},
        data_output={},
        growth_output={},
        external_output={},
        econometrics_output={},
        policy_output={"evidence": [{"series_id": "cpi_headline", "claim": "Headline CPI"}]},
    )

    assert result.status == "PASS"
    assert result.issues == []


def test_report_includes_document_citations_and_stable_sources() -> None:
    evidence = RetrievedEvidence(
        evidence_id="evidence-1",
        filename="cpi-note.pdf",
        format=EvidenceFormat.PDF,
        location=RetrievedEvidenceLocation(page=3),
        excerpt="Headline CPI reference",
        run_id="00000000-0000-0000-0000-000000000001",
    )
    analysis = _analysis()
    report = run_report({}, {}, analysis, analysis, {}, _policy(), {"issues": []}, [evidence])

    assert "cpi-note.pdf" in report.executive_summary
    assert "page 3" in report.executive_summary
    assert report.sources == ["MoSPI", "cpi-note.pdf (doc)"]
