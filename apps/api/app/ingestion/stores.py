from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile

from app.ingestion.errors import IngestionError


class LocalSnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(self, storage_key: str, content: bytes) -> None:
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise IngestionError(
                "invalid_storage_key",
                "snapshot storage key must stay inside the configured root",
                retryable=False,
            )

        target = self.root.joinpath(*key.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != content:
                raise IngestionError(
                    "snapshot_collision",
                    "content-addressed snapshot key contains different bytes",
                    retryable=False,
                )
            return

        with NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.replace(target)
