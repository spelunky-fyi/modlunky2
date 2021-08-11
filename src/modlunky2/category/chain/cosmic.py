from typing import Set

from modlunky2.category.chain.common import (
    ChainMixin,
    ChainStepper,
)
from modlunky2.mem.entities import EntityType
from modlunky2.mem.state import Screen, State, WinState


class CosmicOceanChain(ChainMixin):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls.__name__, cls().collect_bow)

    def collect_bow(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_HOUYIBOW in player_item_types:
            return self.in_progress(self.carry_bow_to_hundun)

        if game_state.world > 2:
            return self.failed()

        return self.unstarted()

    def carry_bow_to_hundun(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        if game_state.win_state is not WinState.NO_WIN:
            return self.failed()

        world_level = (game_state.world, game_state.level)
        if world_level > (7, 3):
            return self.in_progress(self.win_via_co)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.carry_bow_to_hundun)

        if (
            EntityType.ITEM_HOUYIBOW in player_item_types
        ) or self.some_companion_has_item(game_state, EntityType.ITEM_HOUYIBOW):
            return self.in_progress(self.carry_bow_to_hundun)

        if world_level < (7, 1) and (
            EntityType.ITEM_HOUYIBOW in game_state.waddler_storage
        ):
            return self.in_progress(self.carry_bow_to_hundun)

        return self.failed()

    def win_via_co(self, game_state: State, _: Set[EntityType]):
        if game_state.win_state in (WinState.NO_WIN, WinState.COSMIC_OCEAN):
            return self.in_progress(self.win_via_co)

        return self.failed()
