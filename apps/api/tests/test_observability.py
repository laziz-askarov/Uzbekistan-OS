import json
import logging

from app.observability import JsonFormatter, bind_request_id, reset_request_id


def test_json_formatter_includes_request_and_http_context() -> None:
    record = logging.LogRecord(
        name="uzbekistan_os.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    record.http_method = "GET"
    record.http_path = "/api/v1/health"
    record.status_code = 200
    record.duration_ms = 1.25
    token = bind_request_id("observability-test")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["level"] == "INFO"
    assert payload["message"] == "request completed"
    assert payload["request_id"] == "observability-test"
    assert payload["http_method"] == "GET"
    assert payload["http_path"] == "/api/v1/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.25
