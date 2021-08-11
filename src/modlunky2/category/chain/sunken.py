from abc import ABC, abstractmethod
from typing import Set

from modlunky2.category.chain.common import (
    ChainMixin,
    ChainStepper,
    ChainStepEvaluator,
    ChainStepResult,
)
from modlunky2.mem.entities import EntityType
from modlunky2.mem.state import Screen, State, Theme, WinState


class SunkenChain(ChainMixin, ABC):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls.__name__, cls().collect_eye_or_headwear)

    @property
    @abstractmethod
    def world41_theme(self) -> Theme:
        pass

    @property
    @abstractmethod
    def world44_theme(self) -> Theme:
        pass

    @property
    @abstractmethod
    def world4_item_step(self) -> ChainStepEvaluator:
        pass

    def collect_eye_or_headwear(
        self, game_state: State, player_item_types: Set[EntityType]
    ) -> ChainStepResult:
        if EntityType.ITEM_POWERUP_UDJATEYE in player_item_types:
            return self.in_progress(self.collect_headwear)

        if (
            EntityType.ITEM_POWERUP_HEDJET in player_item_types
            or EntityType.ITEM_POWERUP_CROWN in player_item_types
        ):
            return self.in_progress(self.collect_ankh)

        if game_state.world > 2:
            return self.failed()

        return self.unstarted()

    def collect_headwear(
        self, game_state: State, player_item_types: Set[EntityType]
    ) -> ChainStepResult:
        if (
            EntityType.ITEM_POWERUP_HEDJET in player_item_types
            or EntityType.ITEM_POWERUP_CROWN in player_item_types
        ):
            return self.in_progress(self.collect_ankh)

        if game_state.world > 2:
            return self.failed()

        return self.in_progress(self.collect_headwear)

    def collect_ankh(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_ANKH in player_item_types:
            return self.in_progress(self.visit_world41_theme)

        if game_state.world > 3:
            return self.failed()

        return self.in_progress(self.collect_ankh)

    def visit_world41_theme(self, game_state: State, _: Set[EntityType]):
        if game_state.theme == self.world41_theme:
            return self.in_progress(self.world4_item_step)

        if game_state.world > 3:
            return self.failed()

        return self.in_progress(self.visit_world41_theme)

    def visit_world44_theme(self, game_state: State, _: Set[EntityType]):
        if game_state.theme == self.world44_theme:
            return self.in_progress(self.collect_tablet)

        if (game_state.world, game_state.level) > (4, 3):
            return self.failed()

        return self.in_progress(self.visit_world44_theme)

    def collect_tablet(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_POWERUP_TABLETOFDESTINY in player_item_types:
            return self.in_progress(self.carry_ushabti_to_63)

        if game_state.world > 4:
            return self.failed()

        return self.in_progress(self.collect_tablet)

    def carry_ushabti_to_63(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        world_level_screen = (game_state.world, game_state.level, game_state.screen)
        if world_level_screen != (6, 2, Screen.LEVEL_TRANSITION):
            return self.in_progress(self.carry_ushabti_to_63)

        if (
            EntityType.ITEM_USHABTI in player_item_types
            or self.some_companion_has_item(game_state, EntityType.ITEM_USHABTI)
        ):
            return self.in_progress(self.win_via_hundun_or_co)

        return self.failed()

    def win_via_hundun_or_co(self, game_state: State, _: Set[EntityType]):
        if game_state.win_state is WinState.TIAMAT:
            return self.failed()

        return self.in_progress(self.win_via_hundun_or_co)


class AbzuChain(SunkenChain):
    world41_theme = Theme.TIDE_POOL
    world44_theme = Theme.ABZU

    @property
    def world4_item_step(self):
        return self.collect_excalibur

    def collect_excalibur(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_EXCALIBUR in player_item_types:
            return self.in_progress(self.visit_world44_theme)

        world_level = (game_state.world, game_state.level)
        if world_level > (4, 2):
            return self.failed()

        return self.in_progress(self.collect_excalibur)


class DuatChain(SunkenChain):
    world41_theme = Theme.TEMPLE
    world44_theme = Theme.DUAT

    @property
    def world4_item_step(self):
        return self.carry_scepter_to_42

    def carry_scepter_to_42(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        # The ankh is required to reach Duat
        if EntityType.ITEM_POWERUP_ANKH not in player_item_types:
            return self.failed()

        # Scepter must be carried into 4, 2
        world_level_screen = (game_state.world, game_state.level, game_state.screen)
        if world_level_screen != (4, 1, Screen.LEVEL_TRANSITION):
            return self.in_progress(self.carry_scepter_to_42)

        if (
            EntityType.ITEM_SCEPTER in player_item_types
            or self.some_companion_has_item(game_state, EntityType.ITEM_SCEPTER)
        ):
            return self.in_progress(self.visit_city_of_gold)

        return self.failed()

    def visit_city_of_gold(self, game_state: State, player_item_types: Set[EntityType]):
        # The ankh is required to reach Duat
        if EntityType.ITEM_POWERUP_ANKH not in player_item_types:
            return self.failed()

        if game_state.theme is Theme.CITY_OF_GOLD:
            return self.in_progress(self.keep_ankh)

        if (game_state.world, game_state.level) > (4, 2):
            return self.failed()

        return self.in_progress(self.visit_city_of_gold)

    def keep_ankh(self, game_state: State, player_item_types: Set[EntityType]):
        # We won't have the Ankh on our way to Duat
        world_level_screen = (game_state.world, game_state.level, game_state.screen)
        if world_level_screen == (4, 3, Screen.LEVEL_TRANSITION):
            return self.in_progress(self.visit_world44_theme)

        # The player is destroyed when sacrificed
        if game_state.items.players[0] is None:
            return self.in_progress(self.keep_ankh)

        if EntityType.ITEM_POWERUP_ANKH not in player_item_types:
            return self.failed()

        return self.in_progress(self.keep_ankh)
