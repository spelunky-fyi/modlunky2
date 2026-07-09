//! `Label` + `RunLabel`: the display-side of the Category tracker.
//!
//! `Label` is a closed set of category-fragment names ("Pacifist",
//! "Low", "No Gold", ...); `RunLabel` tracks which are currently
//! present for a run and renders the composite string ("Low% Any" /
//! "Pacifist No%" / "Sunken City% Chain" / ...) via a set of hide/show
//! and percent-priority rules distilled from speedrun-category
//! conventions.
//!
//! Kept independent of process-memory concerns: pure value types +
//! logic, no `MemType` or process references. RunState feeds it a
//! label set and gets a string back.

use std::collections::BTreeSet;

/// Category the user might exclude in tracker config. Kept small so
/// it doesn't drag all the config wiring in. Serialized with the
/// legacy display names (`"No%"`, `"No Gold"`, `"Pacifist"`, `"Score"`)
/// so an existing modlunky2.json round-trips verbatim.
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, serde::Serialize, serde::Deserialize,
)]
pub enum SaveableCategory {
    #[serde(rename = "No%")]
    No,
    #[serde(rename = "No Gold")]
    NoGold,
    #[serde(rename = "Pacifist")]
    Pacifist,
    #[serde(rename = "Score")]
    Score,
}

/// Static metadata describing a single label. Kept in a match arm
/// rather than a HashMap so the compiler catches missing variants.
#[derive(Debug, Clone, Copy)]
pub struct LabelMetadata {
    pub text: &'static str,
    /// True for labels the run starts with (Pacifist, No Gold, ...).
    pub start: bool,
    /// True if callers may add this label mid-run. Defaults to `!start`
    /// (start labels are already present).
    pub add_ok: bool,
    /// True if the label should be hidden until the run is far enough
    /// along that the eventual category is clear. Defaults to `start`.
    pub hide_early: bool,
    /// Higher-priority labels win the `%` suffix. None = not eligible
    /// for `%`.
    pub percent_priority: Option<u8>,
    /// Exactly one terminus is always in the label set; it's the
    /// eventual "end goal" of the run (Any, Sunken City, CO, Death).
    pub terminus: bool,
}

/// `RunLabel::text` iterates in declaration order to assemble the
/// output; changing this order changes the rendered string ordering.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Label {
    NoJetpack,
    NoTeleporter,
    NoGold,
    Pacifist,
    IceCavesShortcut,
    Chain,
    Low,
    No,
    Any,
    SunkenCity,
    Eggplant,
    Death,
    JungleTemple,
    VolcanaTemple,
    Duat,
    Abzu,
    Millionaire,
    TrueCrown,
    CosmicOcean,
    Score,
    NoCo,
}

impl Label {
    /// Every Label in declaration order. Both used to build the static
    /// STARTING / HIDE_EARLY / TERMINI sets and to walk labels in
    /// output-string order.
    pub const ALL: &'static [Label] = &[
        Label::NoJetpack,
        Label::NoTeleporter,
        Label::NoGold,
        Label::Pacifist,
        Label::IceCavesShortcut,
        Label::Chain,
        Label::Low,
        Label::No,
        Label::Any,
        Label::SunkenCity,
        Label::Eggplant,
        Label::Death,
        Label::JungleTemple,
        Label::VolcanaTemple,
        Label::Duat,
        Label::Abzu,
        Label::Millionaire,
        Label::TrueCrown,
        Label::CosmicOcean,
        Label::Score,
        Label::NoCo,
    ];

    /// The metadata for this label. Defaulting rules for `add_ok` and
    /// `hide_early` are applied inline (add_ok = !start unless
    /// overridden; hide_early = start unless overridden).
    pub const fn meta(&self) -> LabelMetadata {
        match self {
            Label::NoJetpack => LabelMetadata {
                text: "No Jetpack",
                start: true,
                add_ok: false,
                hide_early: true,
                percent_priority: None,
                terminus: false,
            },
            Label::NoTeleporter => LabelMetadata {
                text: "No TP",
                start: true,
                add_ok: false,
                hide_early: true,
                percent_priority: None,
                terminus: false,
            },
            Label::NoGold => LabelMetadata {
                text: "No Gold",
                start: true,
                add_ok: false,
                hide_early: true,
                percent_priority: None,
                terminus: false,
            },
            Label::Pacifist => LabelMetadata {
                text: "Pacifist",
                start: true,
                add_ok: false,
                hide_early: true,
                percent_priority: None,
                terminus: false,
            },
            Label::IceCavesShortcut => LabelMetadata {
                text: "Ice Caves Shortcut",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: None,
                terminus: false,
            },
            Label::Chain => LabelMetadata {
                text: "Chain",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: None,
                terminus: false,
            },
            Label::Low => LabelMetadata {
                text: "Low",
                start: true,
                add_ok: false,
                hide_early: false,
                percent_priority: Some(5),
                terminus: false,
            },
            Label::No => LabelMetadata {
                text: "No",
                start: true,
                add_ok: false,
                hide_early: false,
                percent_priority: Some(5),
                terminus: false,
            },
            Label::Any => LabelMetadata {
                text: "Any",
                start: true,
                add_ok: false,
                hide_early: false,
                percent_priority: Some(4),
                terminus: true,
            },
            Label::SunkenCity => LabelMetadata {
                text: "Sunken City",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: Some(4),
                terminus: true,
            },
            Label::Eggplant => LabelMetadata {
                text: "Eggplant",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: Some(3),
                terminus: false,
            },
            Label::Death => LabelMetadata {
                text: "Death",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: Some(2),
                terminus: true,
            },
            Label::JungleTemple => LabelMetadata {
                text: "Jungle/Temple",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: None,
                terminus: false,
            },
            Label::VolcanaTemple => LabelMetadata {
                text: "Volcana/Temple",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: None,
                terminus: false,
            },
            Label::Duat => LabelMetadata {
                text: "Duat",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: Some(1),
                terminus: false,
            },
            Label::Abzu => LabelMetadata {
                text: "Abzu",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: Some(1),
                terminus: false,
            },
            Label::Millionaire => LabelMetadata {
                text: "Millionaire",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: None,
                terminus: false,
            },
            Label::TrueCrown => LabelMetadata {
                text: "True Crown",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: None,
                terminus: false,
            },
            Label::CosmicOcean => LabelMetadata {
                text: "Cosmic Ocean",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: Some(4),
                terminus: true,
            },
            Label::Score => LabelMetadata {
                text: "Score",
                start: false,
                add_ok: true,
                hide_early: false,
                percent_priority: None,
                terminus: false,
            },
            Label::NoCo => LabelMetadata {
                text: "No CO",
                start: true,
                add_ok: true,
                hide_early: false,
                percent_priority: None,
                terminus: false,
            },
        }
    }

    /// Translates the config-facing category enum to a Label; used to
    /// filter which labels appear in the tracker output. Only the four
    /// user-visible categories map through.
    pub fn from_saveable_category(sc: SaveableCategory) -> Label {
        match sc {
            SaveableCategory::No => Label::No,
            SaveableCategory::NoGold => Label::NoGold,
            SaveableCategory::Pacifist => Label::Pacifist,
            SaveableCategory::Score => Label::Score,
        }
    }
}

/// Container that tracks which labels are currently in the display set,
/// applies the hide/show + percent rules, and produces the final string.
/// Constructed with the STARTING set by default; the caller (RunState)
/// calls `add` / `discard` / `set_terminus` as the run progresses.
#[derive(Debug, Clone)]
pub struct RunLabel {
    set: BTreeSet<Label>,
    terminus: Label,
}

/// Errors for programmer mistakes (adding a non-add-ok label, setting
/// a non-terminus as terminus).
#[derive(Debug, thiserror::Error)]
pub enum RunLabelError {
    #[error("attempted to add label {0:?} which is not add-ok")]
    NotAddOk(Label),
    #[error("attempted to add {0:?} as a non-terminus")]
    AddedTerminus(Label),
    #[error("attempted to discard terminus {0:?}")]
    DiscardedTerminus(Label),
    #[error("expected exactly one terminus in starting set, found {found}")]
    WrongTerminusCount { found: usize },
    #[error("attempted to use {0:?} as a terminus")]
    NotATerminus(Label),
    #[error("found mutually-exclusive labels: {0:?}")]
    MutuallyExclusive(Vec<Label>),
}

impl RunLabel {
    /// Default starting set: every label marked `start`. Callers who
    /// want a custom starting set (e.g. for tests) use
    /// `RunLabel::with_starting`.
    pub fn new() -> Self {
        let starting: BTreeSet<Label> = Label::ALL
            .iter()
            .copied()
            .filter(|l| l.meta().start)
            .collect();
        Self::with_starting(starting).expect("default starting set is valid")
    }

    pub fn with_starting(starting: BTreeSet<Label>) -> Result<Self, RunLabelError> {
        let termini: Vec<Label> = starting
            .iter()
            .copied()
            .filter(|l| l.meta().terminus)
            .collect();
        if termini.len() != 1 {
            return Err(RunLabelError::WrongTerminusCount {
                found: termini.len(),
            });
        }
        let terminus = termini[0];
        let out = Self {
            set: starting,
            terminus,
        };
        out.validate()?;
        Ok(out)
    }

    /// Add a label to the current set. Returns error on non-add-ok
    /// labels or on adding a terminus (use `set_terminus` for that).
    pub fn add(&mut self, label: Label) -> Result<(), RunLabelError> {
        let meta = label.meta();
        if !meta.add_ok {
            return Err(RunLabelError::NotAddOk(label));
        }
        if meta.terminus {
            return Err(RunLabelError::AddedTerminus(label));
        }
        self.set.insert(label);
        self.validate()
    }

    /// Remove labels from the current set. Never allows discarding the
    /// terminus. No-op for labels that aren't present.
    pub fn discard(&mut self, labels: &[Label]) -> Result<(), RunLabelError> {
        for &label in labels {
            if label.meta().terminus {
                return Err(RunLabelError::DiscardedTerminus(label));
            }
        }
        for &label in labels {
            self.set.remove(&label);
        }
        self.validate()
    }

    /// Swap the current terminus for `label`. Terminus is always
    /// exactly one label; this is how it transitions (Any to Sunken
    /// City to CO, or Any to Death).
    pub fn set_terminus(&mut self, label: Label) -> Result<(), RunLabelError> {
        if !label.meta().terminus {
            return Err(RunLabelError::NotATerminus(label));
        }
        if self.terminus == label {
            return Ok(());
        }
        self.set.remove(&self.terminus);
        self.set.insert(label);
        self.terminus = label;
        self.validate()
    }

    pub fn contains(&self, label: Label) -> bool {
        self.set.contains(&label)
    }

    /// The currently-active terminus label. Tests use it to check
    /// what `update_terminus` picked without calling `text()`.
    pub fn terminus(&self) -> Label {
        self.terminus
    }

    /// Verifies mutex constraints (all termini exclusive with each
    /// other; Abzu exclusive with Duat). Called after every mutation
    /// so bad transitions surface immediately rather than during
    /// text().
    fn validate(&self) -> Result<(), RunLabelError> {
        for mut_set in Self::mutex_sets().iter() {
            let inter: Vec<Label> = mut_set
                .iter()
                .copied()
                .filter(|l| self.set.contains(l))
                .collect();
            if inter.len() > 1 {
                return Err(RunLabelError::MutuallyExclusive(inter));
            }
        }
        Ok(())
    }

    pub(crate) fn mutex_sets() -> [Vec<Label>; 2] {
        let termini: Vec<Label> = Label::ALL
            .iter()
            .copied()
            .filter(|l| l.meta().terminus)
            .collect();
        [termini, vec![Label::Abzu, Label::Duat]]
    }

    /// Produce the display string. `hide_early` toggles the
    /// hide-until-clear behavior for the label subset flagged with it;
    /// `excluded` drops labels the user has opted to omit in config.
    pub fn text(&self, hide_early: bool, excluded: &[SaveableCategory]) -> String {
        let excluded: BTreeSet<Label> = excluded
            .iter()
            .copied()
            .map(Label::from_saveable_category)
            .collect();
        let vis = self.visible(hide_early, &excluded);
        let perc = Self::percent(&vis);
        let mut parts = Vec::new();
        for &candidate in Label::ALL {
            if !vis.contains(&candidate) {
                continue;
            }
            let text = candidate.meta().text;
            if perc == Some(candidate) {
                parts.push(format!("{text}%"));
            } else {
                parts.push(text.to_string());
            }
        }
        parts.join(" ")
    }

    /// The visible-label computation. Applies exclusion,
    /// score-labels-only, hide_early, the HIDES map, and the
    /// ONLY_SHOW_WITH dependency filter in that order.
    fn visible(&self, hide_early: bool, excluded: &BTreeSet<Label>) -> BTreeSet<Label> {
        let mut vis: BTreeSet<Label> = self.set.iter().copied().collect();
        for l in excluded {
            vis.remove(l);
        }

        // SCORE swallows everything except Score + NoCo.
        if vis.contains(&Label::Score) {
            let allowed = [Label::Score, Label::NoCo];
            vis.retain(|l| allowed.contains(l));
        }

        if hide_early {
            for &l in Label::ALL {
                if l.meta().hide_early {
                    vis.remove(&l);
                }
            }
        }

        // HIDES: presence of key removes each label in value.
        for (needle, to_hide) in Self::hides_pairs() {
            if vis.contains(&needle) {
                for l in to_hide {
                    vis.remove(&l);
                }
            }
        }

        // ONLY_SHOW_WITH: key is hidden unless one of the values is
        // present alongside it.
        for (needle, requires) in Self::only_show_with_pairs() {
            if vis.contains(&needle) && requires.iter().all(|r| !vis.contains(r)) {
                vis.remove(&needle);
            }
        }

        // No% swallows NoGold. Applied after the main hides map.
        if vis.contains(&Label::No) {
            vis.remove(&Label::NoGold);
        }

        // Chain gate: with Abzu / Duat present, hide SunkenCity, and
        // hide Chain unless Low is also present (so "Chain Low% Abzu"
        // vs "Sunken City% Abzu" render correctly).
        let has_chain_term = self.set.contains(&Label::Abzu) || self.set.contains(&Label::Duat);
        if has_chain_term {
            vis.remove(&Label::SunkenCity);
            if !vis.contains(&Label::Low) {
                vis.remove(&Label::Chain);
            }
        }

        // No% also hides Low% and everything Low hides.
        if vis.contains(&Label::No) {
            vis.remove(&Label::Low);
            for l in [Label::NoTeleporter, Label::NoJetpack, Label::Any] {
                vis.remove(&l);
            }
        }

        vis
    }

    /// Highest-priority `%`-eligible label in `labels`. None when no
    /// label carries a percent_priority. Panics on a tie; only one
    /// label at the max priority should ever be present at once.
    fn percent(labels: &BTreeSet<Label>) -> Option<Label> {
        let mut found: Option<Label> = None;
        for &candidate in labels {
            let Some(p) = candidate.meta().percent_priority else {
                continue;
            };
            match found {
                None => found = Some(candidate),
                Some(f) => {
                    let fp = f.meta().percent_priority.unwrap();
                    if p == fp {
                        panic!("labels with equal percent_priority: {candidate:?} vs {f:?}");
                    }
                    if p > fp {
                        found = Some(candidate);
                    }
                }
            }
        }
        found
    }

    pub(crate) fn hides_pairs() -> Vec<(Label, Vec<Label>)> {
        vec![
            (Label::Eggplant, vec![Label::SunkenCity]),
            (
                Label::Low,
                vec![Label::NoTeleporter, Label::NoJetpack, Label::Any],
            ),
            (
                Label::Chain,
                vec![Label::JungleTemple, Label::VolcanaTemple],
            ),
            (Label::NoGold, vec![Label::Any]),
            (Label::Pacifist, vec![Label::Any]),
            (Label::Millionaire, vec![Label::Any]),
            (
                Label::CosmicOcean,
                vec![Label::NoTeleporter, Label::Abzu, Label::Duat],
            ),
        ]
    }

    pub(crate) fn only_show_with_pairs() -> Vec<(Label, Vec<Label>)> {
        vec![
            (Label::NoJetpack, vec![Label::CosmicOcean]),
            (Label::JungleTemple, vec![Label::Low]),
            (Label::VolcanaTemple, vec![Label::Low]),
            (Label::NoCo, vec![Label::Score]),
            (Label::TrueCrown, vec![Label::CosmicOcean]),
        ]
    }
}

impl Default for RunLabel {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    //! MossRanking category rendering + structural invariants and
    //! assorted edge cases.
    //!
    //! Category tables live as `&[(&[Label], &str)]` constants; a
    //! single test per group iterates the table so a rendering
    //! regression names the exact case that changed. Test-per-case
    //! would be clearer but ~95 named tests is a lot of noise for
    //! tables that are already dense to read.

    use super::*;

    /// Assemble a RunLabel from a slice + assert its rendered text
    /// with default flags (`hide_early=false`, no excluded categories).
    fn assert_render(labels: &[Label], expected: &str) {
        let set: BTreeSet<Label> = labels.iter().copied().collect();
        let rl = RunLabel::with_starting(set)
            .unwrap_or_else(|e| panic!("with_starting({labels:?}) failed: {e:?}"));
        let actual = rl.text(false, &[]);
        assert_eq!(actual, expected, "labels: {labels:?}");
    }

    // MAIN_SPEED_CATEGORIES: 17 cases.
    const MAIN_SPEED: &[(&[Label], &str)] = &[
        (&[Label::Any], "Any%"),
        (&[Label::SunkenCity], "Sunken City%"),
        (&[Label::CosmicOcean], "Cosmic Ocean%"),
        (&[Label::Low, Label::Any], "Low%"),
        (
            &[Label::Low, Label::JungleTemple, Label::Any],
            "Low% Jungle/Temple",
        ),
        (&[Label::Pacifist, Label::Low, Label::Any], "Pacifist Low%"),
        (&[Label::NoTeleporter, Label::Any], "No TP Any%"),
        (
            &[Label::NoTeleporter, Label::SunkenCity],
            "No TP Sunken City%",
        ),
        (
            &[Label::NoTeleporter, Label::SunkenCity, Label::Eggplant],
            "No TP Eggplant%",
        ),
        (&[Label::NoGold, Label::Any], "No Gold"),
        (&[Label::NoGold, Label::Low, Label::Any], "No Gold Low%"),
        (&[Label::Chain, Label::Abzu, Label::SunkenCity], "Abzu%"),
        (&[Label::Chain, Label::Duat, Label::SunkenCity], "Duat%"),
        (
            &[
                Label::NoTeleporter,
                Label::Chain,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "No TP Abzu%",
        ),
        (
            &[
                Label::NoTeleporter,
                Label::Chain,
                Label::Duat,
                Label::SunkenCity,
            ],
            "No TP Duat%",
        ),
        (
            &[Label::Chain, Label::Low, Label::Abzu, Label::SunkenCity],
            "Chain Low% Abzu",
        ),
        (
            &[Label::Chain, Label::Low, Label::Duat, Label::SunkenCity],
            "Chain Low% Duat",
        ),
    ];

    #[test]
    fn main_speed_categories_render_correctly() {
        for &(labels, expected) in MAIN_SPEED {
            assert_render(labels, expected);
        }
    }

    // MAIN_SCORE_CATEGORIES: 2 cases.
    const MAIN_SCORE: &[(&[Label], &str)] = &[
        (&[Label::Score, Label::Any], "Score"),
        (&[Label::Score, Label::NoCo, Label::Any], "Score No CO"),
    ];

    #[test]
    fn main_score_categories_render_correctly() {
        for &(labels, expected) in MAIN_SCORE {
            assert_render(labels, expected);
        }
    }

    // MISC_CATEGORIES: chain terminals with CosmicOcean,
    // Volcana/Temple, Eggplant / IceCavesShortcut mix-ins,
    // Millionaire + hide-early combinations, No%-with-terminus
    // renderings.
    const MISC: &[(&[Label], &str)] = &[
        (
            &[Label::Eggplant, Label::CosmicOcean],
            "Eggplant Cosmic Ocean%",
        ),
        (
            &[Label::Eggplant, Label::TrueCrown, Label::CosmicOcean],
            "Eggplant True Crown Cosmic Ocean%",
        ),
        (
            &[Label::NoJetpack, Label::CosmicOcean],
            "No Jetpack Cosmic Ocean%",
        ),
        (
            &[Label::Pacifist, Label::CosmicOcean],
            "Pacifist Cosmic Ocean%",
        ),
        (
            &[Label::NoGold, Label::CosmicOcean],
            "No Gold Cosmic Ocean%",
        ),
        (
            &[Label::NoGold, Label::Pacifist, Label::CosmicOcean],
            "No Gold Pacifist Cosmic Ocean%",
        ),
        (&[Label::Low, Label::CosmicOcean], "Low% Cosmic Ocean"),
        (
            &[Label::Chain, Label::Low, Label::Abzu, Label::CosmicOcean],
            "Chain Low% Cosmic Ocean",
        ),
        (
            &[Label::Low, Label::VolcanaTemple, Label::Any],
            "Low% Volcana/Temple",
        ),
        (&[Label::Low, Label::SunkenCity], "Low% Sunken City"),
        (
            &[Label::NoGold, Label::Low, Label::SunkenCity],
            "No Gold Low% Sunken City",
        ),
        (
            &[Label::NoTeleporter, Label::NoGold, Label::Any],
            "No TP No Gold",
        ),
        (&[Label::NoGold, Label::SunkenCity], "No Gold Sunken City%"),
        (
            &[Label::NoTeleporter, Label::NoGold, Label::SunkenCity],
            "No TP No Gold Sunken City%",
        ),
        (
            &[Label::NoGold, Label::Chain, Label::Abzu, Label::SunkenCity],
            "No Gold Abzu%",
        ),
        (
            &[Label::NoGold, Label::Chain, Label::Duat, Label::SunkenCity],
            "No Gold Duat%",
        ),
        (
            &[
                Label::NoGold,
                Label::Chain,
                Label::Low,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "No Gold Chain Low% Abzu",
        ),
        (
            &[
                Label::NoGold,
                Label::Chain,
                Label::Low,
                Label::Duat,
                Label::SunkenCity,
            ],
            "No Gold Chain Low% Duat",
        ),
        (&[Label::Eggplant, Label::SunkenCity], "Eggplant%"),
        (
            &[Label::Low, Label::Eggplant, Label::SunkenCity],
            "Low% Eggplant",
        ),
        (
            &[
                Label::NoTeleporter,
                Label::NoGold,
                Label::Eggplant,
                Label::SunkenCity,
            ],
            "No TP No Gold Eggplant%",
        ),
        (
            &[Label::NoGold, Label::Eggplant, Label::SunkenCity],
            "No Gold Eggplant%",
        ),
        (
            &[
                Label::NoGold,
                Label::Low,
                Label::Eggplant,
                Label::SunkenCity,
            ],
            "No Gold Low% Eggplant",
        ),
        (
            &[
                Label::Eggplant,
                Label::Chain,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "Eggplant% Abzu",
        ),
        (
            &[
                Label::Eggplant,
                Label::Chain,
                Label::Duat,
                Label::SunkenCity,
            ],
            "Eggplant% Duat",
        ),
        (
            &[
                Label::NoTeleporter,
                Label::Eggplant,
                Label::Chain,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "No TP Eggplant% Abzu",
        ),
        (
            &[
                Label::NoTeleporter,
                Label::Eggplant,
                Label::Chain,
                Label::Duat,
                Label::SunkenCity,
            ],
            "No TP Eggplant% Duat",
        ),
        (
            &[
                Label::Chain,
                Label::Low,
                Label::Eggplant,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "Chain Low% Eggplant Abzu",
        ),
        (
            &[
                Label::Chain,
                Label::Low,
                Label::Eggplant,
                Label::Duat,
                Label::SunkenCity,
            ],
            "Chain Low% Eggplant Duat",
        ),
        (
            &[
                Label::NoGold,
                Label::Chain,
                Label::Low,
                Label::Abzu,
                Label::Eggplant,
                Label::SunkenCity,
            ],
            "No Gold Chain Low% Eggplant Abzu",
        ),
        (
            &[
                Label::NoGold,
                Label::Chain,
                Label::Low,
                Label::Duat,
                Label::Eggplant,
                Label::SunkenCity,
            ],
            "No Gold Chain Low% Eggplant Duat",
        ),
        (&[Label::Millionaire, Label::Any], "Millionaire"),
        (
            &[Label::NoTeleporter, Label::Millionaire, Label::Any],
            "No TP Millionaire",
        ),
        (
            &[Label::Low, Label::Millionaire, Label::Any],
            "Low% Millionaire",
        ),
        (&[Label::No, Label::NoGold, Label::Low, Label::Any], "No%"),
        (
            &[Label::No, Label::NoGold, Label::Low, Label::SunkenCity],
            "No% Sunken City",
        ),
        (
            &[Label::IceCavesShortcut, Label::Any],
            "Ice Caves Shortcut Any%",
        ),
        (
            &[Label::IceCavesShortcut, Label::Low, Label::Any],
            "Ice Caves Shortcut Low%",
        ),
        (
            &[
                Label::Pacifist,
                Label::IceCavesShortcut,
                Label::Low,
                Label::Any,
            ],
            "Pacifist Ice Caves Shortcut Low%",
        ),
        (
            &[
                Label::IceCavesShortcut,
                Label::Low,
                Label::Millionaire,
                Label::Any,
            ],
            "Ice Caves Shortcut Low% Millionaire",
        ),
        (
            &[Label::IceCavesShortcut, Label::Low, Label::SunkenCity],
            "Ice Caves Shortcut Low% Sunken City",
        ),
    ];

    #[test]
    fn misc_categories_render_correctly() {
        for &(labels, expected) in MISC {
            assert_render(labels, expected);
        }
    }

    // PACIFIST_CATEGORIES.
    const PACIFIST: &[(&[Label], &str)] = &[
        (&[Label::Pacifist, Label::Any], "Pacifist"),
        (
            &[Label::Pacifist, Label::SunkenCity],
            "Pacifist Sunken City%",
        ),
        (&[Label::Pacifist, Label::Low, Label::Any], "Pacifist Low%"),
        (
            &[Label::Pacifist, Label::CosmicOcean],
            "Pacifist Cosmic Ocean%",
        ),
        (
            &[Label::NoTeleporter, Label::Pacifist, Label::Any],
            "No TP Pacifist",
        ),
        (
            &[Label::NoTeleporter, Label::Pacifist, Label::SunkenCity],
            "No TP Pacifist Sunken City%",
        ),
        (
            &[Label::NoGold, Label::Pacifist, Label::Any],
            "No Gold Pacifist",
        ),
        (
            &[Label::NoGold, Label::Pacifist, Label::SunkenCity],
            "No Gold Pacifist Sunken City%",
        ),
        (
            &[Label::NoGold, Label::Pacifist, Label::Low, Label::Any],
            "No Gold Pacifist Low%",
        ),
        (
            &[Label::NoGold, Label::Pacifist, Label::CosmicOcean],
            "No Gold Pacifist Cosmic Ocean%",
        ),
        (
            &[Label::Pacifist, Label::Low, Label::SunkenCity],
            "Pacifist Low% Sunken City",
        ),
        (
            &[
                Label::NoGold,
                Label::Pacifist,
                Label::Low,
                Label::SunkenCity,
            ],
            "No Gold Pacifist Low% Sunken City",
        ),
        (
            &[
                Label::Pacifist,
                Label::Chain,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "Pacifist Abzu%",
        ),
        (
            &[
                Label::Pacifist,
                Label::Chain,
                Label::Duat,
                Label::SunkenCity,
            ],
            "Pacifist Duat%",
        ),
        (
            &[
                Label::Pacifist,
                Label::Chain,
                Label::Low,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "Pacifist Chain Low% Abzu",
        ),
        (
            &[
                Label::Pacifist,
                Label::Chain,
                Label::Low,
                Label::Duat,
                Label::SunkenCity,
            ],
            "Pacifist Chain Low% Duat",
        ),
        (
            &[
                Label::NoGold,
                Label::Pacifist,
                Label::Chain,
                Label::Low,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "No Gold Pacifist Chain Low% Abzu",
        ),
        (
            &[
                Label::NoGold,
                Label::Pacifist,
                Label::Chain,
                Label::Low,
                Label::Duat,
                Label::SunkenCity,
            ],
            "No Gold Pacifist Chain Low% Duat",
        ),
        (
            &[Label::Pacifist, Label::Eggplant, Label::SunkenCity],
            "Pacifist Eggplant%",
        ),
        (
            &[
                Label::Pacifist,
                Label::Low,
                Label::Eggplant,
                Label::SunkenCity,
            ],
            "Pacifist Low% Eggplant",
        ),
        (
            &[
                Label::NoGold,
                Label::Pacifist,
                Label::Eggplant,
                Label::SunkenCity,
            ],
            "No Gold Pacifist Eggplant%",
        ),
        (
            &[
                Label::NoGold,
                Label::Pacifist,
                Label::Low,
                Label::Eggplant,
                Label::SunkenCity,
            ],
            "No Gold Pacifist Low% Eggplant",
        ),
        (
            &[
                Label::Pacifist,
                Label::Chain,
                Label::Low,
                Label::Eggplant,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "Pacifist Chain Low% Eggplant Abzu",
        ),
        (
            &[
                Label::Pacifist,
                Label::Chain,
                Label::Low,
                Label::Eggplant,
                Label::Duat,
                Label::SunkenCity,
            ],
            "Pacifist Chain Low% Eggplant Duat",
        ),
        (
            &[
                Label::NoGold,
                Label::Pacifist,
                Label::Chain,
                Label::Low,
                Label::Eggplant,
                Label::Abzu,
                Label::SunkenCity,
            ],
            "No Gold Pacifist Chain Low% Eggplant Abzu",
        ),
        (
            &[
                Label::NoGold,
                Label::Pacifist,
                Label::Chain,
                Label::Low,
                Label::Eggplant,
                Label::Duat,
                Label::SunkenCity,
            ],
            "No Gold Pacifist Chain Low% Eggplant Duat",
        ),
        (
            &[Label::Pacifist, Label::No, Label::Low, Label::Any],
            "Pacifist No%",
        ),
        (
            &[Label::Pacifist, Label::No, Label::Low, Label::SunkenCity],
            "Pacifist No% Sunken City",
        ),
        (
            &[
                Label::Pacifist,
                Label::IceCavesShortcut,
                Label::Low,
                Label::Any,
            ],
            "Pacifist Ice Caves Shortcut Low%",
        ),
        (
            &[
                Label::Pacifist,
                Label::IceCavesShortcut,
                Label::Low,
                Label::SunkenCity,
            ],
            "Pacifist Ice Caves Shortcut Low% Sunken City",
        ),
    ];

    #[test]
    fn pacifist_categories_render_correctly() {
        for &(labels, expected) in PACIFIST {
            assert_render(labels, expected);
        }
    }

    // ASSORTED: intermediate + Chain-Death / Chain-CO cases the main
    // tables don't cover.
    const ASSORTED: &[(&[Label], &str)] = &[
        (
            &[Label::Chain, Label::Low, Label::SunkenCity],
            "Chain Low% Sunken City",
        ),
        (&[Label::Chain, Label::SunkenCity], "Chain Sunken City%"),
        (&[Label::Chain, Label::Abzu, Label::Death], "Death% Abzu"),
        (
            &[Label::Chain, Label::Low, Label::Abzu, Label::Death],
            "Chain Low% Death Abzu",
        ),
        (&[Label::Eggplant, Label::Death], "Eggplant% Death"),
        (
            &[
                Label::NoJetpack,
                Label::Chain,
                Label::Low,
                Label::Abzu,
                Label::CosmicOcean,
            ],
            "Chain Low% Cosmic Ocean",
        ),
        (
            &[
                Label::NoJetpack,
                Label::Chain,
                Label::Abzu,
                Label::CosmicOcean,
            ],
            "No Jetpack Cosmic Ocean%",
        ),
        (
            &[
                Label::NoJetpack,
                Label::Chain,
                Label::JungleTemple,
                Label::Duat,
                Label::CosmicOcean,
            ],
            "No Jetpack Cosmic Ocean%",
        ),
    ];

    #[test]
    fn assorted_categories_render_correctly() {
        for &(labels, expected) in ASSORTED {
            assert_render(labels, expected);
        }
    }

    // TRUE_CROWN_CATEGORIES. Score-terminus reverts to underlying
    // category when SCORE is excluded via the tracker-config
    // `excluded_categories`.
    const TRUE_CROWN: &[(&[Label], &str, &str)] = &[
        (
            &[Label::Score, Label::TrueCrown, Label::CosmicOcean],
            "Score",
            "True Crown Cosmic Ocean%",
        ),
        (
            &[Label::Score, Label::TrueCrown, Label::Any],
            "Score",
            "Any%",
        ),
    ];

    #[test]
    fn true_crown_categories_render_with_and_without_score_exclusion() {
        for &(labels, expected, expected_no_score) in TRUE_CROWN {
            let set: BTreeSet<Label> = labels.iter().copied().collect();
            let rl = RunLabel::with_starting(set).unwrap();
            assert_eq!(rl.text(false, &[]), expected, "labels: {labels:?}");
            assert_eq!(
                rl.text(false, &[SaveableCategory::Score]),
                expected_no_score,
                "labels: {labels:?}, SCORE excluded"
            );
        }
    }

    // Structural visibility-graph invariants.
    //
    // Bipartite: no Label appears on BOTH sides of the visibility
    // graph. A label that both hides something AND is hidden by
    // something else would make output depend on the order HIDES +
    // ONLY_SHOW_WITH get applied.
    //
    // Not-mutex: HIDES / ONLY_SHOW_WITH edges must not connect two
    // labels that are already mutually-exclusive; such an edge is
    // trivially unreachable and signals a table typo.

    #[test]
    fn visibility_graph_is_bipartite() {
        // Build the edge set: (label, depends_on) for every HIDES
        // pair plus every ONLY_SHOW_WITH pair. Then walk the "label
        // side" of each edge and assert it never appears on the "dep
        // side" of any edge.
        let mut edges: Vec<(Label, Label)> = Vec::new();
        for (dep, hides_set) in RunLabel::hides_pairs() {
            for l in hides_set {
                edges.push((l, dep));
            }
        }
        for (label, with_set) in RunLabel::only_show_with_pairs() {
            for dep in with_set {
                edges.push((label, dep));
            }
        }

        let label_side: BTreeSet<Label> = edges.iter().map(|&(l, _)| l).collect();
        let dep_side: BTreeSet<Label> = edges.iter().map(|&(_, d)| d).collect();

        let intersection: Vec<Label> = label_side.intersection(&dep_side).copied().collect();
        assert!(
            intersection.is_empty(),
            "labels that appear on BOTH sides of the visibility graph: {intersection:?}"
        );
    }

    #[test]
    fn visibility_edges_never_straddle_a_mutex_set() {
        let mutex = RunLabel::mutex_sets();
        let mut bad = Vec::new();
        for (dep, hides_set) in RunLabel::hides_pairs() {
            for l in hides_set {
                for set in &mutex {
                    if set.contains(&l) && set.contains(&dep) {
                        bad.push(("_HIDES", l, dep));
                    }
                }
            }
        }
        for (label, with_set) in RunLabel::only_show_with_pairs() {
            for dep in with_set {
                for set in &mutex {
                    if set.contains(&label) && set.contains(&dep) {
                        bad.push(("_ONLY_SHOW_WITH", label, dep));
                    }
                }
            }
        }
        assert!(
            bad.is_empty(),
            "visibility edges straddling a mutex set: {bad:?}"
        );
    }
}
