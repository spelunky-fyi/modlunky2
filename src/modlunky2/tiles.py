from enum import Enum
from typing import List
from logging import getLogger
from PIL import ImageTk, Image

logger = getLogger(__name__)


class TileCodes(Enum):
    """
    Pulled the codes from "tilecodes.txt" and made an enum, using the `chr(##)` notation
    to make it clearer what the character is since a lot of them head towards unicode
    land
    """

    empty = chr(97)
    chunk_air = chr(98)
    chunk_ground = chr(99)
    chunk_door = chr(100)
    floor = chr(101)
    styled_floor = chr(102)
    minewood_floor_noreplace = chr(103)
    minewood_floor = chr(104)
    floor_hard = chr(105)
    adjacent_floor = chr(106)
    arrow_trap = chr(107)
    woodenlog_trap = chr(108)
    woodenlog_trap_ceiling = chr(109)
    idol_floor = chr(110)
    idol = chr(111)
    door = chr(112)
    entrance = chr(113)
    exit = chr(114)
    starting_exit = chr(115)
    door_drop_held = chr(116)
    entrance_shortcut = chr(117)
    cookfire = chr(118)
    door2_secret = chr(119)
    ghist_door2 = chr(217)
    spikes = chr(121)
    spring_trap = chr(122)
    push_block = chr(65)
    litwalltorch = chr(66)
    door2 = chr(67)
    pen_floor = chr(68)
    pen_locked_door = chr(69)
    yang = chr(70)
    turkey = chr(71)
    platform = chr(72)
    ladder = chr(73)
    ladder_plat = chr(74)
    locked_door = chr(75)
    key = chr(76)
    altar = chr(77)
    snake = chr(78)
    cobra = chr(79)
    scorpion = chr(80)
    caveman_asleep = chr(81)
    caveman = chr(82)
    haunted_corpse = chr(83)
    cavemanboss = chr(84)
    shop_woodwall = chr(85)
    minewood_floor_hanging_hide = chr(86)
    shop_sign = chr(87)
    wanted_poster = chr(216)
    shop_door = chr(89)
    lamp_hang = chr(90)
    shop_wall = chr(48)
    shop_item = chr(49)
    challenge_waitroom = chr(50)
    die = chr(51)
    shopkeeper_vat = chr(52)
    merchant = chr(53)
    shopkeeper = chr(54)
    cavemanshopkeeper = chr(55)
    ghist_shopkeeper = chr(56)
    sleeping_hiredhand = chr(57)
    rock = chr(48)
    lockedchest = chr(33)
    cursed_pot = chr(64)
    pot = chr(35)
    treasure_vaultchest = chr(36)
    treasure_chest = chr(37)
    crate = chr(94)
    crate_bombs = chr(38)
    crate_ropes = chr(42)
    crate_parachute = chr(40)
    mattock = chr(41)
    crossbow = chr(91)
    houyibow = chr(93)
    lightarrow = chr(124)
    goldbars = chr(123)
    littorch = chr(125)
    bush_block = chr(95)
    walltorch = chr(43)
    autowalltorch = chr(45)
    coffin = chr(61)
    timed_powder_keg = chr(92)
    powder_keg = chr(47)
    chainandblocks_ceiling = chr(44)
    chain_ceiling = chr(46)
    conveyorbelt_left = chr(60)
    conveyorbelt_right = chr(62)
    drill = chr(59)
    udjat_socket = chr(39)
    nonreplaceable_babylon_floor = chr(58)
    lava = chr(96)
    lavamander = chr(126)
    robot = chr(192)
    imp = chr(193)
    vlad_floor = chr(194)
    crown_statue = chr(195)
    vlad = chr(196)
    jungle_floor = chr(197)
    tree_base = chr(256)
    vine = chr(258)
    growable_vine = chr(259)
    thorn_vine = chr(198)
    jungle_spear_trap = chr(200)
    sister = chr(201)
    mantrap = chr(202)
    giant_spider = chr(203)
    tikiman = chr(204)
    witchdoctor = chr(205)
    mosquito = chr(206)
    beehive_floor = chr(207)
    honey_upwards = chr(208)
    honey_downwards = chr(209)
    stone_floor = chr(210)
    vault_wall = chr(211)
    pillar = chr(212)
    stagnant_lava = chr(213)
    olmec = chr(214)
    ankh = chr(218)
    pagoda_floor = chr(219)
    pagoda_platform = chr(220)
    climbing_pole = chr(221)
    growable_climbing_pole = chr(223)
    excalibur_stone = chr(257)
    fountain_head = chr(224)
    slidingwall_switch = chr(225)
    slidingwall_ceiling = chr(226)
    bigspear_trap = chr(227)
    giantclam = chr(228)
    jiangshi = chr(229)
    octopus = chr(230)
    hermitcrab = chr(231)
    treasure = chr(232)
    shop_pagodawall = chr(233)
    madametusk = chr(234)
    bodyguard = chr(235)
    kingu = chr(236)
    tiamat = chr(237)
    water = chr(238)
    coarse_water = chr(239)
    fountain_drain = chr(240)
    temple_floor = chr(241)
    quicksand = chr(242)
    crushtrap = chr(243)
    crushtraplarge = chr(244)
    catmummy = chr(245)
    crocman = chr(246)
    mummy = chr(247)
    sorceress = chr(248)
    necromancer = chr(249)
    anubis = chr(250)
    duat_floor = chr(251)
    empress_grave = chr(252)
    ammit = chr(253)
    icefloor = chr(254)
    falling_platform = chr(255)
    upsidedown_spikes = chr(199)
    landmine = chr(161)
    thinice = chr(162)
    yeti = chr(163)
    alien = chr(164)
    ufo = chr(165)
    mothership_floor = chr(166)
    moai_statue = chr(167)
    factory_generator = chr(168)
    alien_generator = chr(169)
    eggplant_altar = chr(170)
    empty_mech = chr(171)
    alienqueen = chr(172)
    plasma_cannon = chr(174)
    babylon_floor = chr(175)
    mushroom_base = chr(176)
    crushing_elevator = chr(177)
    elevator = chr(178)
    laser_trap = chr(179)
    spark_trap = chr(184)
    timed_forcefield = chr(185)
    forcefield = chr(186)
    forcefield_top = chr(187)
    ushabti = chr(188)
    olmite = chr(189)
    lamassu = chr(190)
    olmecship = chr(191)
    palace_floor = chr(880)
    palace_entrance = chr(881)
    palace_table = chr(883)
    palace_table_tray = chr(886)
    palace_chandelier = chr(887)
    palace_candle = chr(891)
    palace_bookcase = chr(260)
    sunken_floor = chr(261)
    bone_block = chr(262)
    mother_statue = chr(263)
    eggplant_door = chr(264)
    pipe = chr(265)
    regenerating_block = chr(266)
    sticky_trap = chr(267)
    giant_frog = chr(270)
    guts_floor = chr(271)
    jumpdog = chr(272)
    minister = chr(273)
    yama = chr(274)
    tomb_floor = chr(275)
    oldhunter = chr(276)
    thief = chr(277)
    eggplant_child = chr(278)
    storage_guy = chr(279)
    storage_floor = chr(280)
    cog_floor = chr(281)
    potofgold = chr(282)
    clover = chr(283)
    cat = chr(284)
    tv = chr(285)
    couch = chr(286)
    shortcut_station_banner = chr(287)
    construction_sign = chr(288)
    surface_floor = chr(289)
    surface_hidden_floor = chr(290)
    dresser = chr(291)
    bunkbed = chr(292)
    singlebed = chr(293)
    diningtable = chr(294)
    sidetable = chr(295)
    chair_looking_left = chr(296)
    chair_looking_right = chr(297)
    dog_sign = chr(298)
    telescope = chr(299)
    zoo_exhibit = chr(300)
    dm_spawn_point = chr(301)
    idol_hold = chr(302)


class Tile:
    __slots__ = ["code", "sprite", "_texture"]

    def __init__(self, code: TileCodes, sprite: Image.Image):
        self.code = code
        self.sprite = sprite
        self._texture = None

    @property
    def texture(self):
        """
        This is so that we can return the texture when needed, but still be able to
        work with the class objects outside of Tkinter.
        """

        if not self._texture:
            try:
                self._texture = ImageTk.PhotoImage(self.sprite)
            except RuntimeError:
                logger.warning(f"Unable to create a ImageTk outside of a Tk window")
                return None
        return self._texture

    def __repr__(self):
        return f"Tile({self.code.name})"

    def __str__(self):
        return self.__repr__()


def make_sprites(
    sprite_sheet: Image.Image, sprite_width: int = 50, sprite_height: int = 50
) -> List[Image.Image]:
    # Check if the sprite width/height is likely to be valid
    if (
        sprite_sheet.width % sprite_width != 0
        or sprite_sheet.height % sprite_height != 0
    ):
        raise ValueError(
            "Sprite Sheet must be evenly divisible by the height and width"
        )
    sprites = []
    for row in make_rows(sprite_sheet, sprite_height):
        # Using the terminology from the Pillow docs where a bbox is a four-tuple of
        # (left, upper, right, lower)
        left = 0
        while (left + sprite_width) <= sprite_sheet.width:
            sprites.append(row.crop((left, 0, left + sprite_width, sprite_height)))
            left += sprite_width
    return sprites


def make_rows(sprite_sheet: Image.Image, sprite_height: int = 50) -> List[Image.Image]:
    rows = []
    # Using the terminology from the Pillow docs where a bbox is a four-tuple of
    # (left, upper, right, lower)
    upper = 0
    while (upper + sprite_height) <= sprite_sheet.height:
        rows.append(
            sprite_sheet.crop((0, upper, sprite_sheet.width, upper + sprite_height))
        )
        upper += sprite_height
    return rows


def make_tiles(sprites: List[Image.Image]) -> List[Tile]:
    # This is assuming that the TileCodes and the sprites are in the correct order
    # This behavior matches how the tiles and sprites are getting paired up already
    # Also we are getting some blank squares from the sprite sheet, but zip will bail
    # silently once one of the iterables runs out
    tile_sprite_pairs = list(zip(TileCodes, sprites))
    tiles = []
    for tile_enum, sprite in tile_sprite_pairs:
        tiles.append(Tile(code=tile_enum, sprite=sprite))
    return tiles
