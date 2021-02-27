from io import StringIO
from textwrap import dedent

from modlunky2.ui.play.config import PlaylunkyConfig


def test_keep_unknown():
    config = PlaylunkyConfig.from_ini(
        StringIO(
            dedent(
                """\
        [settings]
        random_character_select=off
        enable_loose_audio_files=on
        some_unknown_field=ABACAB00
        cache_decoded_audio_files=off
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
        random_character_select=on
        enable_loose_audio_files=on
        some_unknown_field=ABACAB00
        cache_decoded_audio_files=off
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
        random_character_select=off
        enable_loose_audio_files=on
        cache_decoded_audio_files=off
    """
            )
        )
    )
    assert config.random_character_select is False
    assert config.enable_loose_audio_files is True
    assert config.cache_decoded_audio_files is False


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
        random_character_select=off
    """
            )
        )
    )
    assert config.random_character_select is False
    assert config.enable_loose_audio_files is True
    assert config.cache_decoded_audio_files is False
