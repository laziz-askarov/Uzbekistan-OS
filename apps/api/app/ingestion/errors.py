class IngestionError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class SourceNotEligibleError(IngestionError):
    def __init__(self) -> None:
        super().__init__(
            "source_not_eligible",
            "source is not approved for automatic production ingestion",
            retryable=False,
        )
