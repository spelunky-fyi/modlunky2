from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set, FrozenSet

from modlunky2.config import SaveableCategory  # For saving


@dataclass
class LabelMetadata:
    text: str
    start: bool = False
    add_ok: Optional[bool] = None
    hide_early: Optional[bool] = None
    percent_priority: Optional[int] = None
    terminus: bool = False

    def __post_init__(
        self,
    ) -> None:
        if self.add_ok is None:
            self.add_ok = not self.start
        if self.hide_early is None:
            self.hide_early = self.start


# Order of values is the order they'll appear in
class Label(Enum):
    NO_JETPACK = LabelMetadata("No Jetpack", start=True)
    NO_TELEPORTER = LabelMetadata("No TP", start=True)
    NO_GOLD = LabelMetadata("No Gold", start=True)
    PACIFIST = LabelMetadata("Pacifist", start=True)
    CHAIN = LabelMetadata("Chain")
    LOW = LabelMetadata("Low", start=True, hide_early=False, percent_priority=5)
    ICE_CAVES_SHORTCUT = LabelMetadata("Ice Caves Shortcut", percent_priority=0)
    NO = LabelMetadata("No", start=True, hide_early=False, percent_priority=5)
    ANY = LabelMetadata(
        "Any", start=True, hide_early=False, percent_priority=4, terminus=True
    )
    SUNKEN_CITY = LabelMetadata("Sunken City", percent_priority=4, terminus=True)
    EGGPLANT = LabelMetadata("Eggplant", percent_priority=3)
    DEATH = LabelMetadata("Death", percent_priority=2, terminus=True)
    JUNGLE_TEMPLE = LabelMetadata("Jungle/Temple")
    VOLCANA_TEMPLE = LabelMetadata("Volcana/Temple")
    DUAT = LabelMetadata("Duat", percent_priority=1)
    ABZU = LabelMetadata("Abzu", percent_priority=1)
    MILLIONAIRE = LabelMetadata("Millionaire")
    TRUE_CROWN = LabelMetadata("True Crown")
    COSMIC_OCEAN = LabelMetadata("Cosmic Ocean", percent_priority=4, terminus=True)
    SCORE = LabelMetadata("Score")
    NO_CO = LabelMetadata("No CO", start=True, hide_early=False, add_ok=True)

    @classmethod
    def from_saveable_category(cls, sc):
        mapping = {
            SaveableCategory.NO: Label.NO,
            SaveableCategory.NO_GOLD: Label.NO_GOLD,
            SaveableCategory.PACIFIST: Label.PACIFIST,
        }

        return mapping[sc]


@dataclass(frozen=True)
class _CachedText:
    hide_early: bool
    text: str
    excluded: FrozenSet[Label]


class RunLabel:
    _STARTING = frozenset([k for k in Label if k.value.start])
    _HIDE_EARLY = frozenset([k for k in Label if k.value.hide_early])
    _TERMINI = frozenset([k for k in Label if k.value.terminus])

    # Something's broken if a run supposedly meets the criteria for more than one of these.
    # We tolerate CO and No CO together to simplify updating the terminus.
    _MUTUALLY_EXCLUSIVE = frozenset(
        [
            frozenset(_TERMINI),
            frozenset({Label.ABZU, Label.DUAT}),
        ]
    )

    # Some labels are only shown in conjunction with another.
    # We show the key if any label in the value is present.
    _ONLY_SHOW_WITH = defaultdict(set)
    _ONLY_SHOW_WITH[Label.NO_JETPACK] |= {Label.COSMIC_OCEAN}
    _ONLY_SHOW_WITH[Label.JUNGLE_TEMPLE] |= {Label.LOW}
    _ONLY_SHOW_WITH[Label.NO_CO] |= {Label.SCORE}

    # Some labels hide others, e.g. we want "Low%" not "Low% Any".
    # If the key is present, hide all of the labels in the value
    _HIDES = defaultdict(set)
    _HIDES[Label.EGGPLANT] |= {Label.SUNKEN_CITY}
    _HIDES[Label.LOW] |= {Label.NO_TELEPORTER, Label.NO_JETPACK, Label.ANY}
    _HIDES[Label.CHAIN] |= {Label.JUNGLE_TEMPLE, Label.VOLCANA_TEMPLE}
    _HIDES[Label.NO_GOLD] |= {Label.ANY}
    _HIDES[Label.PACIFIST] |= {Label.ANY}
    _HIDES[Label.MILLIONAIRE] |= {Label.ANY}
    _HIDES[Label.COSMIC_OCEAN] |= {
        Label.NO_TELEPORTER,
        Label.ABZU,
        Label.DUAT,
    }

    # Score hides almost everything
    _SCORE_LABELS = {Label.SCORE, Label.NO_CO}

    def __init__(self, starting=None) -> None:
        self._set: Set[Label] = (
            set(self._STARTING) if starting is None else set(starting)
        )

        termini = list(self._set & self._TERMINI)
        if len(termini) != 1:
            raise ValueError(f"Expected exactly 1 terminus, found {termini}")
        self._terminus = termini[0]
        self._cached_text: Optional[_CachedText] = None

    def add(self, label: Label):
        if not label.value.add_ok:
            raise ValueError(f"Attempted to add label {label}")
        if label.value.terminus:
            raise ValueError(f"Attempted to add a terminus, {label}")

        # Avoid re-validating if nothing's changed
        if label in self._set:
            return
        self._set.add(label)
        self._modified()

    def discard(self, *labels: Label):
        # Avoid re-validating if nothing's changed
        modified = False
        for label in labels:
            if label.value.terminus:
                raise ValueError(f"Attempted to discard a terminus, {label}")

            if label not in self._set:
                continue
            modified = True
            self._set.remove(label)

        if modified:
            self._modified()

    def set_terminus(self, label: Label):
        if not label.value.terminus:
            raise ValueError(f"Attempted to use {label} as a terminus")
        if self._terminus == label:
            return
        self._set.remove(self._terminus)
        self._set.add(label)
        self._terminus = label
        self._modified()

    def _modified(self):
        self._cached_text = None
        self._validate()

    def _validate(self):
        # Note that we're validating while the run is in progress.
        # For example, we should allow "Chain" without "Abzu" or "Duat".
        for mut in self._MUTUALLY_EXCLUSIVE:
            inter = mut & self._set
            if len(inter) > 1:
                raise Exception(f"Found mutually-exclusive labels {inter}")

    def _visible(
        self, hide_early: bool, excluded_categories: FrozenSet[Label]
    ) -> Set[Label]:
        vis = set(self._set)
        vis -= excluded_categories

        if Label.SCORE in vis:
            vis &= self._SCORE_LABELS

        if hide_early:
            vis -= self._HIDE_EARLY

        for needle, to_hide in self._HIDES.items():
            if needle in vis:
                vis -= to_hide

        for needle, need in self._ONLY_SHOW_WITH.items():
            if needle in vis and vis.isdisjoint(need):
                vis.discard(needle)

        # Handle No% hiding No Gold. We do this here to avoid multiple passes over _HIDES.
        if Label.NO in vis:
            vis.discard(Label.NO_GOLD)

        # Handle "Chain Low% Abzu" vs "Sunken City% Abzu"
        if not self._set.isdisjoint({Label.ABZU, Label.DUAT}):
            vis.discard(Label.SUNKEN_CITY)
            if Label.LOW not in vis:
                vis.discard(Label.CHAIN)

        # Handle ICS% and No% hiding Low%. We do this here to avoid multiple passes over _HIDES/duplicating _HIDES[Label.LOW]
        if not vis.isdisjoint({Label.NO, Label.ICE_CAVES_SHORTCUT}):
            vis.discard(Label.LOW)
            vis -= self._HIDES[Label.LOW]

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
                    f"Showing labels with equal percent_priority {candidate} {found}"
                )
            elif candidate.value.percent_priority > found.value.percent_priority:
                found = candidate

        return found

    def text(self, hide_early: bool, excluded_categories: Set[SaveableCategory]) -> str:
        excluded = frozenset(
            [Label.from_saveable_category(sc) for sc in excluded_categories]
        )
        if (
            self._cached_text is not None
            and self._cached_text.hide_early == hide_early
            and self._cached_text.excluded == excluded
        ):
            return self._cached_text.text

        vis = self._visible(hide_early, excluded)
        perc = self._percent(vis)
        parts = []

        for candidate in Label:
            if candidate not in vis:
                continue
            if perc is candidate:
                parts.append(candidate.value.text + "%")
            else:
                parts.append(candidate.value.text)

        text = " ".join(parts)
        self._cached_text = _CachedText(
            hide_early=hide_early, text=text, excluded=excluded
        )
        return text
