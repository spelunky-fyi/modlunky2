from io import StringIO
from textwrap import dedent

from modlunky2.ui.play.config import PlaylunkyConfig


def test_legacy_keep_unknown():
    config = PlaylunkyConfig.from_ini(
        StringIO(
            dedent(
                """\
        [settings]
        random_character_select=false
        enable_loose_audio_files=true
        some_unknown_field=ABACAB00
        cache_decoded_audio_files=false  # test inline-comment
        enable_developer_mode=false

        [script_settings]
        enable_developer_console=true
        console_history_size=50  # test inline-comment
    """
            )
        )
    )
    config.random_character_select = True

    out = StringIO()
    config.write(out)
    out.seek(0)

    assert (
        out.getvalue().strip()
        == dedent(
            """\
        [settings]
        some_unknown_field=ABACAB00
        
        [script_settings]
        enable_developer_console=true
        console_history_size=50
        enable_developer_mode=false

        [general_settings]
        enable_loose_file_warning=true
        disable_asset_caching=false
        block_save_game=false
        allow_save_game_mods=true
        use_playlunky_save=false
        disable_steam_achievements=false
        speedrun_mode=false

        [audio_settings]
        enable_loose_audio_files=true
        cache_decoded_audio_files=false
        synchronous_update=true

        [sprite_settings]
        random_character_select=true
        link_related_files=true
        generate_character_journal_stickers=true
        generate_character_journal_entries=true
        generate_sticker_pixel_art=true
        enable_sprite_hot_loading=false
        sprite_hot_load_delay=400
        enable_customizable_sheets=true
        enable_luminance_scaling=true
    """
        ).strip()
    )


def test_legacy_no_unknowns():
    config = PlaylunkyConfig.from_ini(
        StringIO(
            dedent(
                """\
        [settings]
        random_character_select=false
        enable_loose_audio_files=true
        cache_decoded_audio_files=false
        enable_developer_mode=false

        [script_settings]
        enable_developer_console=true
        console_history_size=50
    """
            )
        )
    )
    config.random_character_select = True

    out = StringIO()
    config.write(out)
    out.seek(0)

    assert (
        out.getvalue().strip()
        == dedent(
            """\
        [script_settings]
        enable_developer_console=true
        console_history_size=50
        enable_developer_mode=false

        [general_settings]
        enable_loose_file_warning=true
        disable_asset_caching=false
        block_save_game=false
        allow_save_game_mods=true
        use_playlunky_save=false
        disable_steam_achievements=false
        speedrun_mode=false

        [audio_settings]
        enable_loose_audio_files=true
        cache_decoded_audio_files=false
        synchronous_update=true

        [sprite_settings]
        random_character_select=true
        link_related_files=true
        generate_character_journal_stickers=true
        generate_character_journal_entries=true
        generate_sticker_pixel_art=true
        enable_sprite_hot_loading=false
        sprite_hot_load_delay=400
        enable_customizable_sheets=true
        enable_luminance_scaling=true
    """
        ).strip()
    )


def test_write_round_trips():
    config = PlaylunkyConfig()
    config.random_character_select = True
    out = StringIO()
    config.write(out)

    out.seek(0)
    new_config = PlaylunkyConfig.from_ini(out)

    assert config == new_config


def test_ini_with_known_values():
    config = PlaylunkyConfig.from_ini(
        StringIO(
            dedent(
                """\
        [settings]
        random_character_select=false
        enable_loose_audio_files=true
        cache_decoded_audio_files=false
        enable_developer_mode=false
    """
            )
        )
    )
    assert config.random_character_select is False
    assert config.enable_loose_audio_files is True
    assert config.cache_decoded_audio_files is False
    assert config.enable_developer_mode is False


def test_ini_when_empty():
    config = PlaylunkyConfig.from_ini(StringIO(""))
    assert config.random_character_select is False
    assert config.enable_loose_audio_files is True
    assert config.cache_decoded_audio_files is False


def test_ini_with_partial_config():
    config = PlaylunkyConfig.from_ini(
        StringIO(
            dedent(
                """\
        [settings]
        random_character_select=false
    """
            )
        )
    )
    assert config.random_character_select is False
    assert config.enable_loose_audio_files is True
    assert config.cache_decoded_audio_files is False
