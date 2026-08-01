from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from redis import Redis
from redis.exceptions import ResponseError


class IngestionTask(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=128)
    attempt: int = Field(default=1, ge=1)
    max_attempts: int = Field(default=3, ge=1, le=20)
    enqueued_at: datetime

    @model_validator(mode="after")
    def validate_task(self) -> "IngestionTask":
        if self.attempt > self.max_attempts:
            raise ValueError("task attempt cannot exceed max_attempts")
        if self.enqueued_at.tzinfo is None or self.enqueued_at.utcoffset() is None:
            raise ValueError("enqueued_at must be timezone-aware")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key cannot be blank")
        return self

    def retry(self, *, increment_attempt: bool = True) -> "IngestionTask":
        attempt = min(self.attempt + 1, self.max_attempts) if increment_attempt else self.attempt
        return self.model_copy(
            update={"attempt": attempt, "enqueued_at": datetime.now(UTC)}
        )

    def canonical_json(self) -> str:
        return self.model_dump_json()


@dataclass(frozen=True, slots=True)
class QueueDelivery:
    message_id: str
    raw_payload: str
    task: IngestionTask | None
    validation_error: str | None = None
    reclaimed: bool = False


class IngestionQueue(Protocol):
    def publish(self, task: IngestionTask) -> str: ...

    def promote_due(self, *, now: datetime, limit: int = 100) -> int: ...

    def reserve(self, *, block_ms: int) -> QueueDelivery | None: ...

    def reclaim_stale(self, *, min_idle_ms: int) -> QueueDelivery | None: ...

    def acknowledge(self, delivery: QueueDelivery) -> None: ...

    def schedule_retry(
        self,
        delivery: QueueDelivery,
        task: IngestionTask,
        *,
        delay: timedelta,
    ) -> None: ...

    def dead_letter(
        self,
        delivery: QueueDelivery,
        *,
        error_code: str,
        error_message: str,
    ) -> None: ...


class RedisStreamIngestionQueue:
    _MAX_PAYLOAD_BYTES = 16_384
    _PROMOTE_DUE_SCRIPT = """
local items = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, ARGV[2])
local promoted = 0
for _, payload in ipairs(items) do
  if redis.call('ZREM', KEYS[1], payload) == 1 then
    redis.call('XADD', KEYS[2], '*', 'payload', payload)
    promoted = promoted + 1
  end
end
return promoted
"""

    def __init__(
        self,
        *,
        client: Redis,
        stream: str,
        group: str,
        consumer: str,
        retry_set: str,
        dead_letter_stream: str,
    ) -> None:
        self.client = client
        self.stream = stream
        self.group = group
        self.consumer = consumer
        self.retry_set = retry_set
        self.dead_letter_stream = dead_letter_stream

    def ensure_group(self) -> None:
        try:
            self.client.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    def publish(self, task: IngestionTask) -> str:
        return self._text(self.client.xadd(self.stream, {"payload": task.canonical_json()}))

    def promote_due(self, *, now: datetime, limit: int = 100) -> int:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("retry promotion time must be timezone-aware")
        return int(
            self.client.eval(
                self._PROMOTE_DUE_SCRIPT,
                2,
                self.retry_set,
                self.stream,
                now.timestamp(),
                limit,
            )
        )

    def reserve(self, *, block_ms: int) -> QueueDelivery | None:
        response = self.client.xreadgroup(
            self.group,
            self.consumer,
            {self.stream: ">"},
            count=1,
            block=block_ms,
        )
        if not response:
            return None
        _, messages = response[0]
        message_id, fields = messages[0]
        return self._delivery(message_id, fields, reclaimed=False)

    def reclaim_stale(self, *, min_idle_ms: int) -> QueueDelivery | None:
        response = self.client.xautoclaim(
            self.stream,
            self.group,
            self.consumer,
            min_idle_ms,
            "0-0",
            count=1,
        )
        messages = response[1] if response and len(response) > 1 else []
        if not messages:
            return None
        message_id, fields = messages[0]
        return self._delivery(message_id, fields, reclaimed=True)

    def acknowledge(self, delivery: QueueDelivery) -> None:
        self.client.xack(self.stream, self.group, delivery.message_id)

    def schedule_retry(
        self,
        delivery: QueueDelivery,
        task: IngestionTask,
        *,
        delay: timedelta,
    ) -> None:
        due_at = datetime.now(UTC) + delay
        pipeline = self.client.pipeline(transaction=True)
        pipeline.zadd(self.retry_set, {task.canonical_json(): due_at.timestamp()})
        pipeline.xack(self.stream, self.group, delivery.message_id)
        pipeline.execute()

    def dead_letter(
        self,
        delivery: QueueDelivery,
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        pipeline = self.client.pipeline(transaction=True)
        pipeline.xadd(
            self.dead_letter_stream,
            {
                "payload": delivery.raw_payload,
                "error_code": error_code,
                "error_message": error_message[:500],
                "failed_at": datetime.now(UTC).isoformat(),
            },
        )
        pipeline.xack(self.stream, self.group, delivery.message_id)
        pipeline.execute()

    @classmethod
    def _delivery(cls, message_id, fields, *, reclaimed: bool) -> QueueDelivery:
        payload_value = fields.get("payload") or fields.get(b"payload")
        payload = cls._text(payload_value) if payload_value is not None else ""
        payload_bytes = payload.encode()
        if len(payload_bytes) > cls._MAX_PAYLOAD_BYTES:
            return QueueDelivery(
                message_id=cls._text(message_id),
                raw_payload=payload_bytes[: cls._MAX_PAYLOAD_BYTES].decode(errors="replace"),
                task=None,
                validation_error="queue payload exceeds the maximum size",
                reclaimed=reclaimed,
            )
        try:
            task = IngestionTask.model_validate_json(payload)
        except Exception as error:
            return QueueDelivery(
                message_id=cls._text(message_id),
                raw_payload=payload,
                task=None,
                validation_error=str(error),
                reclaimed=reclaimed,
            )
        return QueueDelivery(
            message_id=cls._text(message_id),
            raw_payload=payload,
            task=task,
            reclaimed=reclaimed,
        )

    @staticmethod
    def _text(value) -> str:
        return value.decode() if isinstance(value, bytes) else str(value)
