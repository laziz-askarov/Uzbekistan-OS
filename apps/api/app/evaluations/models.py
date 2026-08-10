from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.retrieval.planning import QueryLanguage, RetrievalIntent, RetrievalRisk


class BenchmarkCategory(StrEnum):
    GOLDEN = "golden"
    ADVERSARIAL = "adversarial"
    ABSTENTION = "abstention"


class ExpectedOutcome(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT = "insufficient"
    REJECTED = "rejected"


class BenchmarkBlocker(StrEnum):
    APPROVED_CONTENT = "approved_content"
    MODEL_ROUTE_APPROVAL = "model_route_approval"


class ExpectedSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,119}$")
    relevance: int = Field(default=1, ge=1, le=3)


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,119}$")
    workflow_id: int = Field(ge=1, le=15)
    category: BenchmarkCategory
    query: str = Field(min_length=2, max_length=500)
    language: QueryLanguage
    expected_intent: RetrievalIntent
    expected_domains: list[str] = Field(min_length=1)
    expected_risk: RetrievalRisk
    expected_outcome: ExpectedOutcome
    expected_sources: list[ExpectedSource] = Field(default_factory=list)
    blockers: list[BenchmarkBlocker] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_expected_shape(self) -> "BenchmarkCase":
        source_slugs = [source.slug for source in self.expected_sources]
        if len(source_slugs) != len(set(source_slugs)):
            raise ValueError("expected source slugs must be unique within a case")
        if (
            self.expected_outcome is ExpectedOutcome.ANSWERED
            and not self.expected_sources
            and BenchmarkBlocker.APPROVED_CONTENT not in self.blockers
        ):
            raise ValueError("answered cases without sources must be blocked on approved content")
        if self.expected_outcome is not ExpectedOutcome.ANSWERED and self.expected_sources:
            raise ValueError("non-answer cases cannot declare expected sources")
        return self


class BenchmarkManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(pattern=r"^[1-9][0-9]*\.[0-9]+$")
    status: Literal["frozen"]
    cases: list[BenchmarkCase] = Field(min_length=30, max_length=500)

    @model_validator(mode="after")
    def validate_coverage(self) -> "BenchmarkManifest":
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("benchmark case identifiers must be unique")
        if {case.workflow_id for case in self.cases} != set(range(1, 16)):
            raise ValueError("benchmark must cover all 15 launch workflows")
        if {case.language for case in self.cases} != set(QueryLanguage):
            raise ValueError("benchmark must cover English, Uzbek, and Russian")
        if {case.category for case in self.cases} != set(BenchmarkCategory):
            raise ValueError("benchmark must include golden, adversarial, and abstention cases")
        for workflow_id in range(1, 16):
            workflow_languages = {
                case.language for case in self.cases if case.workflow_id == workflow_id
            }
            if workflow_languages != set(QueryLanguage):
                raise ValueError(f"workflow {workflow_id} must cover English, Uzbek, and Russian")
        return self


class PlanningObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    language: QueryLanguage
    intent: RetrievalIntent
    domains: list[str] = Field(min_length=1)
    risk: RetrievalRisk


class RetrievalObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ranked_source_slugs: list[str] = Field(default_factory=list, max_length=100)
    eligibility_violation_count: int = Field(default=0, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)


class GenerationObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: ExpectedOutcome
    schema_valid: bool
    language_correct: bool
    safety_passed: bool
    total_claims: int = Field(default=0, ge=0)
    cited_claims: int = Field(default=0, ge=0)
    total_citations: int = Field(default=0, ge=0)
    valid_citations: int = Field(default=0, ge=0)
    unsupported_claims: int = Field(default=0, ge=0)
    completion_latency_ms: int | None = Field(default=None, ge=0)
    first_content_latency_ms: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> "GenerationObservation":
        if self.cited_claims > self.total_claims:
            raise ValueError("cited claims cannot exceed total claims")
        if self.valid_citations > self.total_citations:
            raise ValueError("valid citations cannot exceed total citations")
        if self.unsupported_claims > self.total_claims:
            raise ValueError("unsupported claims cannot exceed total claims")
        if self.outcome is not ExpectedOutcome.ANSWERED and any(
            (self.total_claims, self.cited_claims, self.total_citations, self.valid_citations)
        ):
            raise ValueError("non-answer observations cannot contain claims or citations")
        return self


class CaseObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    planning: PlanningObservation | None = None
    retrieval: RetrievalObservation | None = None
    generation: GenerationObservation | None = None

    @model_validator(mode="after")
    def require_stage(self) -> "CaseObservation":
        if self.planning is None and self.retrieval is None and self.generation is None:
            raise ValueError("case observation must contain at least one evaluated stage")
        return self


class EvaluationRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{2,119}$")
    benchmark_version: str
    resolved_blockers: list[BenchmarkBlocker] = Field(default_factory=list)
    observations: list[CaseObservation] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_observation_ids(self) -> "EvaluationRun":
        case_ids = [observation.case_id for observation in self.observations]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("evaluation run case identifiers must be unique")
        if len(self.resolved_blockers) != len(set(self.resolved_blockers)):
            raise ValueError("resolved blockers must be unique")
        return self


class MetricStatus(StrEnum):
    AVAILABLE = "available"
    BLOCKED = "blocked"


class MetricResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float | None = None
    sample_count: int = Field(ge=0)
    status: MetricStatus
    reason: str | None = None


class GateApproval(StrEnum):
    APPROVED = "approved"
    PROPOSED = "proposed"


class GateDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,119}$")
    metric: str = Field(min_length=2, max_length=120)
    operator: Literal["gte", "lte", "eq"]
    threshold: float
    minimum_samples: int = Field(default=1, ge=1)
    approval: GateApproval


class GatePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(pattern=r"^[1-9][0-9]*\.[0-9]+$")
    status: Literal["proposed", "approved"]
    gates: list[GateDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_gate_ids(self) -> "GatePolicy":
        gate_ids = [gate.id for gate in self.gates]
        if len(gate_ids) != len(set(gate_ids)):
            raise ValueError("gate identifiers must be unique")
        return self


class GateResultStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"


class GateResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: str
    metric: str
    status: GateResultStatus
    value: float | None = None
    threshold: float
    reason: str | None = None


class EvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    benchmark_version: str
    policy_version: str
    metrics: dict[str, MetricResult]
    gates: list[GateResult]
    status: GateResultStatus
