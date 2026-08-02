import math
from collections.abc import Iterable

from app.evaluations.models import (
    BenchmarkCase,
    BenchmarkManifest,
    EvaluationReport,
    EvaluationRun,
    ExpectedOutcome,
    GateApproval,
    GateDefinition,
    GatePolicy,
    GateResult,
    GateResultStatus,
    MetricResult,
    MetricStatus,
)


def _available(value: float, sample_count: int) -> MetricResult:
    return MetricResult(value=value, sample_count=sample_count, status=MetricStatus.AVAILABLE)


def _blocked(reason: str) -> MetricResult:
    return MetricResult(value=None, sample_count=0, status=MetricStatus.BLOCKED, reason=reason)


def _rate(successes: int, total: int, reason: str) -> MetricResult:
    return _available(successes / total, total) if total else _blocked(reason)


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


class Phase4Evaluator:
    def evaluate(
        self,
        *,
        benchmark: BenchmarkManifest,
        run: EvaluationRun,
        policy: GatePolicy,
    ) -> EvaluationReport:
        if run.benchmark_version != benchmark.version:
            raise ValueError("evaluation run benchmark version does not match the manifest")
        cases = {case.id: case for case in benchmark.cases}
        unknown_case_ids = sorted(
            observation.case_id
            for observation in run.observations
            if observation.case_id not in cases
        )
        if unknown_case_ids:
            raise ValueError(f"evaluation run contains unknown cases: {unknown_case_ids}")

        metrics = self._metrics(cases, run)
        gates = [self._evaluate_gate(gate, metrics) for gate in policy.gates]
        if any(gate.status is GateResultStatus.FAIL for gate in gates):
            status = GateResultStatus.FAIL
        elif any(gate.status is GateResultStatus.BLOCKED for gate in gates):
            status = GateResultStatus.BLOCKED
        else:
            status = GateResultStatus.PASS
        return EvaluationReport(
            run_id=run.run_id,
            benchmark_version=benchmark.version,
            policy_version=policy.version,
            metrics=metrics,
            gates=gates,
            status=status,
        )

    def _metrics(
        self,
        cases: dict[str, BenchmarkCase],
        run: EvaluationRun,
    ) -> dict[str, MetricResult]:
        observations = run.observations
        resolved_blockers = set(run.resolved_blockers)
        metrics: dict[str, MetricResult] = {}
        planning = [item for item in observations if item.planning is not None]
        planning_correct = sum(
            item.planning is not None
            and item.planning.language == cases[item.case_id].language
            and item.planning.intent == cases[item.case_id].expected_intent
            and item.planning.domains == cases[item.case_id].expected_domains
            and item.planning.risk == cases[item.case_id].expected_risk
            for item in planning
        )
        metrics["planning.exact_accuracy"] = _rate(
            planning_correct, len(planning), "no planning observations"
        )

        retrieval = [item for item in observations if item.retrieval is not None]
        retrieval_with_labels = [
            item
            for item in retrieval
            if cases[item.case_id].expected_sources
            and set(cases[item.case_id].blockers).issubset(resolved_blockers)
        ]
        if retrieval_with_labels:
            recalls: list[float] = []
            reciprocal_ranks: list[float] = []
            ndcgs: list[float] = []
            for item in retrieval_with_labels:
                case = cases[item.case_id]
                ranked = item.retrieval.ranked_source_slugs[:8] if item.retrieval else []
                expected_relevance = {
                    source.slug: source.relevance for source in case.expected_sources
                }
                recalls.append(
                    len(set(ranked).intersection(expected_relevance)) / len(expected_relevance)
                )
                relevant_ranks = [
                    rank for rank, slug in enumerate(ranked, start=1) if slug in expected_relevance
                ]
                reciprocal_ranks.append(1 / min(relevant_ranks) if relevant_ranks else 0.0)
                dcg = sum(
                    (2 ** expected_relevance.get(slug, 0) - 1) / math.log2(rank + 1)
                    for rank, slug in enumerate(ranked, start=1)
                )
                ideal = sorted(expected_relevance.values(), reverse=True)[:8]
                idcg = sum(
                    (2**relevance - 1) / math.log2(rank + 1)
                    for rank, relevance in enumerate(ideal, start=1)
                )
                ndcgs.append(dcg / idcg if idcg else 0.0)
            sample_count = len(retrieval_with_labels)
            metrics["retrieval.recall_at_8"] = _available(sum(recalls) / sample_count, sample_count)
            metrics["retrieval.mrr"] = _available(
                sum(reciprocal_ranks) / sample_count, sample_count
            )
            metrics["retrieval.ndcg_at_8"] = _available(sum(ndcgs) / sample_count, sample_count)
        else:
            reason = "no retrieval observations with approved expected-source labels"
            metrics["retrieval.recall_at_8"] = _blocked(reason)
            metrics["retrieval.mrr"] = _blocked(reason)
            metrics["retrieval.ndcg_at_8"] = _blocked(reason)
        if retrieval:
            violations = sum(
                item.retrieval.eligibility_violation_count
                for item in retrieval
                if item.retrieval is not None
            )
            metrics["retrieval.eligibility_violations"] = _available(violations, len(retrieval))
        else:
            metrics["retrieval.eligibility_violations"] = _blocked(
                "no retrieval observations"
            )

        generation = [item for item in observations if item.generation is not None]
        answered = [
            item.generation
            for item in generation
            if item.generation is not None
            and item.generation.outcome is ExpectedOutcome.ANSWERED
            and set(cases[item.case_id].blockers).issubset(resolved_blockers)
        ]
        total_claims = sum(item.total_claims for item in answered)
        cited_claims = sum(item.cited_claims for item in answered)
        metrics["generation.claim_citation_coverage"] = (
            _available(cited_claims / total_claims, total_claims)
            if total_claims
            else _blocked("no generated factual claims")
        )
        total_citations = sum(item.total_citations for item in answered)
        valid_citations = sum(item.valid_citations for item in answered)
        metrics["generation.citation_validity"] = (
            _available(valid_citations / total_citations, total_citations)
            if total_citations
            else _blocked("no generated citations")
        )
        if generation:
            metrics["generation.schema_validity"] = _rate(
                sum(bool(item.generation and item.generation.schema_valid) for item in generation),
                len(generation),
                "no generation observations",
            )
            metrics["generation.language_accuracy"] = _rate(
                sum(
                    bool(item.generation and item.generation.language_correct)
                    for item in generation
                ),
                len(generation),
                "no generation observations",
            )
            metrics["generation.safety_pass_rate"] = _rate(
                sum(bool(item.generation and item.generation.safety_passed) for item in generation),
                len(generation),
                "no generation observations",
            )
            metrics["generation.unsupported_claims"] = _available(
                sum(
                    item.generation.unsupported_claims
                    for item in generation
                    if item.generation is not None
                ),
                len(generation),
            )
        else:
            reason = "no generation observations"
            metrics["generation.schema_validity"] = _blocked(reason)
            metrics["generation.language_accuracy"] = _blocked(reason)
            metrics["generation.safety_pass_rate"] = _blocked(reason)
            metrics["generation.unsupported_claims"] = _blocked(reason)

        expected_non_answers = [
            item
            for item in generation
            if cases[item.case_id].expected_outcome is not ExpectedOutcome.ANSWERED
        ]
        metrics["generation.abstention_accuracy"] = _rate(
            sum(
                bool(
                    item.generation
                    and item.generation.outcome == cases[item.case_id].expected_outcome
                )
                for item in expected_non_answers
            ),
            len(expected_non_answers),
            "no abstention or rejection observations",
        )

        completion_latencies = [
            item.completion_latency_ms
            for item in answered
            if item.completion_latency_ms is not None
        ]
        first_content_latencies = [
            item.first_content_latency_ms
            for item in answered
            if item.first_content_latency_ms is not None
        ]
        costs = [item.cost_usd for item in answered if item.cost_usd is not None]
        metrics["performance.completion_latency_p50_ms"] = self._distribution_metric(
            completion_latencies, 0.50, "no completion latency observations"
        )
        metrics["performance.first_content_latency_p95_ms"] = self._distribution_metric(
            first_content_latencies, 0.95, "no first-content latency observations"
        )
        metrics["cost.max_request_usd"] = (
            _available(max(costs), len(costs)) if costs else _blocked("no cost observations")
        )
        return metrics

    @staticmethod
    def _distribution_metric(
        values: list[int], percentile: float, reason: str
    ) -> MetricResult:
        value = _percentile(values, percentile)
        return _available(value, len(values)) if value is not None else _blocked(reason)

    @staticmethod
    def _evaluate_gate(
        gate: GateDefinition, metrics: dict[str, MetricResult]
    ) -> GateResult:
        metric = metrics.get(gate.metric)
        if metric is None:
            return GateResult(
                gate_id=gate.id,
                metric=gate.metric,
                status=GateResultStatus.BLOCKED,
                threshold=gate.threshold,
                reason="policy references an unknown metric",
            )
        if gate.approval is GateApproval.PROPOSED:
            return GateResult(
                gate_id=gate.id,
                metric=gate.metric,
                status=GateResultStatus.BLOCKED,
                value=metric.value,
                threshold=gate.threshold,
                reason="gate threshold is proposed and requires owner approval",
            )
        if metric.status is MetricStatus.BLOCKED or metric.value is None:
            return GateResult(
                gate_id=gate.id,
                metric=gate.metric,
                status=GateResultStatus.BLOCKED,
                threshold=gate.threshold,
                reason=metric.reason or "metric is unavailable",
            )
        if metric.sample_count < gate.minimum_samples:
            return GateResult(
                gate_id=gate.id,
                metric=gate.metric,
                status=GateResultStatus.BLOCKED,
                value=metric.value,
                threshold=gate.threshold,
                reason=(
                    f"metric has {metric.sample_count} samples; "
                    f"gate requires {gate.minimum_samples}"
                ),
            )
        comparisons = {
            "gte": metric.value >= gate.threshold,
            "lte": metric.value <= gate.threshold,
            "eq": metric.value == gate.threshold,
        }
        return GateResult(
            gate_id=gate.id,
            metric=gate.metric,
            status=(GateResultStatus.PASS if comparisons[gate.operator] else GateResultStatus.FAIL),
            value=metric.value,
            threshold=gate.threshold,
        )
