pub const SECTION_COMMENT: &str = "// ------------------------------";
pub const TEMPLATE_COMMENT_LINE: &str =
    "////////////////////////////////////////////////////////////////////////////////";

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum DirectivePrefix {
    LevelSetting,
    TileCode,
    LevelChance,
    MonsterChance,
    Template,
    TemplateSetting,
}

impl DirectivePrefix {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::LevelSetting => "\\-",
            Self::TileCode => "\\?",
            Self::LevelChance => "\\%",
            Self::MonsterChance => "\\+",
            Self::Template => "\\.",
            Self::TemplateSetting => "\\!",
        }
    }

    pub fn from_line(line: &str) -> Option<Self> {
        [
            Self::LevelSetting,
            Self::TileCode,
            Self::LevelChance,
            Self::MonsterChance,
            Self::Template,
            Self::TemplateSetting,
        ]
        .into_iter()
        .find(|p| line.starts_with(p.as_str()))
    }
}

/// Partitions a line on its first `//`. The tail is trimmed, then any
/// leading/trailing `/` chars are stripped. Empty comments come back as
/// `None`.
pub fn split_comment(line: &str) -> (String, Option<String>) {
    if let Some(idx) = line.find("//") {
        let rest = line[..idx].trim().to_string();
        let raw = &line[idx + 2..];
        let stripped = raw.trim().trim_matches('/').to_string();
        let comment = if stripped.is_empty() {
            None
        } else {
            Some(stripped)
        };
        (rest, comment)
    } else {
        (line.trim().to_string(), None)
    }
}

pub fn parse_chance_values(s: &str) -> Result<Vec<i64>, std::num::ParseIntError> {
    s.split(',').map(|v| v.trim().parse::<i64>()).collect()
}

/// Format one directive line:
///
/// - `name` left-padded to `name_padding`
/// - if a non-empty comment is present: `value` left-padded to `value_padding`,
///   then ` // `, then the comment with any leading `/` and spaces stripped
/// - otherwise: just `value` (no padding)
pub fn to_line(
    prefix: &str,
    name: &str,
    name_padding: usize,
    value: &str,
    value_padding: usize,
    comment: Option<&str>,
) -> String {
    let name_padded = format!("{:<width$}", name, width = name_padding);
    match comment {
        Some(c) if !c.is_empty() => {
            let value_padded = format!("{:<width$}", value, width = value_padding);
            let stripped = c.trim_start_matches(['/', ' ']);
            format!("{prefix}{name_padded} {value_padded} // {stripped}\n")
        }
        _ => format!("{prefix}{name_padded} {value}\n"),
    }
}

/// Format a section/file-level comment block. Each stored line gets its
/// leading `/` and spaces stripped, then reprefixed with `// `. Ends with an
/// extra blank line.
pub fn format_comment(comment: Option<&str>) -> String {
    let Some(c) = comment else {
        return String::new();
    };
    if c.is_empty() {
        return String::new();
    }
    let mut out = String::new();
    for line in c.lines() {
        let stripped = line.trim_start_matches(['/', ' ']);
        out.push_str("// ");
        out.push_str(stripped);
        out.push('\n');
    }
    out.push('\n');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn split_comment_no_comment() {
        let (rest, comment) = split_comment("\\-liquid_gravity 10.0");
        assert_eq!(rest, "\\-liquid_gravity 10.0");
        assert_eq!(comment, None);
    }

    #[test]
    fn split_comment_with_comment() {
        let (rest, comment) = split_comment(
            "\\-back_room_chance 0                        // % chance of a second room (default = 5%)",
        );
        assert_eq!(rest, "\\-back_room_chance 0");
        assert_eq!(
            comment.as_deref(),
            Some("% chance of a second room (default = 5%)")
        );
    }

    #[test]
    fn split_comment_trims_whitespace_before_slash_strip() {
        // Trim whitespace first, then strip leading/trailing `/`. Interior
        // whitespace is preserved after the slash strip, so extra slashes
        // and trailing whitespace get stripped but interior spaces stay.
        let (_, comment) = split_comment("value // hello");
        assert_eq!(comment.as_deref(), Some("hello"));

        let (_, comment) = split_comment("value ////  hello ////");
        assert_eq!(comment.as_deref(), Some("  hello "));
    }

    #[test]
    fn parse_chance_values_ints_ok() {
        assert_eq!(parse_chance_values("1, 2, 3, 4").unwrap(), vec![1, 2, 3, 4]);
    }

    #[test]
    fn parse_chance_values_non_int_errors() {
        // A non-int token anywhere in the list must surface as a
        // ParseIntError so callers can wrap it as InvalidValue.
        assert!(parse_chance_values("1, 2, x").is_err());
    }

    #[test]
    fn parse_chance_values_trailing_comma_errors() {
        // Trailing comma leaves an empty final token; empty parses to
        // ParseIntError. Same fate as an outright typo.
        assert!(parse_chance_values("1, 2, 3,").is_err());
    }

    #[test]
    fn to_line_no_comment() {
        assert_eq!(
            to_line("\\-", "size", 20, "5 3", 10, None),
            "\\-size                 5 3\n"
        );
    }

    #[test]
    fn to_line_with_comment() {
        assert_eq!(
            to_line("\\-", "size", 20, "5 3", 10, Some("Level size")),
            "\\-size                 5 3        // Level size\n"
        );
    }

    #[test]
    fn to_line_strips_leading_slashes_and_spaces_from_comment() {
        assert_eq!(
            to_line("\\-", "x", 4, "1", 4, Some(" hello")),
            "\\-x    1    // hello\n"
        );
    }

    #[test]
    fn format_comment_empty_and_none() {
        assert_eq!(format_comment(None), "");
        assert_eq!(format_comment(Some("")), "");
    }

    #[test]
    fn format_comment_normalizes_leading_whitespace() {
        // `format_comment` strips ALL leading `/` and space chars from
        // each stored line, then reprefixes with `// `. Double spaces
        // in the source get normalized to a single space in the output.
        let input =
            "// ------------------------------\n//  TILE CODES\n// ------------------------------";
        let out = format_comment(Some(input));
        assert_eq!(
            out,
            "// ------------------------------\n// TILE CODES\n// ------------------------------\n\n"
        );
    }

    #[test]
    fn directive_prefix_recognizes_all() {
        assert_eq!(
            DirectivePrefix::from_line("\\-foo"),
            Some(DirectivePrefix::LevelSetting)
        );
        assert_eq!(
            DirectivePrefix::from_line("\\?bar"),
            Some(DirectivePrefix::TileCode)
        );
        assert_eq!(
            DirectivePrefix::from_line("\\.baz"),
            Some(DirectivePrefix::Template)
        );
        assert_eq!(DirectivePrefix::from_line("nope"), None);
    }
}
