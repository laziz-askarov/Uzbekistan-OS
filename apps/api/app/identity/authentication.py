from typing import Protocol

from app.identity.service import VerifiedIdentity


class AuthenticationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IdentityVerifier(Protocol):
    def verify(self, bearer_token: str) -> VerifiedIdentity: ...


class DisabledIdentityVerifier:
    """Fail closed until a trusted authentication adapter is configured."""

    def verify(self, bearer_token: str) -> VerifiedIdentity:
        del bearer_token
        raise AuthenticationError(
            "authentication_unconfigured",
            "a trusted authentication verifier is not configured",
        )
