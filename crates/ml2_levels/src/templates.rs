use std::io::Write;
use std::iter::Peekable;
use std::str::Lines;

use indexmap::IndexMap;

use crate::error::{LevelError, Result};
use crate::utils::{DirectivePrefix, TEMPLATE_COMMENT_LINE, format_comment, split_comment};

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum TemplateSetting {
    Ignore,
    Flip,
    OnlyFlip,
    Dual,
    Rare,
    Hard,
    Liquid,
    Purge,
}

impl TemplateSetting {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Ignore => "ignore",
            Self::Flip => "flip",
            Self::OnlyFlip => "onlyflip",
            Self::Dual => "dual",
            Self::Rare => "rare",
            Self::Hard => "hard",
            Self::Liquid => "liquid",
            Self::Purge => "purge",
        }
    }

    pub fn from_stripped(name: &str) -> Option<Self> {
        Some(match name {
            "ignore" => Self::Ignore,
            "flip" => Self::Flip,
            "onlyflip" => Self::OnlyFlip,
            "dual" => Self::Dual,
            "rare" => Self::Rare,
            "hard" => Self::Hard,
            "liquid" => Self::Liquid,
            "purge" => Self::Purge,
            _ => return None,
        })
    }

    /// Matches a full `\!name` line and returns the parsed setting.
    fn from_line(line: &str) -> Option<Self> {
        let name = line.strip_prefix(DirectivePrefix::TemplateSetting.as_str())?;
        Self::from_stripped(name)
    }

    fn to_line(self) -> String {
        format!(
            "{}{}\n",
            DirectivePrefix::TemplateSetting.as_str(),
            self.as_str()
        )
    }
}

#[derive(Debug, Clone, Default)]
pub struct Room {
    pub comment: Option<String>,
    pub settings: Vec<TemplateSetting>,
    /// Rows of single-character tile codes. Each row's `Vec<char>` may differ
    /// in length from its neighbors; the parser doesn't enforce a rectangle.
    pub foreground: Vec<Vec<char>>,
    /// Optional dual-layer grid. Empty when the room is single-layer.
    pub background: Vec<Vec<char>>,
}

impl Room {
    /// Parse a room starting from the current line. Consumes lines up to
    /// and including a terminating blank line (or a trailing `//` comment
    /// after the room body started).
    fn parse(lines: &mut Peekable<Lines<'_>>) -> Room {
        let mut room = Room::default();
        let mut comment_buf = String::new();
        let mut started_room = false;

        for raw in lines.by_ref() {
            let line = raw.trim();

            if line.is_empty() {
                break;
            }

            if line.starts_with("//") {
                if started_room {
                    // Trailing comment: signal end of room. This line is
                    // consumed but no further lines are; the next room
                    // starts on the following iteration.
                    break;
                }
                // Store the comment text without its leading `//` markers, the
                // same way template comments are parsed (via split_comment), so
                // consumers see clean text. The writer re-adds `//` through
                // format_comment on save.
                comment_buf.push_str(line.trim_start_matches(['/', ' ']));
                continue;
            }

            if let Some(setting) = TemplateSetting::from_line(line) {
                started_room = true;
                room.settings.push(setting);
                continue;
            }

            started_room = true;
            let (fg, bg) = partition_row(line);
            if !bg.is_empty() {
                room.background.push(bg.chars().collect());
            }
            room.foreground.push(fg.chars().collect());
        }

        if !comment_buf.is_empty() {
            room.comment = Some(comment_buf);
        }
        room
    }

    fn write<W: Write>(&self, writer: &mut W) -> Result<()> {
        if let Some(c) = self.comment.as_deref()
            && !c.is_empty()
        {
            let formatted = format_comment(Some(c));
            let trimmed = formatted.trim_end_matches('\n');
            writer.write_all(trimmed.as_bytes())?;
            writer.write_all(b"\n")?;
        }

        for setting in &self.settings {
            writer.write_all(setting.to_line().as_bytes())?;
        }

        let rows = self.foreground.len().max(self.background.len());
        for i in 0..rows {
            let fg_row = self.foreground.get(i);
            let bg_row = self.background.get(i);

            let mut line = String::new();
            if let Some(fg) = fg_row {
                for c in fg {
                    line.push(*c);
                }
            }
            if let Some(bg) = bg_row
                && !bg.is_empty()
            {
                line.push(' ');
                for c in bg {
                    line.push(*c);
                }
            }
            line.push('\n');
            writer.write_all(line.as_bytes())?;
        }

        Ok(())
    }
}

/// Splits a row on its first ASCII space.
fn partition_row(line: &str) -> (&str, &str) {
    match line.find(' ') {
        Some(idx) => (line[..idx].trim(), line[idx + 1..].trim()),
        None => (line.trim(), ""),
    }
}

#[derive(Debug, Clone)]
pub struct LevelTemplate {
    pub name: String,
    pub comment: Option<String>,
    pub rooms: Vec<Room>,
}

impl LevelTemplate {
    pub const PREFIX: &'static str = DirectivePrefix::Template.as_str();

    /// Parse a template starting from the `\.name` header line. Consumes
    /// subsequent room lines until the next template header or EOF.
    pub(crate) fn parse(header: &str, lines: &mut Peekable<Lines<'_>>) -> Result<Self> {
        let (rest, comment) = split_comment(header);
        let name = rest
            .strip_prefix(Self::PREFIX)
            .ok_or_else(|| LevelError::MissingName(header.to_string()))?
            .trim();
        if name.is_empty() {
            return Err(LevelError::MissingName(header.to_string()));
        }

        let mut template = Self {
            name: name.to_string(),
            comment,
            rooms: Vec::new(),
        };

        while let Some(next_raw) = lines.peek().copied() {
            let (rest, comment) = split_comment(next_raw);

            if rest.starts_with(Self::PREFIX) {
                return Ok(template);
            }

            if !rest.is_empty() || comment.is_some() {
                let room = Room::parse(lines);
                template.rooms.push(room);
            } else {
                // Blank / banner-only line: consume it and keep going.
                lines.next();
            }
        }

        Ok(template)
    }

    fn write<W: Write>(&self, writer: &mut W) -> Result<()> {
        writer.write_all(TEMPLATE_COMMENT_LINE.as_bytes())?;
        writer.write_all(b"\n")?;

        let mut header = format!("{}{}", Self::PREFIX, self.name);
        if let Some(c) = self.comment.as_deref()
            && !c.is_empty()
        {
            let formatted = format_comment(Some(c));
            let trimmed = formatted.trim_end_matches('\n');
            header.push_str("   ");
            header.push_str(trimmed);
        }
        header.push('\n');
        writer.write_all(header.as_bytes())?;

        writer.write_all(TEMPLATE_COMMENT_LINE.as_bytes())?;
        writer.write_all(b"\n\n")?;

        for (idx, room) in self.rooms.iter().enumerate() {
            room.write(writer)?;
            if idx < self.rooms.len() - 1 {
                writer.write_all(b"\n")?;
            }
        }
        Ok(())
    }
}

#[derive(Debug, Default, Clone)]
pub struct LevelTemplates {
    inner: IndexMap<String, LevelTemplate>,
    pub comment: Option<String>,
}

impl LevelTemplates {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn all(&self) -> impl Iterator<Item = &LevelTemplate> {
        self.inner.values()
    }

    pub fn get(&self, name: &str) -> Option<&LevelTemplate> {
        self.inner.get(name)
    }

    pub fn set(&mut self, obj: LevelTemplate) {
        self.inner.insert(obj.name.clone(), obj);
    }

    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    pub fn write<W: Write>(&self, writer: &mut W) -> Result<()> {
        writer.write_all(format_comment(self.comment.as_deref()).as_bytes())?;
        let count = self.inner.len();
        for (idx, template) in self.inner.values().enumerate() {
            template.write(writer)?;
            if idx < count - 1 {
                writer.write_all(b"\n")?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_single_room_template() {
        let src = "\
==00======
1100=====1
0000000000

";
        let mut lines = src.lines().peekable();
        let template = LevelTemplate::parse("\\.entrance", &mut lines).unwrap();
        assert_eq!(template.name, "entrance");
        assert_eq!(template.rooms.len(), 1);
        assert_eq!(template.rooms[0].foreground.len(), 3);
        assert!(template.rooms[0].background.is_empty());
    }

    #[test]
    fn parse_multi_room_template_with_flip_setting() {
        let src = "\
\\!flip
==00======
1100=====1

\\!flip
0000000000
0000000000

";
        let mut lines = src.lines().peekable();
        let template = LevelTemplate::parse("\\.entrance", &mut lines).unwrap();
        assert_eq!(template.rooms.len(), 2);
        assert_eq!(template.rooms[0].settings, vec![TemplateSetting::Flip]);
        assert_eq!(template.rooms[1].settings, vec![TemplateSetting::Flip]);
    }

    #[test]
    fn parse_dual_layer_room() {
        let src = "\
\\!dual
==00====== 0000000000
1100=====1 0000000000

";
        let mut lines = src.lines().peekable();
        let template = LevelTemplate::parse("\\.dual_test", &mut lines).unwrap();
        assert_eq!(template.rooms[0].settings, vec![TemplateSetting::Dual]);
        assert_eq!(template.rooms[0].foreground.len(), 2);
        assert_eq!(template.rooms[0].background.len(), 2);
    }

    #[test]
    fn parse_stops_at_next_template_header() {
        let src = "\
==00======

\\.next_template
";
        let mut lines = src.lines().peekable();
        let template = LevelTemplate::parse("\\.entrance", &mut lines).unwrap();
        assert_eq!(template.rooms.len(), 1);
        // Next line still available for the outer parser.
        assert_eq!(lines.peek().copied(), Some("\\.next_template"));
    }

    #[test]
    fn template_setting_line_roundtrip() {
        assert_eq!(TemplateSetting::Flip.to_line(), "\\!flip\n");
        assert_eq!(TemplateSetting::Dual.to_line(), "\\!dual\n");
    }

    #[test]
    fn parse_template_header_trailing_comment_populates_comment() {
        // `\.coffin_player   Coffin room...` puts a description after
        // enough whitespace to look like padding. The parser has to
        // treat it as an inline comment on the header rather than a
        // second name token, so the template's `.comment` picks it up.
        let src = "==00======\n\n";
        let mut lines = src.lines().peekable();
        let template = LevelTemplate::parse(
            "\\.coffin_player   // Coffin room holding a dead player",
            &mut lines,
        )
        .unwrap();
        assert_eq!(template.name, "coffin_player");
        assert_eq!(
            template.comment.as_deref(),
            Some("Coffin room holding a dead player")
        );
    }

    #[test]
    fn parse_room_leading_slash_comment_becomes_room_comment() {
        // A `// text` line before the first room-body row must land in
        // `room.comment`, not the outer file/section comment. The leading
        // `//` markers are stripped, matching template-comment parsing.
        let src = "\
// entrance variant A
0000000000
1111111111

";
        let mut lines = src.lines().peekable();
        let template = LevelTemplate::parse("\\.entrance", &mut lines).unwrap();
        assert_eq!(template.rooms.len(), 1);
        assert_eq!(
            template.rooms[0].comment.as_deref(),
            Some("entrance variant A")
        );
    }

    #[test]
    fn parse_room_preserves_flip_liquid_setting_order() {
        // Setting order matters for Playlunky: some rooms only render
        // correctly with a specific `\!` order. `settings: Vec<...>`
        // is the source of truth; input order must be preserved.
        let src = "\
\\!flip
\\!liquid
0000000000

";
        let mut lines = src.lines().peekable();
        let template = LevelTemplate::parse("\\.entrance", &mut lines).unwrap();
        assert_eq!(
            template.rooms[0].settings,
            vec![TemplateSetting::Flip, TemplateSetting::Liquid]
        );
    }

    #[test]
    fn parse_room_preserves_liquid_flip_setting_order() {
        let src = "\
\\!liquid
\\!flip
0000000000

";
        let mut lines = src.lines().peekable();
        let template = LevelTemplate::parse("\\.entrance", &mut lines).unwrap();
        assert_eq!(
            template.rooms[0].settings,
            vec![TemplateSetting::Liquid, TemplateSetting::Flip]
        );
    }

    #[test]
    fn partition_row_no_space() {
        assert_eq!(partition_row("1100=====1"), ("1100=====1", ""));
    }

    #[test]
    fn partition_row_with_space() {
        assert_eq!(partition_row("aa bb"), ("aa", "bb"));
    }
}
