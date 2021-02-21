import configparser
from dataclasses import dataclass, field, fields
from typing import Optional, TextIO

PLAYLUNKY_INI_SECTION = "settings"


@dataclass
class PlaylunkyConfig:
    ini: Optional[configparser.ConfigParser] = field(
        init=False, default=None, compare=False, repr=False
    )

    random_character_select: bool = False
    enable_loose_audio_files: bool = True
    cache_decoded_audio_files: bool = False

    @classmethod
    def from_ini(cls, handle: TextIO) -> "PlaylunkyConfig":
        config = configparser.ConfigParser()
        config.read_file(handle)

        random_character_select = config.getboolean(
            PLAYLUNKY_INI_SECTION,
            "random_character_select",
            fallback=False,
        )
        enable_loose_audio_files = config.getboolean(
            "settings",
            "enable_loose_audio_files",
            fallback=True,
        )
        cache_decoded_audio_files = config.getboolean(
            "settings",
            "cache_decoded_audio_files",
            fallback=False,
        )

        obj = cls(
            random_character_select=random_character_select,
            enable_loose_audio_files=enable_loose_audio_files,
            cache_decoded_audio_files=cache_decoded_audio_files,
        )

        obj.ini = config

        return obj

    @staticmethod
    def set_boolean(ini: configparser.ConfigParser, name: str, val: bool):
        if val is True:
            val = "on"
        else:
            val = "off"

        ini.set(PLAYLUNKY_INI_SECTION, name, val)

    def write(self, handle: TextIO):
        if self.ini:
            ini = self.ini
        else:
            ini = configparser.ConfigParser()
            ini.add_section(PLAYLUNKY_INI_SECTION)

        for option in fields(self):
            if option.name == "ini":
                continue
            if issubclass(option.type, bool):
                self.set_boolean(ini, option.name, getattr(self, option.name))
            else:
                ini.set(PLAYLUNKY_INI_SECTION, option.name, getattr(self, option.name))

        ini.write(handle, space_around_delimiters=False)
