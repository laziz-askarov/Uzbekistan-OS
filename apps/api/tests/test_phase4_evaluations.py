import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluations import Phase4Evaluator, load_benchmark, load_gate_policy, load_run
from app.evaluations.models import (
    CaseObservation,
    EvaluationRun,
    ExpectedOutcome,
    GateApproval,
    GateDefinition,
    GatePolicy,
    GateResultStatus,
    GenerationObservation,
    PlanningObservation,
    RetrievalObservation,
)
from app.retrieval.planning import QueryRequest, RetrievalPlanner, RetrievalPlanningError

ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_PATH = ROOT / "data/evaluations/phase-4-benchmark.v1.json"
GATE_POLICY_PATH = ROOT / "data/evaluations/phase-4-gates.v1.json"
PLANNING_BASELINE_PATH = (
    ROOT / "data/evaluations/runs/phase-4-planning-baseline.v1.json"
)


def test_frozen_benchmark_covers_every_flow_language_and_safety_category() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)

    assert benchmark.version == "1.0"
    assert len(benchmark.cases) == 45
    assert {case.workflow_id for case in benchmark.cases} == set(range(1, 16))
    for workflow_id in range(1, 16):
        cases = [case for case in benchmark.cases if case.workflow_id == workflow_id]
        assert {case.language.value for case in cases} == {"en", "uz", "ru"}
        assert {case.category.value for case in cases} == {
            "golden",
            "adversarial",
            "abstention",
        }


def test_frozen_golden_planning_cases_match_deterministic_planner() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    planner = RetrievalPlanner()

    for case in benchmark.cases:
        if case.category.value != "golden":
            continue
        plan = planner.plan(QueryRequest(query=case.query))
        assert plan.language == case.language, case.id
        assert plan.intent == case.expected_intent, case.id
        assert plan.domains == case.expected_domains, case.id
        assert plan.risk == case.expected_risk, case.id


def test_adversarial_control_delimiters_fail_before_retrieval() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    planner = RetrievalPlanner()

    for case in benchmark.cases:
        if case.category.value != "adversarial":
            continue
        with pytest.raises(RetrievalPlanningError) as failure:
            planner.plan(QueryRequest(query=case.query, language=case.language))
        assert failure.value.code == "query_control_delimiter", case.id


def test_benchmark_rejects_unfrozen_or_incomplete_manifests() -> None:
    payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    payload["status"] = "draft"
    with pytest.raises(ValidationError):
        type(load_benchmark(BENCHMARK_PATH)).model_validate(payload)

    payload["status"] = "frozen"
    payload["cases"] = payload["cases"][:3]
    with pytest.raises(ValidationError):
        type(load_benchmark(BENCHMARK_PATH)).model_validate(payload)


def test_evaluator_calculates_retrieval_and_generation_metrics() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    case_one = benchmark.cases[0]
    case_two = benchmark.cases[3]
    run = EvaluationRun(
        run_id="metric-fixture",
        benchmark_version=benchmark.version,
        resolved_blockers=["approved_content", "model_route_approval"],
        observations=[
            CaseObservation(
                case_id=case_one.id,
                retrieval=RetrievalObservation(
                    ranked_source_slugs=["irrelevant-source", case_one.expected_sources[0].slug]
                ),
                generation=GenerationObservation(
                    outcome=ExpectedOutcome.ANSWERED,
                    schema_valid=True,
                    language_correct=True,
                    safety_passed=True,
                    total_claims=2,
                    cited_claims=2,
                    total_citations=2,
                    valid_citations=2,
                    completion_latency_ms=4_000,
                    first_content_latency_ms=2_000,
                    cost_usd=0.02,
                ),
            ),
            CaseObservation(
                case_id=case_two.id,
                retrieval=RetrievalObservation(
                    ranked_source_slugs=[source.slug for source in case_two.expected_sources],
                    eligibility_violation_count=1,
                ),
                generation=GenerationObservation(
                    outcome=ExpectedOutcome.ANSWERED,
                    schema_valid=True,
                    language_correct=True,
                    safety_passed=True,
                    total_claims=2,
                    cited_claims=1,
                    total_citations=2,
                    valid_citations=1,
                    unsupported_claims=1,
                    completion_latency_ms=8_000,
                    first_content_latency_ms=3_500,
                    cost_usd=0.06,
                ),
            ),
        ],
    )
    policy = GatePolicy(
        version="1.0",
        status="approved",
        gates=[
            GateDefinition(
                id="eligibility-zero",
                metric="retrieval.eligibility_violations",
                operator="eq",
                threshold=0,
                approval=GateApproval.APPROVED,
            )
        ],
    )

    report = Phase4Evaluator().evaluate(benchmark=benchmark, run=run, policy=policy)

    assert report.metrics["retrieval.recall_at_8"].value == 1.0
    assert report.metrics["retrieval.mrr"].value == pytest.approx(0.75)
    assert report.metrics["retrieval.eligibility_violations"].value == 1
    assert report.metrics["generation.claim_citation_coverage"].value == 0.75
    assert report.metrics["generation.citation_validity"].value == 0.75
    assert report.metrics["generation.unsupported_claims"].value == 1
    assert report.metrics["performance.completion_latency_p50_ms"].value == 4_000
    assert report.metrics["performance.first_content_latency_p95_ms"].value == 3_500
    assert report.metrics["cost.max_request_usd"].value == 0.06
    assert report.gates[0].status is GateResultStatus.FAIL
    assert report.status is GateResultStatus.FAIL


def test_missing_live_observations_and_proposed_thresholds_block_release() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    policy = load_gate_policy(GATE_POLICY_PATH)
    case = benchmark.cases[0]
    run = EvaluationRun(
        run_id="planning-only",
        benchmark_version=benchmark.version,
        observations=[
            CaseObservation(
                case_id=case.id,
                planning=PlanningObservation(
                    language=case.language,
                    intent=case.expected_intent,
                    domains=case.expected_domains,
                    risk=case.expected_risk,
                ),
            )
        ],
    )

    report = Phase4Evaluator().evaluate(benchmark=benchmark, run=run, policy=policy)

    assert report.metrics["retrieval.recall_at_8"].status.value == "blocked"
    assert report.metrics["generation.citation_validity"].status.value == "blocked"
    assert report.status is GateResultStatus.BLOCKED
    assert all(gate.status is GateResultStatus.BLOCKED for gate in report.gates)


def test_checked_in_planning_baseline_passes_its_gate_and_blocks_live_gates() -> None:
    report = Phase4Evaluator().evaluate(
        benchmark=load_benchmark(BENCHMARK_PATH),
        policy=load_gate_policy(GATE_POLICY_PATH),
        run=load_run(PLANNING_BASELINE_PATH),
    )

    planning_gate = next(gate for gate in report.gates if gate.gate_id == "planning-exact")
    assert planning_gate.status is GateResultStatus.PASS
    assert planning_gate.value == 1.0
    assert report.status is GateResultStatus.BLOCKED


def test_abstention_accuracy_distinguishes_insufficient_from_rejected() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    abstention = next(case for case in benchmark.cases if case.category.value == "abstention")
    adversarial = next(case for case in benchmark.cases if case.category.value == "adversarial")
    run = EvaluationRun(
        run_id="abstention-fixture",
        benchmark_version=benchmark.version,
        observations=[
            CaseObservation(
                case_id=abstention.id,
                generation=GenerationObservation(
                    outcome=ExpectedOutcome.INSUFFICIENT,
                    schema_valid=True,
                    language_correct=True,
                    safety_passed=True,
                ),
            ),
            CaseObservation(
                case_id=adversarial.id,
                generation=GenerationObservation(
                    outcome=ExpectedOutcome.INSUFFICIENT,
                    schema_valid=True,
                    language_correct=True,
                    safety_passed=False,
                ),
            ),
        ],
    )
    policy = GatePolicy(
        version="1.0",
        status="approved",
        gates=[
            GateDefinition(
                id="abstention-perfect",
                metric="generation.abstention_accuracy",
                operator="eq",
                threshold=1,
                minimum_samples=2,
                approval=GateApproval.APPROVED,
            )
        ],
    )

    report = Phase4Evaluator().evaluate(benchmark=benchmark, run=run, policy=policy)

    assert report.metrics["generation.abstention_accuracy"].value == 0.5
    assert report.gates[0].status is GateResultStatus.FAIL


def test_run_rejects_unknown_case_identifiers() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    policy = load_gate_policy(GATE_POLICY_PATH)
    run = EvaluationRun(
        run_id="unknown-case",
        benchmark_version=benchmark.version,
        observations=[
            CaseObservation(
                case_id="does-not-exist",
                retrieval=RetrievalObservation(),
            )
        ],
    )

    with pytest.raises(ValueError, match="unknown cases"):
        Phase4Evaluator().evaluate(benchmark=benchmark, run=run, policy=policy)
