import json
from collections.abc import Callable, Mapping
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


IdentityTransport = Callable[[str], Mapping[str, object]]


class SupabaseIdentityVerifier:
    """Verify customer access tokens against Supabase Auth's user endpoint."""

    def __init__(
        self,
        *,
        supabase_url: str,
        anon_key: str,
        timeout_seconds: float = 3,
        transport: IdentityTransport | None = None,
    ) -> None:
        self.user_url = f"{supabase_url.rstrip('/')}/auth/v1/user"
        self.anon_key = anon_key
        self.timeout_seconds = timeout_seconds
        self.transport = transport or self._verify_remote

    def verify(self, bearer_token: str) -> VerifiedIdentity:
        token = bearer_token.strip()
        if not token:
            raise AuthenticationError("invalid_bearer_token", "the Bearer token is invalid")
        try:
            payload = self.transport(token)
        except AuthenticationError:
            raise
        except Exception as error:
            raise AuthenticationError(
                "identity_provider_unavailable",
                "the identity provider is temporarily unavailable",
            ) from error
        subject = payload.get("id")
        is_anonymous = payload.get("is_anonymous")
        if not isinstance(subject, str) or not subject.strip() or is_anonymous is True:
            raise AuthenticationError("invalid_bearer_token", "the Bearer token is invalid")
        return VerifiedIdentity(provider="supabase", subject=subject)

    def _verify_remote(self, bearer_token: str) -> Mapping[str, object]:
        request = Request(
            self.user_url,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "apikey": self.anon_key,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {401, 403}:
                raise AuthenticationError(
                    "invalid_bearer_token",
                    "the Bearer token is invalid",
                ) from error
            raise AuthenticationError(
                "identity_provider_unavailable",
                "the identity provider is temporarily unavailable",
            ) from error
        except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AuthenticationError(
                "identity_provider_unavailable",
                "the identity provider is temporarily unavailable",
            ) from error
        if not isinstance(payload, dict):
            raise AuthenticationError("invalid_bearer_token", "the Bearer token is invalid")
        return payload
