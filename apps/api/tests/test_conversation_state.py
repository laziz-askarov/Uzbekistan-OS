from datetime import UTC, datetime

import pytest

from app.ai.context import ConversationMessage
from app.ai.dialogue import ClarificationPlanner
from app.ai.state import (
    ContextualQueryResolver,
    ConversationFact,
    ConversationFactUpdate,
    ConversationState,
    ConversationStateError,
    ConversationStateResolver,
    MissingContext,
)
from app.retrieval.planning import QueryRequest, RetrievalIntent, RetrievalPlanner


def user_message(ordinal: int, content: str) -> ConversationMessage:
    return ConversationMessage(
        id=f"message-{ordinal}",
        ordinal=ordinal,
        role="user",
        language="en",
        content=content,
        created_at=datetime(2026, 8, 14, ordinal, tzinfo=UTC),
    )


def base_state() -> ConversationState:
    return ConversationState(
        workflow="foreigner_registration",
        goal="determine-registration-requirements",
        language="en",
        facts=[
            ConversationFact(
                field="nationality",
                value="US",
                status="confirmed",
                source_message_id="message-1",
                quote="US citizen",
            )
        ],
        missing_context=[
            MissingContext(
                field="location",
                reason="Registration procedure may depend on location.",
            )
        ],
    )


def test_confirmed_state_is_inherited_by_retrieval_and_workflow_resolves_follow_up() -> None:
    state = base_state()
    resolution = ContextualQueryResolver().resolve(
        QueryRequest(query="What about my spouse?", language="en"),
        state,
    )

    plan = RetrievalPlanner().plan(
        resolution.request,
        intent_hint=resolution.intent_hint,
    )

    assert resolution.request.applicability.nationality == "US"
    assert resolution.inherited_fields == ["nationality"]
    assert plan.intent is RetrievalIntent.FOREIGNER_REGISTRATION
    assert plan.domains == ["immigration"]


def test_explicit_request_context_overrides_but_does_not_mutate_conversation_state() -> None:
    state = base_state()
    resolution = ContextualQueryResolver().resolve(
        QueryRequest(
            query="What applies to a German citizen?",
            language="en",
            applicability={"nationality": "DE"},
        ),
        state,
    )

    assert resolution.request.applicability.nationality == "DE"
    assert resolution.overridden_fields == ["nationality"]
    assert state.facts[0].value == "US"


def test_inferred_facts_do_not_constrain_retrieval() -> None:
    state = ConversationState(
        language="en",
        facts=[
            ConversationFact(
                field="location",
                value="Tashkent",
                status="inferred",
                confidence="medium",
                source_message_id="message-1",
                quote="hotel in Tashkent",
            )
        ],
    )

    resolution = ContextualQueryResolver().resolve(QueryRequest(query="What next?"), state)

    assert resolution.request.applicability.location is None
    assert resolution.inherited_fields == []


def test_conflicting_observation_removes_active_fact_until_user_corrects_it() -> None:
    messages = [
        user_message(1, "I am a US citizen."),
        user_message(2, "I will use a German passport."),
        user_message(3, "Use my German passport for this question."),
    ]
    resolver = ConversationStateResolver()
    conflicted = resolver.apply(
        base_state(),
        updates=[
            ConversationFactUpdate(
                field="nationality",
                value="DE",
                status="confirmed",
                source_message_id="message-2",
                quote="German passport",
            )
        ],
        messages=messages,
    )

    assert conflicted.facts == []
    assert conflicted.conflicts[0].field == "nationality"

    corrected = resolver.apply(
        conflicted,
        updates=[
            ConversationFactUpdate(
                mode="correct",
                field="nationality",
                value="DE",
                status="confirmed",
                source_message_id="message-3",
                quote="German passport",
            )
        ],
        messages=messages,
    )

    assert corrected.facts[0].value == "DE"
    assert corrected.conflicts == []


def test_fact_update_requires_an_exact_quote_from_an_active_user_message() -> None:
    with pytest.raises(ConversationStateError) as failure:
        ConversationStateResolver().apply(
            ConversationState(language="en"),
            updates=[
                ConversationFactUpdate(
                    field="nationality",
                    value="US",
                    status="confirmed",
                    source_message_id="message-1",
                    quote="Canadian citizen",
                )
            ],
            messages=[user_message(1, "I am a US citizen.")],
        )

    assert failure.value.code == "fact_quote_mismatch"


def test_state_fingerprint_is_deterministic() -> None:
    assert base_state().fingerprint == base_state().fingerprint


def test_clarification_planner_prioritizes_conflicts_then_missing_context() -> None:
    state = base_state()
    missing = ClarificationPlanner().plan(state)

    assert missing is not None
    assert missing.field == "location"
    assert missing.response_type == "text"

    messages = [
        user_message(1, "I am a US citizen."),
        user_message(2, "I will use a German passport."),
    ]
    conflicted = ConversationStateResolver().apply(
        state,
        updates=[
            ConversationFactUpdate(
                field="nationality",
                value="DE",
                status="confirmed",
                source_message_id="message-2",
                quote="German passport",
            )
        ],
        messages=messages,
    )
    conflict = ClarificationPlanner().plan(conflicted)

    assert conflict is not None
    assert conflict.id == "resolve-nationality"
    assert [option.value for option in conflict.options] == ["US", "DE"]
