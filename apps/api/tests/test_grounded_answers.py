from hashlib import sha256
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.ai.answers import ClaimCitation, GroundedAnswer, GroundedAnswerValidator
from app.retrieval.evidence import EvidenceItem, EvidencePack
from app.retrieval.planning import QueryLanguage, RetrievalRisk
from app.retrieval.service import CitationReference

CONTENT = "Visa-free entry is permitted for up to 30 days for eligible visitors."


def evidence_pack(*, status: str = "sufficient") -> EvidencePack:
    items = []
    if status == "sufficient":
        items = [
            EvidenceItem(
                chunk_id="chunk-1",
                document_id="document-1",
                document_version_id="version-1",
                title="Official visa guidance",
                heading="Visa-free entry",
                content=CONTENT,
                content_hash=sha256(CONTENT.encode()).hexdigest(),
                retrieval_score=1,
                citations=[
                    CitationReference(
                        source_id=UUID("00000000-0000-0000-0000-000000000001"),
                        locator="Visa-free entry",
                    )
                ],
            )
        ]
    return EvidencePack(
        plan_fingerprint="plan-1",
        evidence_fingerprint=sha256(status.encode()).hexdigest(),
        status=status,
        reason=None if items else "no eligible evidence",
        total_characters=sum(len(item.content) for item in items),
        quarantined_chunk_ids=[],
        items=items,
    )


def answer(**updates) -> GroundedAnswer:
    values = {
        "status": "answered",
        "language": "en",
        "summary": "Eligible visitors may enter without a visa for up to 30 days.",
        "sections": [
            {
                "id": "section-entry",
                "heading": "Entry",
                "claims": [
                    {
                        "id": "claim-visa-free",
                        "text": "Visa-free entry is permitted for up to 30 days.",
                        "citations": [
                            {
                                "evidence_id": "chunk-1",
                                "quote": "Visa-free entry is permitted for up to 30 days",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    values.update(updates)
    return GroundedAnswer.model_validate(values)


def validate(candidate: GroundedAnswer, evidence=None):
    return GroundedAnswerValidator().validate(
        answer=candidate,
        evidence=evidence or evidence_pack(),
        expected_language=QueryLanguage.EN,
        risk=RetrievalRisk.HIGH,
    )


def test_supported_claim_with_exact_quote_is_accepted() -> None:
    result = validate(answer())

    assert result.accepted is True
    assert result.answer.status == "answered"
    assert result.issues == []


@pytest.mark.parametrize(
    ("citation", "expected_code"),
    [
        (
            {"evidence_id": "missing", "quote": "Visa-free entry is permitted"},
            "citation_evidence_unknown",
        ),
        ({"evidence_id": "chunk-1", "quote": "A quote not in evidence"}, "citation_quote_mismatch"),
    ],
)
def test_invalid_citations_degrade_entire_answer(citation, expected_code) -> None:
    candidate = answer()
    claim = (
        candidate.sections[0]
        .claims[0]
        .model_copy(update={"citations": [ClaimCitation.model_validate(citation)]})
    )
    section = candidate.sections[0].model_copy(update={"claims": [claim]})

    result = validate(candidate.model_copy(update={"sections": [section]}))

    assert result.accepted is False
    assert result.answer.status == "insufficient"
    assert expected_code in {issue.code for issue in result.issues}


def test_lexically_unsupported_claim_and_language_mismatch_are_rejected() -> None:
    candidate = answer(language="ru")
    claim = (
        candidate.sections[0]
        .claims[0]
        .model_copy(update={"text": "Applicants must buy insurance and register an apartment."})
    )
    section = candidate.sections[0].model_copy(update={"claims": [claim]})

    result = validate(candidate.model_copy(update={"sections": [section]}))

    assert {issue.code for issue in result.issues} == {
        "answer_language_mismatch",
        "claim_not_supported",
    }


def test_answered_response_cannot_use_insufficient_evidence() -> None:
    result = validate(answer(), evidence_pack(status="insufficient"))

    assert result.accepted is False
    assert result.issues[0].code == "answer_without_sufficient_evidence"


def test_answer_schema_rejects_extra_fields_and_invalid_shapes() -> None:
    with pytest.raises(ValidationError):
        GroundedAnswer.model_validate(
            {"status": "answered", "language": "en", "summary": "No sections", "sections": []}
        )
    with pytest.raises(ValidationError):
        GroundedAnswer.model_validate(
            {"status": "insufficient", "language": "en", "summary": "No evidence", "extra": True}
        )
