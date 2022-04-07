from pytest import mark

from modlunky2.ui.trackers.label import Label, RunLabel

# This file only contains tests for the correspondence between MossRanking
# and the computed RunLabel string. Most tests are in label_test.py

# Sets of labels and their expected text for each MossRanking category.
MAIN_SPEED_CATEGORIES = [
    ({Label.ANY}, "Any%"),
    ({Label.SUNKEN_CITY}, "Sunken City%"),
    ({Label.COSMIC_OCEAN}, "Cosmic Ocean%"),
    ({Label.LOW, Label.ANY}, "Low%"),
    # -------------------------------------------
    ({Label.LOW, Label.JUNGLE_TEMPLE, Label.ANY}, "Low% Jungle/Temple"),
    ({Label.PACIFIST, Label.LOW, Label.ANY}, "Pacifist Low%"),
    # -------------------------------------------
    ({Label.NO_TELEPORTER, Label.ANY}, "No TP Any%"),
    ({Label.NO_TELEPORTER, Label.SUNKEN_CITY}, "No TP Sunken City%"),
    ({Label.NO_TELEPORTER, Label.SUNKEN_CITY, Label.EGGPLANT}, "No TP Eggplant%"),
    # -------------------------------------------
    ({Label.NO_GOLD, Label.ANY}, "No Gold"),
    ({Label.NO_GOLD, Label.LOW, Label.ANY}, "No Gold Low%"),
    # Chain
    # -------------------------------------------
    ({Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY}, "Abzu%"),
    ({Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY}, "Duat%"),
    # -------------------------------------------
    (
        {Label.NO_TELEPORTER, Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY},
        "No TP Abzu%",
    ),
    (
        {Label.NO_TELEPORTER, Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY},
        "No TP Duat%",
    ),
    # -------------------------------------------
    ({Label.CHAIN, Label.LOW, Label.ABZU, Label.SUNKEN_CITY}, "Chain Low% Abzu"),
    ({Label.CHAIN, Label.LOW, Label.DUAT, Label.SUNKEN_CITY}, "Chain Low% Duat"),
]

MAIN_SCORE_CATEGORIES = [
    ({Label.SCORE, Label.ANY}, "Score"),
    ({Label.SCORE, Label.NO_CO, Label.ANY}, "Score No CO"),
]

MISC_CATEGORIES = [
    ({Label.EGGPLANT, Label.COSMIC_OCEAN}, "Eggplant Cosmic Ocean%"),
    ({Label.TRUE_CROWN, Label.COSMIC_OCEAN}, "True Crown Cosmic Ocean%"),
    (
        {Label.EGGPLANT, Label.TRUE_CROWN, Label.COSMIC_OCEAN},
        "Eggplant True Crown Cosmic Ocean%",
    ),
    ({Label.NO_JETPACK, Label.COSMIC_OCEAN}, "No Jetpack Cosmic Ocean%"),
    ({Label.PACIFIST, Label.COSMIC_OCEAN}, "Pacifist Cosmic Ocean%"),
    ({Label.NO_GOLD, Label.COSMIC_OCEAN}, "No Gold Cosmic Ocean%"),
    (
        {Label.NO_GOLD, Label.PACIFIST, Label.COSMIC_OCEAN},
        "No Gold Pacifist Cosmic Ocean%",
    ),
    # -------------------------------------------
    ({Label.LOW, Label.COSMIC_OCEAN}, "Low% Cosmic Ocean"),
    (
        {Label.CHAIN, Label.LOW, Label.ABZU, Label.COSMIC_OCEAN},
        "Chain Low% Cosmic Ocean",
    ),
    # -------------------------------------------
    ({Label.LOW, Label.VOLCANA_TEMPLE, Label.ANY}, "Low% Volcana/Temple"),
    ({Label.LOW, Label.SUNKEN_CITY}, "Low% Sunken City"),
    ({Label.NO_GOLD, Label.LOW, Label.SUNKEN_CITY}, "No Gold Low% Sunken City"),
    # -------------------------------------------
    ({Label.NO_TELEPORTER, Label.NO_GOLD, Label.ANY}, "No TP No Gold"),
    ({Label.NO_GOLD, Label.SUNKEN_CITY}, "No Gold Sunken City%"),
    (
        {Label.NO_TELEPORTER, Label.NO_GOLD, Label.SUNKEN_CITY},
        "No TP No Gold Sunken City%",
    ),
    # -------------------------------------------
    (
        {Label.NO_GOLD, Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY},
        "No Gold Abzu%",
    ),
    (
        {Label.NO_GOLD, Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY},
        "No Gold Duat%",
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
    # -------------------------------------------
    ({Label.EGGPLANT, Label.SUNKEN_CITY}, "Eggplant%"),
    ({Label.LOW, Label.EGGPLANT, Label.SUNKEN_CITY}, "Low% Eggplant"),
    (
        {Label.NO_TELEPORTER, Label.NO_GOLD, Label.EGGPLANT, Label.SUNKEN_CITY},
        "No TP No Gold Eggplant%",
    ),
    ({Label.NO_GOLD, Label.EGGPLANT, Label.SUNKEN_CITY}, "No Gold Eggplant%"),
    (
        {Label.NO_GOLD, Label.LOW, Label.EGGPLANT, Label.SUNKEN_CITY},
        "No Gold Low% Eggplant",
    ),
    # -------------------------------------------
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
            Label.NO_TELEPORTER,
            Label.EGGPLANT,
            Label.CHAIN,
            Label.ABZU,
            Label.SUNKEN_CITY,
        },
        "No TP Eggplant% Abzu",
    ),
    (
        {
            Label.NO_TELEPORTER,
            Label.EGGPLANT,
            Label.CHAIN,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "No TP Eggplant% Duat",
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
    # -------------------------------------------
    ({Label.MILLIONAIRE, Label.ANY}, "Millionaire"),
    ({Label.NO_TELEPORTER, Label.MILLIONAIRE, Label.ANY}, "No TP Millionaire"),
    ({Label.LOW, Label.MILLIONAIRE, Label.ANY}, "Low% Millionaire"),
    # -------------------------------------------
    ({Label.NO, Label.NO_GOLD, Label.LOW, Label.ANY}, "No%"),
    ({Label.NO, Label.NO_GOLD, Label.LOW, Label.SUNKEN_CITY}, "No% Sunken City"),
    # -------------------------------------------
    (
        {Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.ANY},
        "Ice Caves Shortcut%",
    ),
    (
        {Label.PACIFIST, Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.ANY},
        "Pacifist Ice Caves Shortcut%",
    ),
    (
        {Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.MILLIONAIRE, Label.ANY},
        "Ice Caves Shortcut% Millionaire",
    ),
    (
        {Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.SUNKEN_CITY},
        "Ice Caves Shortcut Sunken City%",
    ),
]

PACIFIST_CATEGORIES = [
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
    (
        {Label.NO_GOLD, Label.PACIFIST, Label.COSMIC_OCEAN},
        "No Gold Pacifist Cosmic Ocean%",
    ),
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
        "Pacifist Abzu%",
    ),
    (
        {
            Label.PACIFIST,
            Label.CHAIN,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "Pacifist Duat%",
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
        {
            Label.PACIFIST,
            Label.CHAIN,
            Label.LOW,
            Label.EGGPLANT,
            Label.ABZU,
            Label.SUNKEN_CITY,
        },
        "Pacifist Chain Low% Eggplant Abzu",
    ),
    (
        {
            Label.PACIFIST,
            Label.CHAIN,
            Label.LOW,
            Label.EGGPLANT,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "Pacifist Chain Low% Eggplant Duat",
    ),
    (
        {
            Label.NO_GOLD,
            Label.PACIFIST,
            Label.CHAIN,
            Label.LOW,
            Label.EGGPLANT,
            Label.ABZU,
            Label.SUNKEN_CITY,
        },
        "No Gold Pacifist Chain Low% Eggplant Abzu",
    ),
    (
        {
            Label.NO_GOLD,
            Label.PACIFIST,
            Label.CHAIN,
            Label.LOW,
            Label.EGGPLANT,
            Label.DUAT,
            Label.SUNKEN_CITY,
        },
        "No Gold Pacifist Chain Low% Eggplant Duat",
    ),
    (
        {Label.PACIFIST, Label.NO, Label.LOW, Label.ANY},
        "Pacifist No%",
    ),
    (
        {Label.PACIFIST, Label.NO, Label.LOW, Label.SUNKEN_CITY},
        "Pacifist No% Sunken City",
    ),
    (
        {Label.PACIFIST, Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.ANY},
        "Pacifist Ice Caves Shortcut%",
    ),
    (
        {Label.PACIFIST, Label.ICE_CAVES_SHORTCUT, Label.LOW, Label.SUNKEN_CITY},
        "Pacifist Ice Caves Shortcut Sunken City%",
    ),
]

MOSSRANKING_CATEGORIES = (
    MAIN_SPEED_CATEGORIES
    + MAIN_SCORE_CATEGORIES
    + MISC_CATEGORIES
    + PACIFIST_CATEGORIES
)


@mark.parametrize("labels,expected", MOSSRANKING_CATEGORIES)
def test_label_matches_mossranking(labels, expected):
    run_label = RunLabel(labels)
    actual = run_label.text(hide_early=False, excluded_categories=set())
    assert actual == expected
