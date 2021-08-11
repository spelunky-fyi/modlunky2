import logging
from typing import Set

from modlunky2.category.chain.common import (
    ChainMixin,
    ChainStepper,
)
from modlunky2.mem.entities import EntityType
from modlunky2.mem.state import Screen, State, Theme

logger = logging.getLogger("modlunky2")


class EggplantChain(ChainMixin):
    @classmethod
    def make_stepper(cls) -> ChainStepper:
        return ChainStepper(cls.__name__, cls().collect_eggplant)

    def collect_eggplant(self, game_state: State, player_item_types: Set[EntityType]):
        if EntityType.ITEM_EGGPLANT in player_item_types:
            return self.in_progress(self.carry_eggplant_to_51)

        # It's possible to collect the child without the eggplant
        if game_state.world == 5 and self.some_companion_is(
            game_state, EntityType.CHAR_EGGPLANT_CHILD
        ):
            return self.in_progress(self.guide_eggplant_child_to_71)

        # It's possible a companion collected the eggplant
        if (
            game_state.screen is Screen.LEVEL_TRANSITION
            and self.some_companion_has_item(game_state, EntityType.ITEM_EGGPLANT)
        ):
            return self.in_progress(self.carry_eggplant_to_51)

        if game_state.world > 5:
            return self.failed()

        return self.unstarted()

    def carry_eggplant_to_51(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        if game_state.world > 4:
            return self.in_progress(self.collect_eggplant_child)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.carry_eggplant_to_51)

        if (
            EntityType.ITEM_EGGPLANT in player_item_types
            or EntityType.ITEM_EGGPLANT in game_state.waddler_storage
            or self.some_companion_has_item(game_state, EntityType.ITEM_EGGPLANT)
        ):
            return self.in_progress(self.carry_eggplant_to_51)

        # We can get another eggplant
        return self.unstarted()

    def collect_eggplant_child(self, game_state: State, _: Set[EntityType]):
        if self.some_companion_is(game_state, EntityType.CHAR_EGGPLANT_CHILD):
            return self.in_progress(self.guide_eggplant_child_to_71)

        if game_state.world > 5:
            return self.failed()

        return self.in_progress(self.collect_eggplant_child)

    def guide_eggplant_child_to_71(self, game_state: State, _: Set[EntityType]):
        world_level = (game_state.world, game_state.level)
        if world_level > (7, 1):
            return self.in_progress(self.visit_eggplant_world)

        if game_state.screen is not Screen.LEVEL_TRANSITION:
            return self.in_progress(self.guide_eggplant_child_to_71)

        # We won't have the child during the 7-1 transition
        if world_level == (7, 1):
            return self.in_progress(self.visit_eggplant_world)

        if self.some_companion_is(game_state, EntityType.CHAR_EGGPLANT_CHILD):
            return self.in_progress(self.guide_eggplant_child_to_71)

        return self.failed()

    def visit_eggplant_world(self, game_state: State, _: Set[EntityType]):
        if game_state.theme is Theme.EGGPLANT_WORLD:
            return self.in_progress(self.collect_eggplant_crown)

        if (game_state.world, game_state.level) > (7, 1):
            return self.failed()

        return self.in_progress(self.visit_eggplant_world)

    def collect_eggplant_crown(
        self, game_state: State, player_item_types: Set[EntityType]
    ):
        if EntityType.ITEM_POWERUP_EGGPLANTCROWN in player_item_types:
            return self.in_progress(self.success)

        if (game_state.world, game_state.level) > (7, 2):
            return self.failed()

        return self.in_progress(self.collect_eggplant_crown)

    def success(self, _unused1: State, _unused2: Set[EntityType]):
        # Eggplant can't fail once you have the crown
        return self.in_progress(self.success)
