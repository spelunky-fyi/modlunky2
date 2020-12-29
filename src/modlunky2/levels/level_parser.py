from pathlib import Path
import re

p = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted\Data\Levels"
)

tile_code_re = re.compile(
    r"^\\\?(?P<name>\w+)(%(?P<pct>\d{2})(?P<second_name>\w+)?)?\s+(?P<code>.)"
)

codes = set()

for lvl_file in p.glob("*lvl"):
    for line in lvl_file.read_text().splitlines():
        m = tile_code_re.match(line)
        if m:
            mdict = m.groupdict()
            codes.add(mdict.get("name"))
            if mdict.get("pct") and mdict.get("second_name"):
                codes.add(mdict.get("second_name"))
