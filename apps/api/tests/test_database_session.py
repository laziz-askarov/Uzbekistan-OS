import pytest

from app.database import session as session_module


class RecordingSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


def install_session(monkeypatch: pytest.MonkeyPatch) -> RecordingSession:
    session = RecordingSession()
    monkeypatch.setattr(session_module, "get_session_factory", lambda: lambda: session)
    return session


def test_database_dependency_commits_successful_request(monkeypatch: pytest.MonkeyPatch) -> None:
    session = install_session(monkeypatch)
    dependency = session_module.get_database_session()

    assert next(dependency) is session
    with pytest.raises(StopIteration):
        next(dependency)

    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closes == 1


def test_database_dependency_rolls_back_failed_request(monkeypatch: pytest.MonkeyPatch) -> None:
    session = install_session(monkeypatch)
    dependency = session_module.get_database_session()

    assert next(dependency) is session
    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    assert session.commits == 0
    assert session.rollbacks == 1
    assert session.closes == 1
