import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import ClassVar

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    _EXTRA_FIELDS: ClassVar[tuple[str, ...]] = (
        "answer_accepted",
        "answer_generated",
        "answer_issue_codes",
        "assistant_intent",
        "assistant_risk",
        "duration_ms",
        "dependency",
        "evidence_item_count",
        "evidence_source",
        "evidence_status",
        "http_method",
        "http_path",
        "lexical_candidate_count",
        "retrieval_status",
        "status_code",
        "vector_candidate_count",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None) or request_id_context.get()
        if request_id:
            payload["request_id"] = request_id
        for field in self._EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    for handler in root.handlers:
        if getattr(handler, "uzbekistan_os_json", False):
            root.setLevel(level)
            return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.uzbekistan_os_json = True  # type: ignore[attr-defined]
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def bind_request_id(request_id: str) -> Token[str | None]:
    return request_id_context.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    request_id_context.reset(token)
