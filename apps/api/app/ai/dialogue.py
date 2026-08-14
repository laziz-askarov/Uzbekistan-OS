from typing import ClassVar

from app.ai.answers import ClarificationOption, ClarificationRequest
from app.ai.state import ConversationField, ConversationState
from app.retrieval.planning import QueryLanguage


class ClarificationPlanner:
    _CHOICES: ClassVar[dict[ConversationField, tuple[ClarificationOption, ...]]] = {
        ConversationField.ACCOMMODATION_TYPE: (
            ClarificationOption(value="hotel", label="Hotel"),
            ClarificationOption(value="private_accommodation", label="Private home or apartment"),
            ClarificationOption(value="multiple", label="More than one place"),
        ),
        ConversationField.APPLICANT_ROLE: (
            ClarificationOption(value="self", label="Myself"),
            ClarificationOption(value="spouse", label="Spouse"),
            ClarificationOption(value="dependent", label="Dependent"),
            ClarificationOption(value="representative", label="Representative"),
        ),
        ConversationField.AUDIENCE: (
            ClarificationOption(value="visitor", label="Visitor"),
            ClarificationOption(value="student", label="Student"),
            ClarificationOption(value="worker", label="Worker"),
            ClarificationOption(value="resident", label="Resident"),
        ),
    }

    _QUESTIONS: ClassVar[dict[QueryLanguage, str]] = {
        QueryLanguage.EN: "What is the applicable {field}?",
        QueryLanguage.UZ: "Tegishli {field} qiymati qanday?",
        QueryLanguage.RU: "Какое значение следует использовать для поля {field}?",
    }
    _CONFLICT_QUESTIONS: ClassVar[dict[QueryLanguage, str]] = {
        QueryLanguage.EN: "You provided different values for {field}. Which should I use?",
        QueryLanguage.UZ: "{field} uchun turli qiymatlar berildi. Qaysi birini ishlatay?",
        QueryLanguage.RU: "Для поля {field} указаны разные значения. Какое использовать?",
    }

    def plan(self, state: ConversationState | None) -> ClarificationRequest | None:
        if state is None:
            return None
        if state.conflicts:
            conflict = state.conflicts[0]
            return ClarificationRequest(
                id=f"resolve-{conflict.field.value.replace('_', '-')}",
                field=conflict.field,
                question=self._CONFLICT_QUESTIONS[state.language].format(
                    field=conflict.field.value.replace("_", " ")
                ),
                reason="Conflicting context cannot be used to filter official guidance safely.",
                response_type="single_choice",
                options=[
                    ClarificationOption(
                        value=conflict.previous.value,
                        label=conflict.previous.value,
                    ),
                    ClarificationOption(
                        value=conflict.proposed.value,
                        label=conflict.proposed.value,
                    ),
                ],
            )
        if not state.missing_context:
            return None
        missing = state.missing_context[0]
        options = list(self._CHOICES.get(missing.field, ()))
        return ClarificationRequest(
            id=f"provide-{missing.field.value.replace('_', '-')}",
            field=missing.field,
            question=self._QUESTIONS[state.language].format(
                field=missing.field.value.replace("_", " ")
            ),
            reason=missing.reason,
            response_type="single_choice" if options else "text",
            options=options,
        )
