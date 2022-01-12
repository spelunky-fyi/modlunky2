from collections import defaultdict
from dataclasses import dataclass
from typing import List

from pytest import mark

from modlunky2.ui.trackers.label import Label, RunLabel

# Sets of labels and their expected text for each MossRanking category.
MOSSRANKING_CATEGORIES = [
    # Main tab
    ({Label.ANY}, "Any%"),
    ({Label.SUNKEN_CITY}, "Sunken City%"),
    ({Label.LOW, Label.ANY}, "Low%"),
    ({Label.LOW, Label.JUNGLE_TEMPLE, Label.ANY}, "Low% Jungle/Temple"),
    ({Label.PACIFIST, Label.LOW, Label.ANY}, "Pacifist Low%"),
    ({Label.CHAIN, Label.LOW, Label.ABZU, Label.SUNKEN_CITY}, "Chain Low% Abzu"),
    ({Label.CHAIN, Label.LOW, Label.DUAT, Label.SUNKEN_CITY}, "Chain Low% Duat"),
    ({Label.COSMIC_OCEAN}, "Cosmic Ocean%"),
    ({Label.NO_TELEPORTER, Label.ANY}, "No TP Any%"),
    ({Label.NO_TELEPORTER, Label.SUNKEN_CITY}, "No TP Sunken City%"),
    (
        {Label.NO_TELEPORTER, Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY},
        "No TP Sunken City% Abzu",
    ),
    (
        {Label.NO_TELEPORTER, Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY},
        "No TP Sunken City% Duat",
    ),
    ({Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY}, "Sunken City% Abzu"),
    ({Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY}, "Sunken City% Duat"),
    ({Label.NO_GOLD, Label.ANY}, "No Gold"),
    ({Label.NO_GOLD, Label.LOW, Label.ANY}, "No Gold Low%"),
    # Score tab
    ({Label.SCORE, Label.ANY}, "Score"),
    ({Label.SCORE, Label.NO_CO, Label.ANY}, "Score No CO"),
    # Misc tab
    ({Label.EGGPLANT, Label.COSMIC_OCEAN}, "Eggplant Cosmic Ocean%"),
    ({Label.TRUE_CROWN, Label.COSMIC_OCEAN}, "True Crown Cosmic Ocean%"),
    (
        {Label.EGGPLANT, Label.TRUE_CROWN, Label.COSMIC_OCEAN},
        "Eggplant True Crown Cosmic Ocean%",
    ),
    ({Label.NO_JETPACK, Label.COSMIC_OCEAN}, "No Jetpack Cosmic Ocean%"),
    ({Label.NO_GOLD, Label.COSMIC_OCEAN}, "No Gold Cosmic Ocean%"),
    ({Label.LOW, Label.COSMIC_OCEAN}, "Low% Cosmic Ocean"),
    (
        {Label.CHAIN, Label.LOW, Label.ABZU, Label.COSMIC_OCEAN},
        "Chain Low% Cosmic Ocean",
    ),
    ({Label.LOW, Label.SUNKEN_CITY}, "Low% Sunken City"),
    ({Label.NO_GOLD, Label.LOW, Label.SUNKEN_CITY}, "No Gold Low% Sunken City"),
    ({Label.NO_TELEPORTER, Label.NO_GOLD, Label.ANY}, "No TP No Gold"),
    ({Label.NO_GOLD, Label.SUNKEN_CITY}, "No Gold Sunken City%"),
    (
        {Label.NO_TELEPORTER, Label.NO_GOLD, Label.SUNKEN_CITY},
        "No TP No Gold Sunken City%",
    ),
    (
        {Label.NO_GOLD, Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY},
        "No Gold Sunken City% Abzu",
    ),
    (
        {Label.NO_GOLD, Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY},
        "No Gold Sunken City% Duat",
    ),
    (
        {
            Label.NO_GOLD,
            Label.CHAIN,
            Label.LOW,
            Label.ABZU,
            Label.SUNKEN_CITY,
        },
        "No Gold Chain Low% Abzu",
    ),
    (
        {
            Label.NO_GOLD,
            Label.CHAIN,
            Label.LOW,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "No Gold Chain Low% Duat",
    ),
    ({Label.EGGPLANT, Label.SUNKEN_CITY}, "Eggplant%"),
    ({Label.NO_TELEPORTER, Label.EGGPLANT, Label.SUNKEN_CITY}, "No TP Eggplant%"),
    ({Label.LOW, Label.EGGPLANT, Label.SUNKEN_CITY}, "Low% Eggplant"),
    ({Label.NO_GOLD, Label.EGGPLANT, Label.SUNKEN_CITY}, "No Gold Eggplant%"),
    (
        {Label.NO_GOLD, Label.LOW, Label.EGGPLANT, Label.SUNKEN_CITY},
        "No Gold Low% Eggplant",
    ),
    (
        {Label.EGGPLANT, Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY},
        "Eggplant% Abzu",
    ),
    (
        {Label.EGGPLANT, Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY},
        "Eggplant% Duat",
    ),
    (
        {
            Label.CHAIN,
            Label.LOW,
            Label.EGGPLANT,
            Label.ABZU,
            Label.SUNKEN_CITY,
        },
        "Chain Low% Eggplant Abzu",
    ),
    (
        {
            Label.CHAIN,
            Label.LOW,
            Label.EGGPLANT,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "Chain Low% Eggplant Duat",
    ),
    (
        {
            Label.NO_GOLD,
            Label.CHAIN,
            Label.LOW,
            Label.ABZU,
            Label.EGGPLANT,
            Label.SUNKEN_CITY,
        },
        "No Gold Chain Low% Eggplant Abzu",
    ),
    (
        {
            Label.NO_GOLD,
            Label.CHAIN,
            Label.LOW,
            Label.DUAT,
            Label.EGGPLANT,
            Label.SUNKEN_CITY,
        },
        "No Gold Chain Low% Eggplant Duat",
    ),
    ({Label.MILLIONAIRE, Label.ANY}, "Millionaire"),
    ({Label.NO_TELEPORTER, Label.MILLIONAIRE, Label.ANY}, "No TP Millionaire"),
    ({Label.LOW, Label.MILLIONAIRE, Label.ANY}, "Low% Millionaire"),
    (
        {Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.ANY},
        "Ice Caves Shortcut%",
    ),
    (
        {Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.SUNKEN_CITY},
        "Ice Caves Shortcut Sunken City%",
    ),
    (
        {Label.PACIFIST, Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.ANY},
        "Pacifist Ice Caves Shortcut%",
    ),
    (
        {Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.MILLIONAIRE, Label.ANY},
        "Ice Caves Shortcut% Millionaire",
    ),
    # Pacifist tab
    ({Label.PACIFIST, Label.ANY}, "Pacifist"),
    ({Label.PACIFIST, Label.SUNKEN_CITY}, "Pacifist Sunken City%"),
    ({Label.PACIFIST, Label.LOW, Label.ANY}, "Pacifist Low%"),
    ({Label.PACIFIST, Label.COSMIC_OCEAN}, "Pacifist Cosmic Ocean%"),
    ({Label.NO_TELEPORTER, Label.PACIFIST, Label.ANY}, "No TP Pacifist"),
    (
        {Label.NO_TELEPORTER, Label.PACIFIST, Label.SUNKEN_CITY},
        "No TP Pacifist Sunken City%",
    ),
    ({Label.NO_GOLD, Label.PACIFIST, Label.ANY}, "No Gold Pacifist"),
    (
        {Label.NO_GOLD, Label.PACIFIST, Label.SUNKEN_CITY},
        "No Gold Pacifist Sunken City%",
    ),
    ({Label.NO_GOLD, Label.PACIFIST, Label.LOW, Label.ANY}, "No Gold Pacifist Low%"),
    ({Label.PACIFIST, Label.LOW, Label.SUNKEN_CITY}, "Pacifist Low% Sunken City"),
    (
        {Label.NO_GOLD, Label.PACIFIST, Label.LOW, Label.SUNKEN_CITY},
        "No Gold Pacifist Low% Sunken City",
    ),
    (
        {
            Label.PACIFIST,
            Label.CHAIN,
            Label.ABZU,
            Label.SUNKEN_CITY,
        },
        "Pacifist Sunken City% Abzu",
    ),
    (
        {
            Label.PACIFIST,
            Label.CHAIN,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "Pacifist Sunken City% Duat",
    ),
    (
        {
            Label.PACIFIST,
            Label.CHAIN,
            Label.LOW,
            Label.ABZU,
            Label.SUNKEN_CITY,
        },
        "Pacifist Chain Low% Abzu",
    ),
    (
        {
            Label.PACIFIST,
            Label.CHAIN,
            Label.LOW,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "Pacifist Chain Low% Duat",
    ),
    (
        {
            Label.NO_GOLD,
            Label.PACIFIST,
            Label.CHAIN,
            Label.LOW,
            Label.ABZU,
            Label.SUNKEN_CITY,
        },
        "No Gold Pacifist Chain Low% Abzu",
    ),
    (
        {
            Label.NO_GOLD,
            Label.PACIFIST,
            Label.CHAIN,
            Label.LOW,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "No Gold Pacifist Chain Low% Duat",
    ),
    ({Label.PACIFIST, Label.EGGPLANT, Label.SUNKEN_CITY}, "Pacifist Eggplant%"),
    (
        {Label.PACIFIST, Label.LOW, Label.EGGPLANT, Label.SUNKEN_CITY},
        "Pacifist Low% Eggplant",
    ),
    ({Label.PACIFIST, Label.EGGPLANT, Label.SUNKEN_CITY}, "Pacifist Eggplant%"),
    (
        {Label.PACIFIST, Label.LOW, Label.EGGPLANT, Label.SUNKEN_CITY},
        "Pacifist Low% Eggplant",
    ),
    (
        {Label.NO_GOLD, Label.PACIFIST, Label.EGGPLANT, Label.SUNKEN_CITY},
        "No Gold Pacifist Eggplant%",
    ),
    (
        {Label.NO_GOLD, Label.PACIFIST, Label.LOW, Label.EGGPLANT, Label.SUNKEN_CITY},
        "No Gold Pacifist Low% Eggplant",
    ),
    (
        {Label.PACIFIST, Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.ANY},
        "Pacifist Ice Caves Shortcut%",
    ),
]


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


@mark.parametrize("labels,expected", MOSSRANKING_CATEGORIES)
def test_mossranking_alignment(labels, expected):
    run_label = RunLabel(labels)
    actual = run_label.text(hide_early=False, excluded_categories=set())
    assert actual == expected


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
