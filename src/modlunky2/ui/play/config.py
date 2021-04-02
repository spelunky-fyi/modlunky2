import configparser
from dataclasses import dataclass, field, fields
from typing import Optional, TextIO

LEGACY_INI_SECTION = "settings"


SECTIONS = {
    "general_settings": [
        "enable_loose_file_warning",
    ],
    "script_settings": [
        "enable_developer_mode",
    ],
    "audio_settings": [
        "enable_loose_audio_files",
        "cache_decoded_audio_files",
    ],
    "sprite_settings": [
        "random_character_select",
        "generate_character_journal_stickers",
        "generate_character_journal_entries",
        "generate_sticker_pixel_art",
    ],
}

OPTION_TO_SECTION = {
    option: section for section, options in SECTIONS.items() for option in options
}


@dataclass
class PlaylunkyConfig:
    ini: Optional[configparser.ConfigParser] = field(
        init=False, default=None, compare=False, repr=False
    )

    # General Settings
    enable_loose_file_warning: bool = True

    # Script Settings
    enable_developer_mode: bool = False

    # Audio Settings
    enable_loose_audio_files: bool = True
    cache_decoded_audio_files: bool = False

    # Sprite Settings
    random_character_select: bool = False
    generate_character_journal_stickers: bool = True
    generate_character_journal_entries: bool = True
    generate_sticker_pixel_art: bool = True

    @classmethod
    def from_ini(cls, handle: TextIO) -> "PlaylunkyConfig":
        config = configparser.ConfigParser()
        config.read_file(handle)

        obj = cls()
        for section, options in SECTIONS.items():
            for option in options:
                val = config.getboolean(section, option, fallback=None)
                if val is None:
                    val = config.getboolean(LEGACY_INI_SECTION, option, fallback=None)
                if val is None:
                    continue

                setattr(obj, option, val)

        obj.ini = config
        return obj

    @staticmethod
    def set_boolean(ini: configparser.ConfigParser, name: str, val: bool):
        if val is True:
            val = "on"
        else:
            val = "off"

        ini.set(OPTION_TO_SECTION[name], name, val)

    @staticmethod
    def clean_ini(ini):
        for section in SECTIONS:
            if not ini.has_section(section):
                ini.add_section(section)

        if ini.has_section(LEGACY_INI_SECTION):
            for option in OPTION_TO_SECTION:
                if ini.has_option(LEGACY_INI_SECTION, option):
                    ini.remove_option(LEGACY_INI_SECTION, option)

            if not ini.options(LEGACY_INI_SECTION):
                ini.remove_section(LEGACY_INI_SECTION)

    def write(self, handle: TextIO):
        if self.ini:
            ini = self.ini
        else:
            ini = configparser.ConfigParser()

        self.clean_ini(ini)

        for option in fields(self):
            if option.name == "ini":
                continue

            if issubclass(option.type, bool):
                self.set_boolean(ini, option.name, getattr(self, option.name))
            else:
                ini.set(LEGACY_INI_SECTION, option.name, getattr(self, option.name))

        ini.write(handle, space_around_delimiters=False)
