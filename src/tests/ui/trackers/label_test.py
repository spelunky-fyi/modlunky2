from modlunky2.ui.trackers.label import Label, RunLabel

# TODO check _MUTUALLY_EXCLUSIVE doesn't contain _HIDES or _ONLY_SHOW_WITH 'pairs'
# TODO check _ONLY_SHOW_WITH things aren't hidden by the labels they require


def test_mossranking_alignment():
    main_speed = [
        ({Label.ANY}, "Any%"),
        ({Label.SUNKEN_CITY}, "Sunken City%"),
        ({Label.LOW, Label.ANY}, "Low%"),
        ({Label.LOW, Label.JUNGLE_TEMPLE, Label.ANY}, "Low% Jungle/Temple"),
        ({Label.PACIFIST, Label.LOW, Label.ANY}, "Pacifist Low%"),
        (
            {Label.CHAIN, Label.CHAIN_LOW, Label.ABZU, Label.SUNKEN_CITY},
            "Chain Low% Abzu",
        ),
        (
            {Label.CHAIN, Label.CHAIN_LOW, Label.DUAT, Label.SUNKEN_CITY},
            "Chain Low% Duat",
        ),
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
    ]
    main_score = [
        ({Label.SCORE, Label.ANY}, "Score"),
        ({Label.SCORE, Label.NO_CO, Label.ANY}, "Score No CO"),
    ]
    misc = [
        ({Label.NO_GOLD, Label.COSMIC_OCEAN}, "No Gold Cosmic Ocean%"),
        ({Label.EGGPLANT, Label.COSMIC_OCEAN}, "Eggplant Cosmic Ocean%"),
        ({Label.TRUE_CROWN, Label.COSMIC_OCEAN}, "True Crown Cosmic Ocean%"),
        (
            {Label.EGGPLANT, Label.TRUE_CROWN, Label.COSMIC_OCEAN},
            "Eggplant True Crown Cosmic Ocean%",
        ),
        ({Label.NO_JETPACK, Label.COSMIC_OCEAN}, "No Jetpack Cosmic Ocean%"),
        ({Label.LOW, Label.COSMIC_OCEAN}, "Low% Cosmic Ocean"),
        (
            {Label.CHAIN, Label.CHAIN_LOW, Label.ABZU, Label.COSMIC_OCEAN},
            "Chain Low% Cosmic Ocean",
        ),
        (
            {Label.CHAIN, Label.CHAIN_LOW, Label.DUAT, Label.COSMIC_OCEAN},
            "Chain Low% Cosmic Ocean",
        ),
        # We accept % after SC even though it doesn't really align
        (
            {Label.NO_TELEPORTER, Label.NO_GOLD, Label.SUNKEN_CITY},
            "No TP No Gold Sunken City%",
        ),
        ({Label.NO_TELEPORTER, Label.NO_GOLD, Label.ANY}, "No TP No Gold"),
        ({Label.LOW, Label.SUNKEN_CITY}, "Low% Sunken City"),
        ({Label.NO_GOLD, Label.SUNKEN_CITY}, "No Gold Sunken City%"),
        (
            {Label.NO_GOLD, Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY},
            "No Gold Sunken City% Abzu",
        ),
        (
            {Label.NO_GOLD, Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY},
            "No Gold Sunken City% Duat",
        ),
        ({Label.NO_GOLD, Label.LOW, Label.SUNKEN_CITY}, "No Gold Low% Sunken City"),
        (
            {
                Label.NO_GOLD,
                Label.CHAIN,
                Label.CHAIN_LOW,
                Label.ABZU,
                Label.SUNKEN_CITY,
            },
            "No Gold Chain Low% Abzu",
        ),
        (
            {
                Label.NO_GOLD,
                Label.CHAIN,
                Label.CHAIN_LOW,
                Label.DUAT,
                Label.SUNKEN_CITY,
            },
            "No Gold Chain Low% Duat",
        ),
        ({Label.EGGPLANT, Label.SUNKEN_CITY}, "Eggplant%"),
        (
            {Label.EGGPLANT, Label.CHAIN, Label.ABZU, Label.SUNKEN_CITY},
            "Abzu Eggplant%",
        ),
        (
            {Label.EGGPLANT, Label.CHAIN, Label.DUAT, Label.SUNKEN_CITY},
            "Duat Eggplant%",
        ),
        ({Label.LOW, Label.EGGPLANT, Label.SUNKEN_CITY}, "Low% Eggplant"),
        (
            {
                Label.CHAIN,
                Label.CHAIN_LOW,
                Label.EGGPLANT,
                Label.ABZU,
                Label.SUNKEN_CITY,
            },
            "Chain Low% Abzu Eggplant",
        ),
        (
            {
                Label.CHAIN,
                Label.CHAIN_LOW,
                Label.EGGPLANT,
                Label.DUAT,
                Label.SUNKEN_CITY,
            },
            "Chain Low% Duat Eggplant",
        ),
        ({Label.NO_GOLD, Label.EGGPLANT, Label.SUNKEN_CITY}, "No Gold Eggplant%"),
        (
            {
                Label.NO_GOLD,
                Label.CHAIN,
                Label.CHAIN_LOW,
                Label.ABZU,
                Label.EGGPLANT,
                Label.SUNKEN_CITY,
            },
            "No Gold Chain Low% Abzu Eggplant",
        ),
        (
            {
                Label.NO_GOLD,
                Label.CHAIN,
                Label.CHAIN_LOW,
                Label.DUAT,
                Label.EGGPLANT,
                Label.SUNKEN_CITY,
            },
            "No Gold Chain Low% Duat Eggplant",
        ),
        ({Label.MILLIONAIRE, Label.ANY}, "Millionaire"),
        ({Label.LOW, Label.MILLIONAIRE, Label.ANY}, "Low% Millionaire"),
        ({Label.NO_TELEPORTER, Label.MILLIONAIRE, Label.ANY}, "No TP Millionaire"),
        ({Label.PACIFIST, Label.ANY}, "Pacifist Any%"),
    ]
    pacifist = [
        ({Label.PACIFIST, Label.SUNKEN_CITY}, "Pacifist Sunken City%"),
        ({Label.PACIFIST, Label.LOW, Label.ANY}, "Pacifist Low%"),
        ({Label.PACIFIST, Label.LOW, Label.SUNKEN_CITY}, "Pacifist Low% Sunken City"),
        (
            {
                Label.PACIFIST,
                Label.CHAIN,
                Label.CHAIN_LOW,
                Label.ABZU,
                Label.SUNKEN_CITY,
            },
            "Pacifist Chain Low% Abzu",
        ),
        (
            {
                Label.PACIFIST,
                Label.CHAIN,
                Label.CHAIN_LOW,
                Label.DUAT,
                Label.SUNKEN_CITY,
            },
            "Pacifist Chain Low% Duat",
        ),
        ({Label.PACIFIST, Label.EGGPLANT, Label.SUNKEN_CITY}, "Pacifist Eggplant%"),
        ({Label.NO_GOLD, Label.PACIFIST, Label.ANY}, "No Gold Pacifist"),
        (
            {Label.NO_GOLD, Label.PACIFIST, Label.SUNKEN_CITY},
            "No Gold Pacifist Sunken City%",
        ),
        (
            {Label.NO_GOLD, Label.PACIFIST, Label.LOW, Label.ANY},
            "No Gold Pacifist Low%",
        ),
        (
            {Label.NO_GOLD, Label.PACIFIST, Label.LOW, Label.SUNKEN_CITY},
            "No Gold Pacifist Low% Sunken City",
        ),
        (
            {Label.NO_GOLD, Label.PACIFIST, Label.EGGPLANT, Label.SUNKEN_CITY},
            "No Gold Pacifist Eggplant%",
        ),
    ]
    for labels, text in main_speed + main_score + misc + pacifist:
        run_label = RunLabel(labels)
        assert run_label.text(hide_early=False) == text
