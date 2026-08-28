"""Recursive minimum reconstruction set closure with fail-closed outcomes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Mapping, Protocol

from .canonical import canonical_json_bytes, sha256_ref


class Resolution(StrEnum):
    PRESENT = "PRESENT"
    FETCH = "FETCH"
    RECONSTRUCT = "RECONSTRUCT"
    GENERATE = "GENERATE"
    HOLD_UNKNOWN = "HOLD_UNKNOWN"
    HOLD_UNAVAILABLE = "HOLD_UNAVAILABLE"
    QUARANTINE_CONFLICT = "QUARANTINE_CONFLICT"


EXECUTABLE = frozenset(
    {
        Resolution.PRESENT,
        Resolution.FETCH,
        Resolution.RECONSTRUCT,
        Resolution.GENERATE,
    }
)


@dataclass(frozen=True, slots=True)
class DependencyDecision:
    requirement_ref: str
    resolution: Resolution
    dependency_refs: tuple[str, ...] = ()
    selected_artifact_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    sealed_resolution_scope_ref: str | None = None


class DependencyCatalog(Protocol):
    def decide_exact(
        self,
        requirement_ref: str,
        *,
        environment_ref: str,
    ) -> DependencyDecision: ...


@dataclass(frozen=True, slots=True)
class ClosedDependencyGraph:
    nodes: tuple[DependencyDecision, ...]
    edges: tuple[tuple[str, str], ...]
    dependency_first_order: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MinimumReconstructionSet:
    environment_ref: str
    requirement_refs: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    closure_ref: str

    @classmethod
    def from_closed_graph(
        cls,
        graph: ClosedDependencyGraph,
        *,
        environment_ref: str,
    ) -> "MinimumReconstructionSet":
        by_ref = {node.requirement_ref: node for node in graph.nodes}
        artifact_refs: list[str] = []
        seen_artifacts: set[str] = set()
        for requirement_ref in graph.dependency_first_order:
            node = by_ref[requirement_ref]
            if node.resolution not in EXECUTABLE or not node.selected_artifact_ref:
                raise ValueError("MRS_GRAPH_NOT_EXECUTABLE")
            if node.selected_artifact_ref not in seen_artifacts:
                artifact_refs.append(node.selected_artifact_ref)
                seen_artifacts.add(node.selected_artifact_ref)

        body = {
            "schema_id": "W7TP_MRS_V0_1",
            "environment_ref": environment_ref,
            "requirements": [
                {
                    "requirement_ref": requirement_ref,
                    "resolution": by_ref[requirement_ref].resolution.value,
                    "selected_artifact_ref": (
                        by_ref[requirement_ref].selected_artifact_ref
                    ),
                    "dependency_refs": list(
                        by_ref[requirement_ref].dependency_refs
                    ),
                    "evidence_refs": list(by_ref[requirement_ref].evidence_refs),
                }
                for requirement_ref in graph.dependency_first_order
            ],
            "edges": [list(edge) for edge in graph.edges],
        }
        return cls(
            environment_ref=environment_ref,
            requirement_refs=graph.dependency_first_order,
            artifact_refs=tuple(artifact_refs),
            closure_ref=sha256_ref(canonical_json_bytes(body)),
        )


@dataclass(frozen=True, slots=True)
class MRSClosureResult:
    state: str
    reason: str | None
    diagnostic_graph: ClosedDependencyGraph
    mrs: MinimumReconstructionSet | None


@dataclass(frozen=True, slots=True)
class MappingDependencyCatalog:
    """Small deterministic catalog useful for sealed inputs and unit tests."""

    decisions: Mapping[str, DependencyDecision]
    environment_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.environment_ref, str) or not self.environment_ref:
            raise ValueError("MRS_CATALOG_ENVIRONMENT_REF_INVALID")

    def decide_exact(
        self,
        requirement_ref: str,
        *,
        environment_ref: str,
    ) -> DependencyDecision:
        if environment_ref != self.environment_ref:
            return _conflict_decision(requirement_ref)
        try:
            return self.decisions[requirement_ref]
        except KeyError:
            return DependencyDecision(
                requirement_ref=requirement_ref,
                resolution=Resolution.HOLD_UNKNOWN,
            )


def _conflict_decision(requirement_ref: str) -> DependencyDecision:
    return DependencyDecision(
        requirement_ref=requirement_ref,
        resolution=Resolution.QUARANTINE_CONFLICT,
    )


def _normalize_decision(
    requirement_ref: str,
    decision: object,
) -> DependencyDecision:
    if not isinstance(decision, DependencyDecision):
        return _conflict_decision(requirement_ref)
    if decision.requirement_ref != requirement_ref:
        return _conflict_decision(requirement_ref)
    try:
        resolution = Resolution(decision.resolution)
    except (TypeError, ValueError):
        return _conflict_decision(requirement_ref)

    if not isinstance(decision.dependency_refs, tuple) or any(
        not isinstance(reference, str) or not reference
        for reference in decision.dependency_refs
    ):
        return _conflict_decision(requirement_ref)
    if not isinstance(decision.evidence_refs, tuple) or any(
        not isinstance(reference, str) or not reference
        for reference in decision.evidence_refs
    ):
        return _conflict_decision(requirement_ref)
    if decision.selected_artifact_ref is not None and (
        not isinstance(decision.selected_artifact_ref, str)
        or not decision.selected_artifact_ref
    ):
        return _conflict_decision(requirement_ref)
    if decision.sealed_resolution_scope_ref is not None and (
        not isinstance(decision.sealed_resolution_scope_ref, str)
        or not decision.sealed_resolution_scope_ref
    ):
        return _conflict_decision(requirement_ref)

    dependencies = tuple(sorted(set(decision.dependency_refs)))
    evidence_refs = tuple(sorted(set(decision.evidence_refs)))
    normalized = replace(
        decision,
        resolution=resolution,
        dependency_refs=dependencies,
        evidence_refs=evidence_refs,
    )

    if resolution in EXECUTABLE and (
        not isinstance(normalized.selected_artifact_ref, str)
        or not normalized.selected_artifact_ref
    ):
        return replace(
            normalized,
            resolution=Resolution.QUARANTINE_CONFLICT,
            selected_artifact_ref=None,
        )
    if resolution == Resolution.HOLD_UNAVAILABLE and (
        not isinstance(normalized.sealed_resolution_scope_ref, str)
        or not normalized.sealed_resolution_scope_ref
    ):
        return replace(normalized, resolution=Resolution.HOLD_UNKNOWN)
    return normalized


def close_mrs(
    roots: tuple[str, ...],
    catalog: DependencyCatalog,
    environment_ref: str,
) -> MRSClosureResult:
    """Recursively close and classify every reachable dependency exactly once."""

    if not isinstance(environment_ref, str) or not environment_ref:
        raise ValueError("MRS_ENVIRONMENT_REF_INVALID")
    if any(not isinstance(root, str) or not root for root in roots):
        raise ValueError("MRS_ROOT_REF_INVALID")

    decisions: dict[str, DependencyDecision] = {}
    active: list[str] = []
    finished: set[str] = set()
    edges: set[tuple[str, str]] = set()
    dependency_first: list[str] = []
    cycle_members: set[str] = set()

    def visit(requirement_ref: str) -> None:
        if requirement_ref in active:
            cycle_members.update(active[active.index(requirement_ref) :])
            return
        if requirement_ref in finished:
            return

        active.append(requirement_ref)
        try:
            try:
                raw_decision = catalog.decide_exact(
                    requirement_ref,
                    environment_ref=environment_ref,
                )
            except LookupError:
                raw_decision = DependencyDecision(
                    requirement_ref=requirement_ref,
                    resolution=Resolution.HOLD_UNKNOWN,
                )
            decision = _normalize_decision(requirement_ref, raw_decision)
            decisions[requirement_ref] = decision
            for dependency_ref in decision.dependency_refs:
                edges.add((dependency_ref, requirement_ref))
                visit(dependency_ref)
        finally:
            active.pop()
        finished.add(requirement_ref)
        dependency_first.append(requirement_ref)

    for root_ref in sorted(set(roots)):
        visit(root_ref)

    for member in cycle_members:
        decisions[member] = replace(
            decisions[member],
            resolution=Resolution.QUARANTINE_CONFLICT,
        )

    graph = ClosedDependencyGraph(
        nodes=tuple(decisions[key] for key in sorted(decisions)),
        edges=tuple(sorted(edges)),
        dependency_first_order=(
            () if cycle_members else tuple(dependency_first)
        ),
    )

    if cycle_members:
        return MRSClosureResult(
            state="QUARANTINED",
            reason="HOLD_MRS_DEPENDENCY_CYCLE",
            diagnostic_graph=graph,
            mrs=None,
        )

    states = {item.resolution for item in decisions.values()}
    if Resolution.QUARANTINE_CONFLICT in states:
        return MRSClosureResult(
            state="QUARANTINED",
            reason="HOLD_MRS_DEPENDENCY_CONFLICT",
            diagnostic_graph=graph,
            mrs=None,
        )
    if Resolution.HOLD_UNKNOWN in states:
        return MRSClosureResult(
            state="HOLD",
            reason="HOLD_MRS_DEPENDENCY_UNKNOWN",
            diagnostic_graph=graph,
            mrs=None,
        )
    if Resolution.HOLD_UNAVAILABLE in states:
        return MRSClosureResult(
            state="HOLD",
            reason="HOLD_MRS_DEPENDENCY_UNAVAILABLE",
            diagnostic_graph=graph,
            mrs=None,
        )
    if not states.issubset(EXECUTABLE):
        return MRSClosureResult(
            state="QUARANTINED",
            reason="HOLD_MRS_DEPENDENCY_CONFLICT",
            diagnostic_graph=graph,
            mrs=None,
        )

    return MRSClosureResult(
        state="MRS_READY",
        reason=None,
        diagnostic_graph=graph,
        mrs=MinimumReconstructionSet.from_closed_graph(
            graph,
            environment_ref=environment_ref,
        ),
    )
