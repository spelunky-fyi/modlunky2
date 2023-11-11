import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageTk

class TextureUtil():
    def __init__(self, sprite_fetcher):
        self.sprite_fetcher = sprite_fetcher

    @staticmethod
    def adjust_texture_xy(width, height, mode, scale=50):
        # slight adjustments of textures for tile preview
        # 1 = lower half tile
        # 2 = draw from bottom left
        # 3 = center
        # 4 = center to the right
        # 5 = draw bottom left + raise 1 tile
        # 6 = position doors
        # 7 = draw bottom left + raise half tile
        # 8 = draw bottom left + lower 1 tile.
        # 9 = draw bottom left + raise 1 tile + move left 1.5 tiles.
        # 10 = draw bottom left + raise 2 tile.
        # 11 = move left 1 tile
        # 12 = raise 1 tile
        # 13 = draw from bottom left + move left half tile
        # 14 = precise bottom left for yama
        # 15 = draw bottom left + raise 1 tile + move left 1 tile.
        # 16 = move left half a tile.
        # 17 = center + move down half a tile.
        # 18 = draw bottom left + lower 1.5 tiles + move left 1.5 tiles.
        x_coord = 0
        y_coord = 0
        scale_factor = scale / 50
        if mode == 1:
            y_coord = (height * -1) / 2
        elif mode == 2:
            y_coord = height / 2
        elif mode == 3:
            x_coord = width / 3.2
            y_coord = height / 2
        elif mode == 4:
            x_coord = (width * -1) / 2
        elif mode == 5:
            y_coord = height / 2 + 50 * scale_factor
        elif mode == 6:
            x_coord = 25 * scale_factor
            y_coord = 22 * scale_factor
        elif mode == 7:
            y_coord = height / 2 + 25 * scale_factor
        elif mode == 8:
            y_coord = height / 2 - 50 * scale_factor
        elif mode == 9:
            y_coord = height / 2 + 50 * scale_factor
            x_coord = 75 * scale_factor
        elif mode == 10:
            y_coord = height / 2 + 100 * scale_factor
        elif mode == 11:
            x_coord = 50 * scale_factor
        elif mode == 12:
            y_coord = 50 * scale_factor
        elif mode == 13:
            y_coord = height / 2
            x_coord = 25 * scale_factor
        elif mode == 14:
            y_coord = height - 50 * scale_factor
            x_coord = 100 * scale_factor
        elif mode == 15:
            y_coord = height / 2 + 50 * scale_factor
            x_coord = 50 * scale_factor
        elif mode == 16:
            x_coord = 25 * scale_factor
        elif mode == 17:
            x_coord = width / 3.2
            y_coord = height / 2 - 25 * scale_factor
        elif mode == 18:
            y_coord = height / 2 - 75 * scale_factor
            x_coord = 75 * scale_factor
        return int(x_coord), int(y_coord)

    def get_texture(self, tile, biome, lvl, scale):
        def get_specific_tile(tile):
            img_spec = None

            if (
                lvl.startswith("generic")
                or lvl.startswith("challenge")
                or lvl.startswith("testing")
                or lvl.startswith("beehive")
                or lvl.startswith("palace")
            ):
                if tile == "floor":
                    img_spec = self.sprite_fetcher.get("generic_floor", str(biome))
                elif tile == "styled_floor":
                    img_spec = self.sprite_fetcher.get(
                        "generic_styled_floor", str(biome)
                    )
            # base is weird with its tiles so I gotta get specific here
            if lvl.startswith("base"):
                if tile == "floor":
                    img_spec = self.sprite_fetcher.get("floor", "cave")
            if lvl.startswith("duat"):  # specific floor hard for this biome
                if tile == "floor_hard":
                    img_spec = self.sprite_fetcher.get("duat_floor_hard")
                elif tile == "coffin":
                    img_spec = self.sprite_fetcher.get(
                        "duat_coffin",
                    )
            # specific floor hard for this biome
            if (
                lvl.startswith("sunken")
                or lvl.startswith("hundun")
                or lvl.endswith("_sunkencity.lvl")
            ):
                if tile == "floor_hard":
                    img_spec = self.sprite_fetcher.get("sunken_floor_hard")
            # specific floor styled for this biome
            if (
                lvl.startswith("volcan")
                or lvl.startswith("ice")
                or lvl.endswith("_icecavesarea.lvl")
                or lvl.endswith("_volcano.lvl")
            ):
                if tile == "styled_floor":
                    img_spec = self.sprite_fetcher.get("empty")
            if lvl.startswith("olmec"):  # specific door
                if tile == "door":
                    img_spec = self.sprite_fetcher.get(
                        "stone_door",
                    )
            if lvl.startswith("cityofgold"):  # specific door
                if tile == "crushtraplarge":
                    img_spec = self.sprite_fetcher.get(
                        "gold_crushtraplarge",
                    )
                elif tile == "coffin":
                    img_spec = self.sprite_fetcher.get(
                        "gold_coffin",
                    )
            if lvl.startswith("temple"):  # specific door
                if tile == "coffin":
                    img_spec = self.sprite_fetcher.get(
                        "temple_coffin",
                    )

            return img_spec

        img = self.sprite_fetcher.get(str(tile), str(biome))
        if get_specific_tile(str(tile)) is not None:
            img = get_specific_tile(str(tile))

        if len(tile.split("%", 2)) > 1:
            img1 = self.sprite_fetcher.get("unknown")
            img2 = self.sprite_fetcher.get("unknown")
            primary_tile = tile.split("%", 2)[0]
            if self.sprite_fetcher.get(primary_tile, str(biome)):
                img1 = self.sprite_fetcher.get(primary_tile, str(biome))
                if get_specific_tile(str(tile)) is not None:
                    img1 = get_specific_tile(str(primary_tile))
            percent = tile.split("%", 2)[1]
            secondary_tile = "empty"
            img2 = None
            if len(tile.split("%", 2)) > 2:
                secondary_tile = tile.split("%", 2)[2]
                if self.sprite_fetcher.get(secondary_tile, str(biome)):
                    img2 = self.sprite_fetcher.get(secondary_tile, str(biome))
                    if get_specific_tile(str(tile)) is not None:
                        img2 = get_specific_tile(str(secondary_tile))
            img = self.get_tilecode_percent_texture(
                primary_tile, secondary_tile, percent, img1, img2
            )

        if img is None:
            img = self.sprite_fetcher.get_dyn(str(tile))
        width, height = img.size

        scale_factor = 128 / scale
        width = int(
            width / scale_factor
        )  # 2.65 is the scale to get the typical 128 tile size down to the needed 50
        height = int(height / scale_factor)

        _scale = 1
        # for some reason these are sized differently then everything elses typical universal scale
        # if (tile == "door2" or tile == "door2_secret" or tile == "ghist_door2"):
        #    width = int(width/2)
        #    height = int(height/2)

        # since theres rounding involved, this makes sure each tile is size
        # correctly by making up for what was rounded off
        if width < scale and height < scale:
            difference = 0
            if width > height:
                difference = scale - width
            else:
                difference = scale - height

            width = width + difference
            height = height + difference

        img = img.resize((width, height), Image.Resampling.LANCZOS)
        return img

    @staticmethod
    def get_tilecode_percent_texture(_tile, alt_tile, percent, img1, img2):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir_path = Path(tempdir)
            temp1 = tempdir_path / "temp1.png"
            temp2 = tempdir_path / "temp2.png"
            # ImageTk.PhotoImage()._PhotoImage__photo.write(temp1, format="png")

            image1_save = ImageTk.PhotoImage(img1)
            # pylint: disable=protected-access
            image1_save._PhotoImage__photo.write(temp1, format="png")
            image1 = Image.open(
                temp1,
            ).convert("RGBA")
            image1 = image1.resize((50, 50), Image.BILINEAR)
            tile_text = percent + "%"
            if alt_tile != "empty":
                tile_text += "/" + str(100 - int(percent)) + "%"

                # ImageTk.PhotoImage()._PhotoImage__photo.write(temp2, format="png")

                image2_save = ImageTk.PhotoImage(img2)
                # pylint: disable=protected-access
                image2_save._PhotoImage__photo.write(temp2, format="png")
                image2 = Image.open(temp2).convert("RGBA")
                image2 = image2.resize((50, 50), Image.BILINEAR).convert("RGBA")
                image2.crop([25, 0, 50, 50]).save(temp2)
                image1.save(temp1)
                image1 = Image.open(temp1).convert("RGBA")
                image2 = Image.open(temp2).convert("RGBA")

                offset = (25, 0)
                image1.paste(image2, offset)
            # make a blank image for the text, initialized to transparent text color
            txt = Image.new("RGBA", (50, 50), (255, 255, 255, 0))

            # get a drawing context
            draw_ctx = ImageDraw.Draw(txt)

            # draw text, half opacity
            draw_ctx.text((6, 34), tile_text, fill=(0, 0, 0, 255))
            draw_ctx.text((4, 34), tile_text, fill=(0, 0, 0, 255))
            draw_ctx.text((6, 36), tile_text, fill=(0, 0, 0, 255))
            draw_ctx.text((4, 36), tile_text, fill=(0, 0, 0, 255))
            draw_ctx.text((5, 35), tile_text, fill=(255, 255, 255, 255))

            out = Image.alpha_composite(image1, txt)
        return out

    @staticmethod
    def get_bg_texture_file_name(level_file_name):
        if (
            level_file_name.startswith("challenge_sun")
            or level_file_name.startswith("sunken")
            or level_file_name.startswith("hundun")
            or level_file_name.startswith("ending_hard")
            or level_file_name.endswith("_sunkencity.lvl")
        ):
            return "bg_sunken.png"
        elif (
            level_file_name.startswith("abzu.lvl")
            or level_file_name.startswith("lake")
            or level_file_name.startswith("tide")
            or level_file_name.startswith("end")
            or level_file_name.endswith("_tidepool.lvl")
        ):
            return "bg_tidepool.png"
        elif (
            level_file_name.startswith("babylon")
            or level_file_name.startswith("hallofu")
            or level_file_name.endswith("_babylon.lvl")
            or level_file_name.startswith("palace")
            or level_file_name.startswith("tiamat")
        ):
            return "bg_babylon.png"
        elif level_file_name.startswith("basecamp"):
            return "bg_cave.png"
        elif level_file_name.startswith("beehive"):
            return "bg_beehive.png"
        elif (
            level_file_name.startswith("blackmark")
            or level_file_name.startswith("jungle")
            or level_file_name.startswith("challenge_moon")
            or level_file_name.endswith("_jungle.lvl")
        ):
            return "bg_jungle.png"
        elif (
            level_file_name.startswith("challenge_star")
            or level_file_name.startswith("temple")
            or level_file_name.endswith("_temple.lvl")
        ):
            return "bg_temple.png"
        elif level_file_name.startswith("city"):
            return "bg_gold.png"
        elif level_file_name.startswith("duat"):
            return "bg_temple.png"
        elif level_file_name.startswith("egg"):
            return "bg_eggplant.png"
        elif level_file_name.startswith("ice") or level_file_name.endswith("_icecavesarea.lvl"):
            return "bg_ice.png"
        elif level_file_name.startswith("olmec"):
            return "bg_stone.png"
        elif level_file_name.startswith("vlad"):
            return "bg_vlad.png"
        elif level_file_name.startswith("volcano") or level_file_name.endswith("_volcano.lvl"):
            return "bg_volcano.png"
        return "bg_cave.png"