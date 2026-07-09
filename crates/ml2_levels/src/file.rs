use std::fs;
use std::io::Write;
use std::iter::Peekable;
use std::path::Path;
use std::str::Lines;

use encoding_rs::WINDOWS_1252;

use crate::chances::{LevelChance, LevelChances, MonsterChance, MonsterChances};
use crate::error::Result;
use crate::settings::{LevelSetting, LevelSettings};
use crate::templates::{LevelTemplate, LevelTemplates};
use crate::tilecodes::{TileCode, TileCodes};
use crate::utils::{DirectivePrefix, SECTION_COMMENT, format_comment};

#[derive(Debug, Default, Clone)]
pub struct LevelFile {
    pub comment: Option<String>,
    pub level_settings: LevelSettings,
    pub tile_codes: TileCodes,
    pub level_chances: LevelChances,
    pub monster_chances: MonsterChances,
    pub level_templates: LevelTemplates,
}

impl LevelFile {
    /// Parse from a cp1252-encoded byte buffer.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        let (decoded, _, _) = WINDOWS_1252.decode(bytes);
        Self::from_str(&decoded)
    }

    /// Parse from a cp1252-encoded file.
    pub fn from_path<P: AsRef<Path>>(path: P) -> Result<Self> {
        let bytes = fs::read(path.as_ref())?;
        Self::from_bytes(&bytes)
    }

    #[allow(clippy::should_implement_trait)]
    pub fn from_str(input: &str) -> Result<Self> {
        let mut file = LevelFile::default();
        let mut lines = input.lines().peekable();

        let mut last_section_comment: Option<String> = None;
        let mut last_seen_directive: Option<DirectivePrefix> = None;

        while let Some(raw) = lines.next() {
            let line = raw.trim();
            if line.is_empty() {
                continue;
            }

            if let Some(prefix) = DirectivePrefix::from_line(line) {
                match prefix {
                    DirectivePrefix::LevelSetting => {
                        let obj = LevelSetting::parse(line)?;
                        file.level_settings.set(obj);
                        transition(
                            &mut last_seen_directive,
                            &mut last_section_comment,
                            prefix,
                            |c| file.level_settings.comment = Some(c),
                        );
                    }
                    DirectivePrefix::TileCode => {
                        let obj = TileCode::parse(line)?;
                        file.tile_codes.set(obj);
                        transition(
                            &mut last_seen_directive,
                            &mut last_section_comment,
                            prefix,
                            |c| file.tile_codes.comment = Some(c),
                        );
                    }
                    DirectivePrefix::LevelChance => {
                        let obj = LevelChance::parse(line)?;
                        file.level_chances.set(obj);
                        transition(
                            &mut last_seen_directive,
                            &mut last_section_comment,
                            prefix,
                            |c| file.level_chances.comment = Some(c),
                        );
                    }
                    DirectivePrefix::MonsterChance => {
                        let obj = MonsterChance::parse(line)?;
                        file.monster_chances.set(obj);
                        transition(
                            &mut last_seen_directive,
                            &mut last_section_comment,
                            prefix,
                            |c| file.monster_chances.comment = Some(c),
                        );
                    }
                    DirectivePrefix::Template => {
                        let template = LevelTemplate::parse(line, &mut lines)?;
                        file.level_templates.set(template);
                        transition(
                            &mut last_seen_directive,
                            &mut last_section_comment,
                            prefix,
                            |c| file.level_templates.comment = Some(c),
                        );
                    }
                    DirectivePrefix::TemplateSetting => {
                        // Bare template setting outside a room is silently
                        // ignored.
                    }
                }
                continue;
            }

            if line == SECTION_COMMENT {
                let block = parse_section_comment(line, &mut lines);
                if file.comment.is_none() && last_seen_directive.is_none() {
                    file.comment = Some(block);
                } else {
                    last_section_comment = Some(block);
                }
                continue;
            }
            // Any other line (banner slashes, orphan text) is silently ignored.
        }

        Ok(file)
    }

    pub fn write<W: Write>(&self, writer: &mut W) -> Result<()> {
        writer.write_all(format_comment(self.comment.as_deref()).as_bytes())?;
        self.level_settings.write(writer)?;
        self.tile_codes.write(writer)?;
        self.level_chances.write(writer)?;
        self.monster_chances.write(writer)?;
        self.level_templates.write(writer)?;
        Ok(())
    }

    pub fn to_string(&self) -> Result<String> {
        let mut buf = Vec::new();
        self.write(&mut buf)?;
        // Everything emitted is ASCII-safe, but decode as cp1252 just
        // to be safe.
        let (decoded, _, _) = WINDOWS_1252.decode(&buf);
        Ok(decoded.into_owned())
    }

    /// Serialize to a cp1252-encoded byte buffer.
    pub fn to_bytes(&self) -> Result<Vec<u8>> {
        let s = self.to_string()?;
        let (encoded, _, _) = WINDOWS_1252.encode(&s);
        Ok(encoded.into_owned())
    }

    pub fn write_path<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let bytes = self.to_bytes()?;
        fs::write(path.as_ref(), bytes)?;
        Ok(())
    }
}

fn transition(
    last: &mut Option<DirectivePrefix>,
    pending: &mut Option<String>,
    incoming: DirectivePrefix,
    assign: impl FnOnce(String),
) {
    if *last == Some(incoming) {
        return;
    }
    if let Some(c) = pending.take() {
        assign(c);
    }
    *last = Some(incoming);
}

/// Reconstruct a section-comment block starting from `first_line` (already
/// stripped by the outer loop) plus any subsequent `//`-prefixed lines.
/// The block includes trailing newlines so it round-trips through
/// `format_comment`.
fn parse_section_comment(first_line: &str, lines: &mut Peekable<Lines<'_>>) -> String {
    let mut output = String::new();
    output.push_str(first_line);
    output.push('\n');
    while let Some(&peek) = lines.peek() {
        if !peek.starts_with("//") {
            break;
        }
        output.push_str(peek);
        output.push('\n');
        lines.next();
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn first_section_comment_block_routes_to_file_comment() {
        // A section-banner block at the top of the file, before any
        // directive, must land in `file.comment` -- NOT in the first
        // section's `.comment`. Only the very first banner behaves this
        // way; subsequent banners feed the next section.
        let src = "\
// ------------------------------
// My custom pack
// ------------------------------

\\-back_room_chance 5
";
        let file = LevelFile::from_str(src).unwrap();
        assert!(
            file.comment
                .as_deref()
                .is_some_and(|c| c.contains("My custom pack")),
            "file.comment = {:?}",
            file.comment
        );
        assert!(
            file.level_settings.comment.is_none(),
            "level_settings should NOT own the file banner: {:?}",
            file.level_settings.comment
        );
        assert!(file.level_settings.get("back_room_chance").is_some());
    }

    #[test]
    fn subsequent_section_comment_routes_to_next_section() {
        // Once the first directive lands, subsequent banners are staged
        // in `last_section_comment` and flushed into the NEXT section's
        // `.comment` by `transition`.
        let src = "\
\\-back_room_chance 5

// ------------------------------
// TILE CODES
// ------------------------------
\\?empty                     0
";
        let file = LevelFile::from_str(src).unwrap();
        assert!(file.comment.is_none(), "no file banner in this input");
        assert!(
            file.tile_codes
                .comment
                .as_deref()
                .is_some_and(|c| c.contains("TILE CODES")),
            "tile_codes.comment = {:?}",
            file.tile_codes.comment
        );
    }

    #[test]
    fn bare_template_setting_outside_room_is_ignored() {
        // A dangling `\!flip` at file scope must not error, the loader
        // silently skips it. Verify the following directive still parses
        // so the loop kept going.
        let src = "\
\\!flip

\\-back_room_chance 5
";
        let file = LevelFile::from_str(src).unwrap();
        assert!(file.level_settings.get("back_room_chance").is_some());
    }

    #[test]
    fn missing_optional_sections_parses_ok() {
        // Only level settings + tile codes present; no chances, no
        // monster chances, no templates. Every optional container
        // should stay empty without erroring.
        let src = "\
\\-back_room_chance 5

\\?empty                     0
";
        let file = LevelFile::from_str(src).unwrap();
        assert!(!file.level_settings.is_empty());
        assert!(!file.tile_codes.is_empty());
        assert!(file.level_chances.is_empty());
        assert!(file.monster_chances.is_empty());
        assert!(file.level_templates.is_empty());
    }
}
