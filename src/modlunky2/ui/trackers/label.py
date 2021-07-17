from collections import defaultdict
from enum import Enum
from typing import Optional, Set


class LabelMetadata:
    def __init__(
        self, label, start=False, hide_early=None, percent_priority=None, terminus=False
    ) -> None:
        self.label = label
        self.start = start
        self.hide_early = start if hide_early is None else hide_early
        self.percent_priority = percent_priority
        self.terminus = terminus


# Order of values is the order they'll appear in
class Label(Enum):
    NO_JETPACK = LabelMetadata("No Jetpack", start=True)
    NO_TELEPORTER = LabelMetadata("No TP", start=True)
    NO_GOLD = LabelMetadata("No Gold", start=True)
    PACIFIST = LabelMetadata("Pacifist", start=True)
    CHAIN = LabelMetadata("Chain")
    # TODO shift complexity of chain low into here
    CHAIN_LOW = LabelMetadata("Chain Low", percent_priority=3)
    LOW = LabelMetadata("Low", start=True, hide_early=False, percent_priority=3)
    ANY = LabelMetadata(
        "Any", start=True, hide_early=False, percent_priority=2, terminus=True
    )
    SUNKEN_CITY = LabelMetadata("Sunken City", percent_priority=2, terminus=True)
    DEATH = LabelMetadata("Death", percent_priority=2, terminus=True)
    JUNGLE_TEMPLE = LabelMetadata("Jungle/Temple")
    DUAT = LabelMetadata("Duat")
    ABZU = LabelMetadata("Abzu")
    MILLIONAIRE = LabelMetadata("Millionaire")
    EGGPLANT = LabelMetadata("Eggplant", percent_priority=1)
    TRUE_CROWN = LabelMetadata("True Crown")
    COSMIC_OCEAN = LabelMetadata("Cosmic Ocean", percent_priority=2, terminus=True)
    SCORE = LabelMetadata("Score")
    NO_CO = LabelMetadata("No CO", start=True)


class RunLabel:
    _STARTING = frozenset([k for k in Label if k.value.start])
    _HIDE_EARLY = frozenset([k for k in Label if k.value.hide_early])
    _TERMINI = frozenset([k for k in Label if k.value.terminus])

    # Something's broken if a run supposedly meets the criteria for more than one of these
    _MUTUALLY_EXCLUSIVE = frozenset(
        [
            frozenset(_TERMINI),
            frozenset({Label.CHAIN, Label.LOW}),
            frozenset({Label.CHAIN_LOW, Label.LOW}),
            frozenset({Label.ABZU, Label.DUAT}),
            frozenset({Label.NO_GOLD, Label.MILLIONAIRE}),
            frozenset({Label.COSMIC_OCEAN, Label.NO_CO}),
        ]
    )

    # Some labels are only shown in conjunction with another
    _ONLY_SHOW_WITH = defaultdict(set)
    _ONLY_SHOW_WITH[Label.NO_JETPACK] |= {Label.NO_JETPACK}
    _ONLY_SHOW_WITH[Label.JUNGLE_TEMPLE] |= {Label.LOW}
    _ONLY_SHOW_WITH[Label.ABZU] |= {Label.CHAIN, Label.CHAIN_LOW}
    _ONLY_SHOW_WITH[Label.DUAT] |= {Label.CHAIN, Label.CHAIN_LOW}
    _ONLY_SHOW_WITH[Label.NO_CO] |= {Label.SCORE}

    # Some labels hide others, e.g. we want "Low%" not "Low% Any"
    _HIDES = defaultdict(set)
    _HIDES[Label.EGGPLANT] |= {Label.SUNKEN_CITY}
    _HIDES[Label.ABZU] |= {Label.CHAIN}
    _HIDES[Label.DUAT] |= {Label.CHAIN}

    _HIDES[Label.CHAIN_LOW] |= {Label.CHAIN, Label.SUNKEN_CITY}
    _HIDES[Label.LOW] |= {Label.ANY}

    _HIDES[Label.NO_GOLD] |= {Label.ANY}
    _HIDES[Label.MILLIONAIRE] |= {Label.ANY}
    _HIDES[Label.COSMIC_OCEAN] |= {
        Label.NO_TELEPORTER,
        Label.CHAIN,
        Label.ABZU,
        Label.DUAT,
    }

    # Score hides almost
    _HIDES[Label.SCORE] |= set(Label) - {Label.SCORE, Label.NO_CO}

    # Low% implies No TP and No Jetpack
    for k in (Label.CHAIN_LOW, Label.LOW):
        _HIDES[k] |= {Label.NO_TELEPORTER, Label.NO_JETPACK}

    def __init__(self, starting=None) -> None:
        self._set: Set[Label] = (
            set(self._STARTING) if starting is None else set(starting)
        )

        termini = list(self._set & self._TERMINI)
        if len(termini) != 1:
            raise ValueError("Expected exactly 1 terminus, found {}".format(termini))
        self._terminus = termini[0]
        self._cached_text: Optional[str] = None

    def add(self, label: Label):
        if label.value.start:
            raise ValueError("Attempted to add starting label {}".format(label))
        if label.value.terminus:
            raise ValueError("Attempted to add a terminus, {}".format(label))

        # Avoid re-validating if nothing's changed
        if label in self._set:
            return
        self._set.add(label)
        self._modified()

    def discard(self, label: Label):
        if label.value.terminus:
            raise ValueError("Attempted to discard a terminus, {}".format(label))

        # Avoid re-validating if nothing's changed
        if label not in self._set:
            return
        self._set.remove(label)
        self._modified()

    def set_terminus(self, label: Label):
        if not label.value.terminus:
            raise ValueError("Attempted to use {} as a terminus".format(label))
        self._set.remove(self._terminus)
        self._set.add(label)
        self._terminus = label
        self._modified()

    def _modified(self):
        self._cached_text = None
        self._validate()

    def _validate(self):
        # Note that we're validating while the run is in progress.
        # For example, we should allow "Chain Low%" without "Abzu" or "Duat".
        for mut in self._MUTUALLY_EXCLUSIVE:
            inter = mut & self._set
            if len(inter) > 1:
                raise Exception("Found mutually-exclusive labels {}".format(inter))

    def _visible(self, hide_early) -> Set[Label]:
        vis = set(self._set)

        for needle, to_hide in self._HIDES.items():
            if needle in self._set:
                vis -= to_hide

        for needle, need in self._ONLY_SHOW_WITH.items():
            if needle not in self._set:
                continue
            if self._set.isdisjoint(need):
                vis.discard(needle)

        if hide_early:
            vis -= self._HIDE_EARLY

        return vis

    @classmethod
    def _percent(cls, labels: Set[Label]) -> Optional[Label]:
        found = None
        for candidate in labels:
            if candidate.value.percent_priority is None:
                continue

            if found is None:
                found = candidate
            elif candidate.value.percent_priority == found.value.percent_priority:
                raise Exception(
                    "Showing labels with equal percent_priority {} {}".format(
                        candidate, found
                    )
                )
            elif candidate.value.percent_priority > found.value.percent_priority:
                found = candidate

        return found

    def text(self, hide_early) -> str:
        if self._cached_text is not None:
            return self._cached_text

        vis = self._visible(hide_early)
        perc = self._percent(vis)
        parts = []

        for candidate in Label:
            if candidate not in vis:
                continue
            if perc is candidate:
                parts.append(candidate.value.label + "%")
            else:
                parts.append(candidate.value.label)

        self._cached_text = " ".join(parts)
        return self._cached_text
