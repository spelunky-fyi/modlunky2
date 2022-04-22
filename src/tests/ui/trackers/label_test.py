from collections import defaultdict
from dataclasses import dataclass
from typing import List

from pytest import mark

from modlunky2.ui.trackers.label import Label, RunLabel

# In addition to this file, there are test for whether generated labels match MossRanking
# in label_matches_mr_test.py


@dataclass(frozen=True)
class VisibilityEdge:
    label: Label
    depends_on: Label
    reason: str


def _build_visibility_edges() -> List[VisibilityEdge]:
    edge_list = []
    for dep, hides_set in RunLabel._HIDES.items():  # pylint: disable=protected-access
        for label in hides_set:
            edge_list.append(VisibilityEdge(label, dep, "_HIDES"))
    for (
        label,
        with_set,
    ) in RunLabel._ONLY_SHOW_WITH.items():  # pylint: disable=protected-access
        for dep in with_set:
            edge_list.append(VisibilityEdge(label, dep, "_ONLY_SHOW_WITH"))

    return edge_list


def test_visibility_deps_not_mutually_exclusive():
    mut_ex_edges = []
    for edge in _build_visibility_edges():
        for mut_ex in RunLabel._MUTUALLY_EXCLUSIVE:  # pylint: disable=protected-access
            if mut_ex >= {edge.label, edge.depends_on}:
                mut_ex_edges.append(edge)

    assert mut_ex_edges == []


def test_visibility_bipartite():
    # If the visibility dependencies aren't bipartite:
    # * We need to iterate/traverse and detect cycles
    # * Iteration order of HIDES and ONLY_SHOW_WITH matters, even though it's not defined
    # * The result depends on the order we apply HIDES or ONLY_SHOW_WITH, making reasoning harder
    edges_by_label = defaultdict(set)
    edges_by_dep = defaultdict(set)
    for edge in _build_visibility_edges():
        edges_by_label[edge.label].add(edge)
        edges_by_dep[edge.depends_on].add(edge)

    labels_that_are_deps = set()
    for label, edges in edges_by_label.items():
        for edge in edges:
            if label in edges_by_dep:
                labels_that_are_deps.add(edge)
    assert labels_that_are_deps == set()

    deps_that_are_labels = set()
    for dep, edges in edges_by_dep.items():
        for edge in edges:
            if dep in edges_by_label:
                deps_that_are_labels.add(edge)
    assert labels_that_are_deps == set()


ASSORTED_LABELS = [
    # Intermediate states
    (
        {Label.CHAIN, Label.LOW, Label.SUNKEN_CITY},
        "Chain Low% Sunken City",
    ),
    (
        {Label.CHAIN, Label.SUNKEN_CITY},
        "Chain Sunken City%",
    ),
    # Chain Death%
    (
        {Label.CHAIN, Label.ABZU, Label.DEATH},
        "Death% Abzu",
    ),
    (
        {Label.CHAIN, Label.LOW, Label.ABZU, Label.DEATH},
        "Chain Low% Death Abzu",
    ),
    (
        {Label.EGGPLANT, Label.DEATH},
        "Eggplant% Death",
    ),
    # Chain CO
    (
        {Label.NO_JETPACK, Label.CHAIN, Label.LOW, Label.ABZU, Label.COSMIC_OCEAN},
        "Chain Low% Cosmic Ocean",
    ),
    (
        {Label.NO_JETPACK, Label.CHAIN, Label.ABZU, Label.COSMIC_OCEAN},
        "No Jetpack Cosmic Ocean%",
    ),
    (
        {
            Label.NO_JETPACK,
            Label.CHAIN,
            Label.JUNGLE_TEMPLE,
            Label.DUAT,
            Label.COSMIC_OCEAN,
        },
        "No Jetpack Cosmic Ocean%",
    ),
]


@mark.parametrize("labels,expected", ASSORTED_LABELS)
def test_assorted_labels(labels, expected):
    run_label = RunLabel(labels)
    actual = run_label.text(hide_early=False, excluded_categories=set())
    assert actual == expected
