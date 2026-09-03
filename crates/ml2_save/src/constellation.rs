//! The Cosmic Ocean constellation.
//!
//! Finishing the Cosmic Ocean generates a star chart, which the game then
//! shows on the ending screen. It is stored as up to 45 stars, each with a
//! position, size and color, plus up to 90 lines connecting them by index.
//!
//! The block sits in the version-dependent tail of the file. It is the
//! last field before the checksum in v25 and v26, but not in v30, where
//! 72 undecoded bytes follow it.
//!
//! # How this was confirmed
//!
//! Checked against a real save containing a five-star, four-line
//! constellation, compared side by side with what the game drew:
//!
//! - The five stored positions match the five drawn stars, once `x` is
//!   negated. Higher `x` moves a star left; higher `y` moves it down.
//! - Stored coordinates span roughly -1.35 to 1.35 on both axes, which is
//!   exactly the range [`Constellation::from_points`] maps into.
//! - The four lines, `0-3, 3-2, 2-1, 1-4`, trace the drawn chain in order.
//! - Every star read `(1, 1, 1)` for its color and `(0.12, 0.42, 0.00)`
//!   for the next three floats, and the game drew white stars with green
//!   halos. That settles a disagreement between the two sources this was
//!   built from: Overlunky's `halo_red/green/blue` naming is right, and
//!   the spelunky.fyi editor's reading of those slots as a light radius
//!   and bleed is not.
//!
//! # Availability
//!
//! The constellation lives in the part of the file whose offsets depend on
//! the save version, so it is only reachable when
//! [`Layout::has_constellation`](crate::Layout::has_constellation) is
//! true. Reading returns `None` otherwise and writing fails, rather than
//! either one guessing at an offset.

use serde::{Deserialize, Serialize};

use crate::{Result, SaveError, SaveFile, layout};

/// One star.
///
/// Positions are in a normalized space centred on the origin and running
/// to about 1.35 in each direction, with x increasing to the *left* and y
/// increasing downward. [`Constellation::from_points`] converts from
/// ordinary image coordinates, which is usually what a caller has.
#[derive(Debug, Clone, Copy, PartialEq, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConstellationStar {
    /// Star variant. The game picks small values, biased toward 0.
    pub kind: u32,
    /// Horizontal position. Higher moves the star left.
    pub x: f32,
    /// Vertical position. Higher moves the star down.
    pub y: f32,
    /// Radius of the star itself.
    pub size: f32,
    /// Red channel of the star.
    pub red: f32,
    /// Green channel of the star.
    pub green: f32,
    /// Blue channel of the star.
    pub blue: f32,
    /// Opacity of the star.
    pub alpha: f32,
    /// Red channel of the glow. The game's own constellations use a green
    /// halo, around `(0.12, 0.42, 0.00)`.
    pub halo_red: f32,
    /// Green channel of the glow.
    pub halo_green: f32,
    /// Blue channel of the glow.
    pub halo_blue: f32,
    /// Opacity of the glow.
    pub halo_alpha: f32,
    /// Draws an orange ring around the star, for Canis.
    pub canis_ring: bool,
    /// Draws a red ring around the star, for Fidelis.
    pub fidelis_ring: bool,
    /// Unidentified trailing word. Possibly to do with how stars are laid
    /// out along the path, or which are offshoots. Preserved on read so a
    /// round trip does not lose it.
    pub unknown: u32,
}

/// A line joining two stars, by their index into
/// [`Constellation::stars`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConstellationLine {
    /// Index of the star the line starts at.
    pub from: u8,
    /// Index of the star the line ends at.
    pub to: u8,
}

/// A whole constellation, trimmed to the counts the file declares.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Constellation {
    /// The stars in use. At most [`layout::CONSTELLATION_MAX_STARS`].
    pub stars: Vec<ConstellationStar>,
    /// The lines in use. At most [`layout::CONSTELLATION_MAX_LINES`].
    pub lines: Vec<ConstellationLine>,
    /// Overall scale of the chart. The game uses values around 1 to 10.
    pub scale: f32,
    /// Tints the connecting lines. Zero draws them white; the game raises
    /// it toward 1.0 as NPC kills climb, taking the lines pink and then
    /// deep red for a Criminalis ending.
    pub line_red_intensity: f32,
}

impl Constellation {
    /// Builds a constellation from plain 2D points, the way an SVG or a
    /// drawing tool would give them.
    ///
    /// `points` are in an image-style space: x to the right, y down,
    /// bounded by `width` and `height`. They are mapped into the game's
    /// space with the same transform the spelunky.fyi editor uses, so a
    /// shape imported here lands where it did there. Points past
    /// [`layout::CONSTELLATION_MAX_STARS`] are dropped.
    ///
    /// Stars get a plain white default appearance. Callers wanting the
    /// game's slightly random look can vary the fields afterward.
    pub fn from_points(points: &[(f32, f32)], width: f32, height: f32) -> Self {
        let width = if width == 0.0 { 1.0 } else { width };
        let height = if height == 0.0 { 1.0 } else { height };
        let stars = points
            .iter()
            .take(layout::CONSTELLATION_MAX_STARS)
            .map(|(px, py)| ConstellationStar {
                kind: 0,
                x: ((px / width) * 3.5 - 1.5) * -0.9,
                y: ((py / height) * 3.5 - 1.5) * 0.9,
                size: 1.0,
                red: 1.0,
                green: 1.0,
                blue: 1.0,
                alpha: 0.8,
                halo_red: 1.0,
                halo_green: 1.0,
                halo_blue: 1.0,
                halo_alpha: 0.6,
                canis_ring: false,
                fidelis_ring: false,
                unknown: 0,
            })
            .collect();
        Self {
            stars,
            lines: Vec::new(),
            scale: 4.0,
            line_red_intensity: 0.0,
        }
    }

    /// Converts a star's position back to image-style coordinates, the
    /// inverse of the mapping [`Constellation::from_points`] applies.
    pub fn to_point(star: &ConstellationStar, width: f32, height: f32) -> (f32, f32) {
        (
            (star.x / -0.9 + 1.5) / 3.5 * width,
            (star.y / 0.9 + 1.5) / 3.5 * height,
        )
    }

    /// Checks that no line refers to a star that is not there.
    ///
    /// The game indexes straight into the star array, so an out-of-range
    /// index would have it read a star that does not exist.
    fn validate(&self) -> Result<()> {
        if self.stars.len() > layout::CONSTELLATION_MAX_STARS {
            return Err(SaveError::IndexOutOfRange {
                what: "star",
                index: self.stars.len(),
                count: layout::CONSTELLATION_MAX_STARS,
            });
        }
        if self.lines.len() > layout::CONSTELLATION_MAX_LINES {
            return Err(SaveError::IndexOutOfRange {
                what: "line",
                index: self.lines.len(),
                count: layout::CONSTELLATION_MAX_LINES,
            });
        }
        for line in &self.lines {
            for end in [line.from, line.to] {
                if usize::from(end) >= self.stars.len() {
                    return Err(SaveError::IndexOutOfRange {
                        what: "line endpoint",
                        index: usize::from(end),
                        count: self.stars.len(),
                    });
                }
            }
        }
        Ok(())
    }
}

impl SaveFile {
    /// Reads the constellation, or `None` if this file's tail layout is
    /// not one this build recognizes.
    pub fn constellation(&self) -> Option<Constellation> {
        let tail = self.layout().tail?;
        let star_count = usize::from(self.read_u8(tail.constellation.start))
            .min(layout::CONSTELLATION_MAX_STARS);
        let line_count = usize::from(self.read_u8(tail.constellation_line_count()))
            .min(layout::CONSTELLATION_MAX_LINES);

        let stars = (0..star_count)
            .map(|i| {
                let at = tail.constellation_star(i);
                ConstellationStar {
                    kind: self.read_u32(at),
                    x: self.read_f32(at + 4),
                    y: self.read_f32(at + 8),
                    size: self.read_f32(at + 12),
                    red: self.read_f32(at + 16),
                    green: self.read_f32(at + 20),
                    blue: self.read_f32(at + 24),
                    alpha: self.read_f32(at + 28),
                    halo_red: self.read_f32(at + 32),
                    halo_green: self.read_f32(at + 36),
                    halo_blue: self.read_f32(at + 40),
                    halo_alpha: self.read_f32(at + 44),
                    canis_ring: self.read_bool(at + 48),
                    fidelis_ring: self.read_bool(at + 49),
                    unknown: self.read_u32(at + 52),
                }
            })
            .collect();

        let lines_at = tail.constellation_lines();
        let lines = (0..line_count)
            .map(|i| ConstellationLine {
                from: self.read_u8(lines_at + i * layout::CONSTELLATION_LINE_LEN),
                to: self.read_u8(lines_at + i * layout::CONSTELLATION_LINE_LEN + 1),
            })
            .collect();

        Some(Constellation {
            stars,
            lines,
            scale: self.read_f32(tail.constellation_scale()),
            line_red_intensity: self.read_f32(tail.constellation_line_red_intensity()),
        })
    }

    /// How many stars the constellation has, without decoding all of them.
    ///
    /// `None` means the block could not be located, which is not the same
    /// as a save that simply has no constellation yet; that reads
    /// `Some(0)`.
    pub fn constellation_star_count(&self) -> Option<u8> {
        let tail = self.layout().tail?;
        Some(self.read_u8(tail.constellation.start))
    }

    /// Replaces the constellation.
    ///
    /// Star and line slots past the new counts are zeroed rather than left
    /// alone. The alternative leaves stale stars sitting behind a smaller
    /// count, so the file would disagree with itself about what it holds;
    /// this way what is written is exactly what was asked for.
    ///
    /// Fails with [`SaveError::ConstellationUnavailable`] if this build
    /// cannot locate the block, since writing it at a guessed offset would
    /// destroy whatever is actually there.
    pub fn set_constellation(&mut self, constellation: &Constellation) -> Result<()> {
        constellation.validate()?;
        let layout = self.layout();
        let tail = layout.tail.ok_or(SaveError::ConstellationUnavailable {
            version: layout.version,
            len: layout.file_len,
        })?;

        self.write_u8(tail.constellation.start, constellation.stars.len() as u8);
        for i in 0..layout::CONSTELLATION_MAX_STARS {
            let at = tail.constellation_star(i);
            let star = constellation.stars.get(i).copied().unwrap_or_default();
            self.write_u32(at, star.kind);
            for (n, value) in [
                star.x,
                star.y,
                star.size,
                star.red,
                star.green,
                star.blue,
                star.alpha,
                star.halo_red,
                star.halo_green,
                star.halo_blue,
                star.halo_alpha,
            ]
            .into_iter()
            .enumerate()
            {
                self.write_f32(at + 4 + n * 4, value);
            }
            self.write_bool(at + 48, star.canis_ring);
            self.write_bool(at + 49, star.fidelis_ring);
            self.write_u32(at + 52, star.unknown);
        }

        self.write_f32(tail.constellation_scale(), constellation.scale);
        self.write_u8(
            tail.constellation_line_count(),
            constellation.lines.len() as u8,
        );
        let lines_at = tail.constellation_lines();
        for i in 0..layout::CONSTELLATION_MAX_LINES {
            let line = constellation.lines.get(i).copied().unwrap_or_default();
            self.write_u8(lines_at + i * layout::CONSTELLATION_LINE_LEN, line.from);
            self.write_u8(lines_at + i * layout::CONSTELLATION_LINE_LEN + 1, line.to);
        }
        self.write_f32(
            tail.constellation_line_red_intensity(),
            constellation.line_red_intensity,
        );
        Ok(())
    }
}

impl Constellation {
    /// A stable signature for this constellation's shape.
    ///
    /// Every snapshot taken after a Cosmic Ocean win holds the same
    /// chart, so a gallery built from an archive would otherwise show the
    /// same picture twenty times over. Grouping on this collapses them.
    ///
    /// Positions and the line list are what make a constellation
    /// recognizable, so only those go in. Colors and sizes are left out
    /// deliberately: they carry per-star randomness that would make two
    /// captures of one chart look like two different charts.
    pub fn signature(&self) -> String {
        use std::fmt::Write as _;
        let mut out = String::with_capacity(self.stars.len() * 16);
        for star in &self.stars {
            // Four decimals is far finer than the chart is ever drawn at,
            // and keeps float formatting identical across platforms.
            let _ = write!(out, "{:.4},{:.4};", star.x, star.y);
        }
        out.push('|');
        for line in &self.lines {
            let _ = write!(out, "{}-{};", line.from, line.to);
        }
        out
    }

    /// Whether there is anything to draw.
    pub fn is_empty(&self) -> bool {
        self.stars.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tests::blank_save;

    #[test]
    fn round_trips_through_the_file() {
        let mut save = blank_save(13862, 30);
        let constellation = Constellation {
            stars: vec![
                ConstellationStar {
                    kind: 2,
                    x: 0.25,
                    y: -0.5,
                    size: 1.5,
                    red: 0.9,
                    green: 0.8,
                    blue: 0.7,
                    alpha: 0.75,
                    halo_red: 0.6,
                    halo_green: 0.5,
                    halo_blue: 0.4,
                    halo_alpha: 0.55,
                    canis_ring: true,
                    fidelis_ring: false,
                    unknown: 7,
                },
                ConstellationStar {
                    kind: 0,
                    x: -0.25,
                    y: 0.5,
                    ..Default::default()
                },
            ],
            lines: vec![ConstellationLine { from: 0, to: 1 }],
            scale: 4.5,
            line_red_intensity: 0.25,
        };
        save.set_constellation(&constellation).unwrap();
        assert_eq!(save.constellation().unwrap(), constellation);
        assert_eq!(save.constellation_star_count(), Some(2));
    }

    /// A line pointing at a star that was removed would have the game read
    /// past the end of the stars it believes it has.
    #[test]
    fn rejects_lines_pointing_at_missing_stars() {
        let mut save = blank_save(13862, 30);
        let constellation = Constellation {
            stars: vec![ConstellationStar::default()],
            lines: vec![ConstellationLine { from: 0, to: 3 }],
            scale: 4.0,
            line_red_intensity: 0.0,
        };
        let err = save.set_constellation(&constellation).unwrap_err();
        assert!(matches!(
            err,
            SaveError::IndexOutOfRange {
                what: "line endpoint",
                ..
            }
        ));
    }

    #[test]
    fn rejects_too_many_stars() {
        let mut save = blank_save(13862, 30);
        let constellation = Constellation {
            stars: vec![ConstellationStar::default(); layout::CONSTELLATION_MAX_STARS + 1],
            ..Default::default()
        };
        assert!(save.set_constellation(&constellation).is_err());
    }

    /// Shrinking the constellation must not leave the dropped stars in the
    /// file, where a later reader could pick them up.
    #[test]
    fn clears_slots_past_the_new_count() {
        let mut save = blank_save(13862, 30);
        let many = Constellation {
            stars: vec![
                ConstellationStar {
                    size: 9.0,
                    ..Default::default()
                };
                10
            ],
            ..Default::default()
        };
        save.set_constellation(&many).unwrap();
        let few = Constellation {
            stars: vec![ConstellationStar::default(); 2],
            ..Default::default()
        };
        save.set_constellation(&few).unwrap();

        let at = save.layout().tail.unwrap().constellation_star(5);
        assert_eq!(
            save.read_f32(at + 12),
            0.0,
            "star 5 should have been zeroed"
        );
    }

    /// The gallery groups on this, so two captures of one chart have to
    /// agree and two different charts have to differ.
    #[test]
    fn signature_identifies_a_shape() {
        let a = Constellation {
            stars: vec![
                ConstellationStar {
                    x: 0.25,
                    y: -0.5,
                    ..Default::default()
                },
                ConstellationStar {
                    x: -0.25,
                    y: 0.5,
                    ..Default::default()
                },
            ],
            lines: vec![ConstellationLine { from: 0, to: 1 }],
            scale: 4.0,
            line_red_intensity: 0.0,
        };
        assert_eq!(a.signature(), a.clone().signature());

        let mut moved = a.clone();
        moved.stars[1].x = 0.9;
        assert_ne!(
            a.signature(),
            moved.signature(),
            "moving a star is a new chart"
        );

        let mut rejoined = a.clone();
        rejoined.lines = vec![ConstellationLine { from: 1, to: 0 }];
        assert_ne!(
            a.signature(),
            rejoined.signature(),
            "the lines are part of the shape"
        );
    }

    /// The reason colors are excluded: the game randomizes them per
    /// star, so two snapshots of the same chart would otherwise look like
    /// two charts and show up twice in the gallery.
    #[test]
    fn signature_ignores_color_and_size() {
        let base = Constellation {
            stars: vec![ConstellationStar {
                x: 0.25,
                y: -0.5,
                size: 1.0,
                red: 1.0,
                ..Default::default()
            }],
            ..Default::default()
        };
        let mut recolored = base.clone();
        recolored.stars[0].red = 0.2;
        recolored.stars[0].size = 3.0;
        recolored.stars[0].halo_green = 0.7;

        assert_eq!(base.signature(), recolored.signature());
    }

    #[test]
    fn an_empty_constellation_reports_itself_empty() {
        assert!(Constellation::default().is_empty());
        assert!(
            !Constellation {
                stars: vec![ConstellationStar::default()],
                ..Default::default()
            }
            .is_empty()
        );
    }

    /// Points go in as image coordinates and come back out the same, so an
    /// imported shape can be re-exported without drifting.
    #[test]
    fn point_conversion_round_trips() {
        let constellation = Constellation::from_points(&[(128.0, 384.0)], 512.0, 512.0);
        let (x, y) = Constellation::to_point(&constellation.stars[0], 512.0, 512.0);
        assert!((x - 128.0).abs() < 0.01, "x was {x}");
        assert!((y - 384.0).abs() < 0.01, "y was {y}");
    }

    #[test]
    fn from_points_caps_at_the_maximum() {
        let points: Vec<(f32, f32)> = (0..80).map(|i| (i as f32, i as f32)).collect();
        let constellation = Constellation::from_points(&points, 512.0, 512.0);
        assert_eq!(constellation.stars.len(), layout::CONSTELLATION_MAX_STARS);
    }
}
