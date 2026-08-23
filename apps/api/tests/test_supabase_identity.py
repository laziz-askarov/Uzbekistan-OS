import pytest

from app.identity.authentication import AuthenticationError, SupabaseIdentityVerifier


def test_supabase_verifier_accepts_non_anonymous_verified_user() -> None:
    verifier = SupabaseIdentityVerifier(
        supabase_url="https://project.supabase.co",
        anon_key="anon-key",
        transport=lambda token: {"id": "user-123", "is_anonymous": False, "token": token},
    )

    identity = verifier.verify("access-token")

    assert identity.provider == "supabase"
    assert identity.subject == "user-123"


@pytest.mark.parametrize(
    "payload",
    [{}, {"id": ""}, {"id": "guest", "is_anonymous": True}],
)
def test_supabase_verifier_rejects_missing_or_anonymous_identity(payload) -> None:
    verifier = SupabaseIdentityVerifier(
        supabase_url="https://project.supabase.co",
        anon_key="anon-key",
        transport=lambda _: payload,
    )

    with pytest.raises(AuthenticationError) as failure:
        verifier.verify("access-token")

    assert failure.value.code == "invalid_bearer_token"
