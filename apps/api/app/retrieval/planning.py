import re
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RetrievalPlanningError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class QueryLanguage(StrEnum):
    EN = "en"
    UZ = "uz"
    RU = "ru"


class RetrievalRisk(StrEnum):
    MEDIUM = "medium"
    HIGH = "high"


class RetrievalIntent(StrEnum):
    ARRIVAL_ENTRY = "arrival_entry"
    VISA_ELIGIBILITY = "visa_eligibility"
    FOREIGNER_REGISTRATION = "foreigner_registration"
    MOVING = "moving"
    BUSINESS_REGISTRATION = "business_registration"
    RESIDENCE_PERMIT = "residence_permit"
    EMPLOYMENT = "employment"
    STUDY = "study"
    BANKING = "banking"
    PINFL = "pinfl"
    HEALTHCARE = "healthcare"
    RENTING = "renting"
    CUSTOMS = "customs"
    STAY_EXTENSION = "stay_extension"
    DEPARTURE = "departure"
    GENERAL = "general"


class ApplicabilityContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    audience: str | None = Field(default=None, min_length=1, max_length=120)
    nationality: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    residency_status: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, min_length=1, max_length=160)


class QueryRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=2, max_length=500)
    language: QueryLanguage | None = None
    applicability: ApplicabilityContext = Field(default_factory=ApplicabilityContext)

    @field_validator("query")
    @classmethod
    def normalize_query_boundary(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("query must contain at least two visible characters")
        if "\x00" in value:
            raise ValueError("query contains a forbidden null character")
        return cleaned


class RetrievalPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    normalized_query: str
    query_terms: list[str] = Field(min_length=1, max_length=32)
    language: QueryLanguage
    intent: RetrievalIntent
    domains: list[str] = Field(min_length=1)
    risk: RetrievalRisk
    allowed_trust_tiers: list[int] = Field(min_length=1)
    applicability: ApplicabilityContext
    semantic_enabled: bool
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


_ROLE_DELIMITERS = (
    "<|system|>",
    "<|assistant|>",
    "[system]",
    "begin system message",
    "end system message",
)

_INTENT_RULES: tuple[tuple[RetrievalIntent, tuple[str, ...]], ...] = (
    (RetrievalIntent.PINFL, ("pinfl", "jshshir", "пинфл")),
    (
        RetrievalIntent.STAY_EXTENSION,
        (
            "extend stay",
            "visa extension",
            "overstay",
            "overstaying",
            "visa expired",
            "stay expired",
            "muddatidan osh",
            "qolish muddati",
            "uzaytir",
            "просроч",
            "срок пребывания",
            "продлить",
            "продление",
        ),
    ),
    (
        RetrievalIntent.RESIDENCE_PERMIT,
        ("residence permit", "temporary residence", "yashash guvohnoma", "вид на жительство"),
    ),
    (
        RetrievalIntent.FOREIGNER_REGISTRATION,
        ("foreigner registration", "hotel registration", "ro'yxatdan", "регистрац"),
    ),
    (
        RetrievalIntent.BUSINESS_REGISTRATION,
        # The three Cyrillic letters are an intentional Russian LLC marker.
        ("start an llc", "register company", "business", "mchj", "kompaniya", "ооо"),  # noqa: RUF001
    ),
    (RetrievalIntent.VISA_ELIGIBILITY, ("visa", "viza", "виза")),
    (
        RetrievalIntent.EMPLOYMENT,
        ("work permit", "employment", "job offer", "ishlash", "работ"),
    ),
    (RetrievalIntent.STUDY, ("student", "study", "university", "o'qish", "учеб", "студент")),
    (
        RetrievalIntent.HEALTHCARE,
        ("health", "clinic", "hospital", "insurance", "shifoxona", "клиник", "больниц"),
    ),
    (
        RetrievalIntent.BANKING,
        ("bank account", "bank card", "mobile banking", "bank hisob", "банков", "счет"),
    ),
    (RetrievalIntent.RENTING, ("rent", "lease", "apartment", "ijara", "аренд", "квартир")),
    (
        RetrievalIntent.CUSTOMS,
        ("customs", "bring", "import belongings", "bojxona", "тамож", "ввоз"),
    ),
    (
        RetrievalIntent.DEPARTURE,
        ("leaving uzbekistan", "exit registration", "depart", "chiqish", "выезд"),
    ),
    (
        RetrievalIntent.MOVING,
        ("moving to uzbekistan", "relocate", "ko'chib", "переезд"),
    ),
    (
        RetrievalIntent.ARRIVAL_ENTRY,
        ("flying", "arrival", "airport", "entry", "kelish", "aeroport", "прилет", "въезд"),
    ),
)

_INTENT_DOMAINS = {
    RetrievalIntent.ARRIVAL_ENTRY: ["immigration", "tourism"],
    RetrievalIntent.VISA_ELIGIBILITY: ["immigration"],
    RetrievalIntent.FOREIGNER_REGISTRATION: ["immigration"],
    RetrievalIntent.MOVING: ["immigration", "everyday-living"],
    RetrievalIntent.BUSINESS_REGISTRATION: ["business-registration"],
    RetrievalIntent.RESIDENCE_PERMIT: ["immigration"],
    RetrievalIntent.EMPLOYMENT: ["immigration", "everyday-living"],
    RetrievalIntent.STUDY: ["immigration", "everyday-living"],
    RetrievalIntent.BANKING: ["everyday-living"],
    RetrievalIntent.PINFL: ["everyday-living"],
    RetrievalIntent.HEALTHCARE: ["healthcare"],
    RetrievalIntent.RENTING: ["everyday-living"],
    RetrievalIntent.CUSTOMS: ["immigration", "tourism"],
    RetrievalIntent.STAY_EXTENSION: ["immigration"],
    RetrievalIntent.DEPARTURE: ["immigration", "tourism"],
    RetrievalIntent.GENERAL: [
        "immigration",
        "tourism",
        "business-registration",
        "healthcare",
        "everyday-living",
    ],
}

_HIGH_RISK_DOMAINS = {"immigration", "business-registration", "healthcare"}
_UZBEK_MARKERS = {"uchun", "kerak", "qanday", "o'zbekiston", "viza", "ro'yxatdan", "ijara"}
_RUSSIAN_MARKERS = {"для", "нужно", "как", "узбекистан", "виза", "регистрация", "аренда"}


class RetrievalPlanner:
    def plan(
        self,
        request: QueryRequest,
        *,
        intent_hint: RetrievalIntent | None = None,
    ) -> RetrievalPlan:
        normalized = request.query.casefold()
        if any(delimiter in normalized for delimiter in _ROLE_DELIMITERS):
            raise RetrievalPlanningError(
                "query_control_delimiter",
                "query contains a reserved orchestration delimiter",
            )
        language = request.language or self._detect_language(normalized)
        intent = self._detect_intent(normalized)
        if intent is RetrievalIntent.GENERAL and intent_hint is not None:
            intent = intent_hint
        domains = _INTENT_DOMAINS[intent]
        risk = (
            RetrievalRisk.HIGH
            if any(domain in _HIGH_RISK_DOMAINS for domain in domains)
            else RetrievalRisk.MEDIUM
        )
        query_terms = self._terms(normalized, intent)
        fingerprint_source = "|".join(
            [normalized, language.value, intent.value, *domains, *query_terms]
        )
        return RetrievalPlan(
            query=request.query,
            normalized_query=normalized,
            query_terms=query_terms,
            language=language,
            intent=intent,
            domains=domains,
            risk=risk,
            allowed_trust_tiers=[1] if risk is RetrievalRisk.HIGH else [1, 2],
            applicability=request.applicability,
            semantic_enabled=True,
            fingerprint=sha256(fingerprint_source.encode()).hexdigest(),
        )

    @staticmethod
    def _detect_language(query: str) -> QueryLanguage:
        tokens = set(re.findall(r"[^\W_]+", query, flags=re.UNICODE))
        if tokens.intersection(_RUSSIAN_MARKERS) or re.search(r"[а-яё]", query):  # noqa: RUF001
            return QueryLanguage.RU
        uzbek_apostrophe_markers = ("o‘", "g‘", "oʻ", "gʻ")  # noqa: RUF001
        if tokens.intersection(_UZBEK_MARKERS) or any(
            mark in query for mark in uzbek_apostrophe_markers
        ):
            return QueryLanguage.UZ
        return QueryLanguage.EN

    @staticmethod
    def _detect_intent(query: str) -> RetrievalIntent:
        best_intent = RetrievalIntent.GENERAL
        best_score = (0, 0)
        for intent, phrases in _INTENT_RULES:
            matches = [phrase for phrase in phrases if phrase in query]
            score = (len(matches), max((len(phrase) for phrase in matches), default=0))
            if score > best_score:
                best_intent = intent
                best_score = score
        return best_intent

    @staticmethod
    def _terms(query: str, intent: RetrievalIntent) -> list[str]:
        tokens = [
            token for token in re.findall(r"[^\W_]+", query, flags=re.UNICODE) if len(token) > 1
        ]
        intent_terms = intent.value.split("_") if intent is not RetrievalIntent.GENERAL else []
        return list(dict.fromkeys([*tokens, *intent_terms]))[:32]
