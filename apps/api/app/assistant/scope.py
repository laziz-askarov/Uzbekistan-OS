import re

from app.retrieval.planning import RetrievalIntent, RetrievalPlan

_UZBEKISTAN_MARKERS = (
    "uzbekistan",
    "uzbek",
    "o'zbekiston",
    "oʻzbekiston",  # noqa: RUF001
    "o‘zbekiston",  # noqa: RUF001
    "узбекистан",
    "ўзбекистон",
    "tashkent",
    "toshkent",
    "ташкент",
    "samarkand",
    "samarqand",
    "самарканд",
    "bukhara",
    "buxoro",
    "бухар",  # noqa: RUF001
)

_SUPPORTED_GENERAL_MARKERS = (
    "travel",
    "tourism",
    "tourist",
    "visit",
    "hotel",
    "visa",
    "immigration",
    "border",
    "customs",
    "overstay",
    "registration",
    "residence",
    "business",
    "company",
    "llc",
    "mchj",
    "tax",
    "health",
    "hospital",
    "clinic",
    "insurance",
    "rent",
    "apartment",
    "bank",
    "pinfl",
    "work",
    "study",
    "university",
    "sayohat",
    "mehmonxona",
    "bojxona",
    "ro'yxat",
    "roʻyxat",  # noqa: RUF001
    "biznes",
    "kompaniya",
    "soliq",
    "sog'liq",
    "sogʻliq",  # noqa: RUF001
    "shifoxona",
    "ijara",
    "банк",
    "виза",
    "туризм",
    "тамож",
    "регистрац",
    "бизнес",
    "налог",
    "больниц",
    "клиник",
    "аренд",
)

# Explicit foreign-country references fail closed unless Uzbekistan is also named.
# The assistant otherwise treats supported procedural questions as implicitly about
# Uzbekistan, which preserves natural prompts such as "How do I register an LLC?".
_FOREIGN_SCOPE_PATTERN = re.compile(
    r"\b(?:in|to|for|from|about)\s+(?:"
    r"afghanistan|australia|austria|azerbaijan|belarus|belgium|canada|china|france|"
    r"georgia|germany|india|italy|japan|kazakhstan|kyrgyzstan|pakistan|poland|russia|"
    r"south korea|spain|sweden|switzerland|tajikistan|turkey|turkmenistan|ukraine|"
    r"united arab emirates|united kingdom|united states|usa|uk|uae"
    r")\b",
    flags=re.IGNORECASE,
)


class UzbekistanScopeGuard:
    """Deterministically keep assistant answers inside the approved Uzbekistan MVP scope."""

    @staticmethod
    def allows(plan: RetrievalPlan) -> bool:
        query = plan.normalized_query
        names_uzbekistan = any(marker in query for marker in _UZBEKISTAN_MARKERS)
        if _FOREIGN_SCOPE_PATTERN.search(query) and not names_uzbekistan:
            return False
        if plan.intent is not RetrievalIntent.GENERAL:
            return True
        if not names_uzbekistan:
            return False
        return any(marker in query for marker in _SUPPORTED_GENERAL_MARKERS)
