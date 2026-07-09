use std::io::Write;

use indexmap::IndexMap;
use once_cell::sync::Lazy;

use crate::error::{LevelError, Result};
use crate::utils::{DirectivePrefix, format_comment, split_comment, to_line};

pub const VALID_LEVEL_SETTINGS: &[&str] = &[
    "altar_room_chance",
    "back_room_chance",
    "back_room_hidden_door_cache_chance",
    "back_room_hidden_door_chance",
    "back_room_interconnection_chance",
    "background_chance",
    "flagged_liquid_rooms",
    "floor_bottom_spread_chance",
    "floor_side_spread_chance",
    "ground_background_chance",
    "idol_room_chance",
    "liquid_gravity",
    "machine_bigroom_chance",
    "machine_rewardroom_chance",
    "machine_tallroom_chance",
    "machine_wideroom_chance",
    "max_liquid_particles",
    "mount_chance",
    "size",
];

static NAME_PADDING: Lazy<usize> = Lazy::new(|| {
    VALID_LEVEL_SETTINGS
        .iter()
        .map(|s| s.len())
        .max()
        .unwrap_or(0)
        + 4
});

const VALUE_PADDING: usize = 10;

#[derive(Debug, Clone, PartialEq)]
pub enum LevelSettingValue {
    Int(i64),
    Float(f64),
    Size(String, String),
}

impl LevelSettingValue {
    fn to_str(&self) -> String {
        match self {
            Self::Int(v) => v.to_string(),
            // Debug format on f64 always includes a decimal point, so
            // 10.0 serializes back as `"10.0"`, not `"10"`.
            Self::Float(v) => format!("{:?}", v),
            Self::Size(a, b) => format!("{a} {b}"),
        }
    }
}

#[derive(Debug, Clone)]
pub struct LevelSetting {
    pub name: String,
    pub value: LevelSettingValue,
    pub comment: Option<String>,
}

impl LevelSetting {
    pub const PREFIX: &'static str = DirectivePrefix::LevelSetting.as_str();

    pub fn parse(line: &str) -> Result<Self> {
        let (rest, comment) = split_comment(line);
        let mut split = rest.splitn(2, char::is_whitespace);
        let directive = split
            .next()
            .ok_or_else(|| LevelError::MissingName(line.to_string()))?;
        let value_str = split
            .next()
            .ok_or_else(|| LevelError::MissingValue(rest.clone()))?
            .trim();

        let name = directive
            .strip_prefix(Self::PREFIX)
            .ok_or_else(|| LevelError::MissingName(line.to_string()))?;
        if name.is_empty() {
            return Err(LevelError::MissingName(line.to_string()));
        }

        let value = parse_value(name, value_str)?;
        Ok(Self {
            name: name.to_string(),
            value,
            comment,
        })
    }

    pub fn to_line(&self) -> String {
        to_line(
            Self::PREFIX,
            &self.name,
            *NAME_PADDING,
            &self.value.to_str(),
            VALUE_PADDING,
            self.comment.as_deref(),
        )
    }
}

fn parse_value(name: &str, raw: &str) -> Result<LevelSettingValue> {
    match name {
        "size" => {
            let parts: Vec<&str> = raw.split_whitespace().collect();
            if parts.len() != 2 {
                return Err(LevelError::BadSize(parts.len()));
            }
            Ok(LevelSettingValue::Size(
                parts[0].to_string(),
                parts[1].to_string(),
            ))
        }
        "liquid_gravity" => raw
            .parse::<f64>()
            .map(LevelSettingValue::Float)
            .map_err(|e| LevelError::InvalidValue {
                name: name.to_string(),
                value: raw.to_string(),
                reason: e.to_string(),
            }),
        _ => raw
            .parse::<i64>()
            .map(LevelSettingValue::Int)
            .map_err(|e| LevelError::InvalidValue {
                name: name.to_string(),
                value: raw.to_string(),
                reason: e.to_string(),
            }),
    }
}

#[derive(Debug, Default, Clone)]
pub struct LevelSettings {
    inner: IndexMap<String, LevelSetting>,
    pub comment: Option<String>,
}

impl LevelSettings {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn all(&self) -> impl Iterator<Item = &LevelSetting> {
        self.inner.values()
    }

    pub fn get(&self, name: &str) -> Option<&LevelSetting> {
        self.inner.get(name)
    }

    pub fn set(&mut self, obj: LevelSetting) {
        self.inner.insert(obj.name.clone(), obj);
    }

    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    pub fn write<W: Write>(&self, writer: &mut W) -> Result<()> {
        writer.write_all(format_comment(self.comment.as_deref()).as_bytes())?;
        for setting in self.inner.values() {
            writer.write_all(setting.to_line().as_bytes())?;
        }
        writer.write_all(b"\n")?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_int_setting() {
        let s = LevelSetting::parse("\\-back_room_chance 0                        // % chance of a second room (default = 5%)").unwrap();
        assert_eq!(s.name, "back_room_chance");
        assert_eq!(s.value, LevelSettingValue::Int(0));
        assert_eq!(
            s.comment.as_deref(),
            Some("% chance of a second room (default = 5%)")
        );
    }

    #[test]
    fn parse_float_setting() {
        let s = LevelSetting::parse("\\-liquid_gravity 10.0                       // Liquid vertical gravity (default -10.0)").unwrap();
        assert_eq!(s.name, "liquid_gravity");
        match s.value {
            LevelSettingValue::Float(v) => assert!((v - 10.0).abs() < f64::EPSILON),
            other => panic!("wrong variant: {other:?}"),
        }
    }

    #[test]
    fn parse_size_setting() {
        let s = LevelSetting::parse("\\-size 5 3").unwrap();
        assert_eq!(s.name, "size");
        assert_eq!(s.value, LevelSettingValue::Size("5".into(), "3".into()));
        assert_eq!(s.comment, None);
    }

    #[test]
    fn parse_missing_name_errors() {
        // Bare prefix + value is not a valid setting; the empty name
        // must trip `MissingName`, not fall through to `parse_value`.
        assert!(matches!(
            LevelSetting::parse("\\- 5"),
            Err(LevelError::MissingName(_))
        ));
    }

    #[test]
    fn parse_missing_value_errors() {
        // Name-only line has no value token after the whitespace split.
        assert!(matches!(
            LevelSetting::parse("\\-back_room_chance"),
            Err(LevelError::MissingValue(_))
        ));
    }

    #[test]
    fn parse_size_with_one_token_errors() {
        // BadSize is the error the size directive reports when the
        // 2-int contract is broken.
        let err = LevelSetting::parse("\\-size 5");
        assert!(matches!(err, Err(LevelError::BadSize(1))), "got {err:?}");
    }

    #[test]
    fn parse_size_with_three_tokens_errors() {
        let err = LevelSetting::parse("\\-size 5 3 2");
        assert!(matches!(err, Err(LevelError::BadSize(3))), "got {err:?}");
    }

    #[test]
    fn float_roundtrips_with_decimal() {
        let s = LevelSetting {
            name: "liquid_gravity".into(),
            value: LevelSettingValue::Float(10.0),
            comment: None,
        };
        let line = s.to_line();
        assert!(line.contains("10.0"), "got: {line:?}");
    }
}
