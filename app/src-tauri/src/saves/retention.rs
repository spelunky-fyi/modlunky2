//! Which automatic snapshots keep a restorable save.
//!
//! # Pruning must not cost you the history
//!
//! Every archived save can produce a `SaveSummary`, and those summaries
//! are what the stats views chart over time. Deleting old snapshots
//! outright would delete the early points of every one of those curves,
//! which is the opposite of what someone turned snapshotting on for.
//!
//! So pruning never removes a record. It removes the `.sav` and leaves the
//! sidecar, with the summary and any constellation baked into it: the
//! snapshot stops being restorable, and the data point stays forever. A
//! `.sav` is about 14 KB and a sidecar a few, so this is most of the disk
//! saving with none of the data loss.
//!
//! # The policy
//!
//! [`RetentionSettings::keep_all`] is the default and means exactly what
//! it says. At a daily snapshot that costs about 5 MB a year, which for
//! most people is the honest answer: this does not need managing.
//!
//! Turning it off hands over to a tiered rotation, the same shape as
//! `rotate-backups` and every other generational backup scheme:
//!
//! ```text
//! hourly  = 24    keep the last snapshot of each of the last 24 hours
//! daily   = 7                                          7 days
//! weekly  = 4                                          4 weeks
//! monthly = 12                                        12 months
//! yearly  = 2                                          2 years
//! ```
//!
//! A snapshot survives if *any* tier wants it, so the tiers overlap
//! rather than compete: yesterday's snapshots are held by `hourly` and
//! then, as they age out of that, by `daily`, and so on. The effect is
//! dense coverage of the recent past thinning smoothly into the distant
//! past, which is what you actually want from a rollback archive.
//!
//! Within a bucket the *newest* snapshot is the one kept, so the survivor
//! of any period is the furthest along, which is what someone restoring
//! from that period would expect.

use serde::{Deserialize, Serialize};

const MS_PER_HOUR: u64 = 60 * 60 * 1000;
const MS_PER_DAY: u64 = 24 * MS_PER_HOUR;

/// How many snapshots each tier keeps.
///
/// Zero disables a tier. All zero with `keep_all` off keeps only what the
/// floor in [`plan_pruning`] guarantees, which is the newest snapshot.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RetentionPolicy {
    pub hourly: u32,
    pub daily: u32,
    pub weekly: u32,
    pub monthly: u32,
    pub yearly: u32,
}

impl Default for RetentionPolicy {
    /// A year and a half of useful coverage in around 45 saves.
    fn default() -> Self {
        Self {
            hourly: 24,
            daily: 7,
            weekly: 4,
            monthly: 12,
            yearly: 2,
        }
    }
}

/// The retention settings as a whole.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RetentionSettings {
    /// When true nothing is ever pruned, and `policy` is ignored.
    pub keep_all: bool,
    pub policy: RetentionPolicy,
}

impl Default for RetentionSettings {
    fn default() -> Self {
        Self {
            keep_all: true,
            policy: RetentionPolicy::default(),
        }
    }
}

/// The five rotation tiers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Tier {
    Hourly,
    Daily,
    Weekly,
    Monthly,
    Yearly,
}

impl Tier {
    const ALL: [Tier; 5] = [
        Tier::Hourly,
        Tier::Daily,
        Tier::Weekly,
        Tier::Monthly,
        Tier::Yearly,
    ];

    fn count(self, policy: &RetentionPolicy) -> u32 {
        match self {
            Tier::Hourly => policy.hourly,
            Tier::Daily => policy.daily,
            Tier::Weekly => policy.weekly,
            Tier::Monthly => policy.monthly,
            Tier::Yearly => policy.yearly,
        }
    }

    /// The bucket a timestamp falls in.
    ///
    /// Any monotonic numbering works, since buckets are only ever
    /// compared and counted. Months and years go through the calendar
    /// rather than a fixed number of days, so "12 monthly" really is a
    /// year rather than 360 days that drift against it.
    fn bucket(self, ms: u64) -> i64 {
        let days = (ms / MS_PER_DAY) as i64;
        match self {
            Tier::Hourly => (ms / MS_PER_HOUR) as i64,
            Tier::Daily => days,
            // The epoch was a Thursday; +3 shifts week boundaries to
            // Monday, which is where people expect them.
            Tier::Weekly => (days + 3).div_euclid(7),
            Tier::Monthly => {
                let (year, month, _) = civil_from_days(days);
                year as i64 * 12 + month as i64
            }
            Tier::Yearly => {
                let (year, _, _) = civil_from_days(days);
                year as i64
            }
        }
    }
}

/// Converts days since 1970-01-01 into a calendar date.
///
/// Howard Hinnant's civil-from-days algorithm. Implemented here rather
/// than pulled in as a dependency: months and years are the only calendar
/// question this crate asks, and the answer is fifteen lines.
fn civil_from_days(days: i64) -> (i32, u32, u32) {
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 }.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = (if mp < 10 { mp + 3 } else { mp - 9 }) as u32;
    ((y + i64::from(m <= 2)) as i32, m, d)
}

/// One snapshot, reduced to what a retention decision needs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Candidate {
    /// Capture time, epoch milliseconds.
    pub taken_at_ms: u64,
    /// Whether it still has a restorable `.sav`. Already-pruned records
    /// are inert: they cost nothing more and cannot be pruned again.
    pub has_save: bool,
}

/// Decides which snapshots should lose their `.sav`.
///
/// Takes and returns indices into `candidates` so the caller keeps hold of
/// its own records, and so this stays a pure function that is easy to test
/// against a synthetic timeline. `candidates` may be in any order.
///
/// The newest snapshot is always kept, whatever the policy says. A
/// retention setting that leaves nothing to roll back to is a
/// misconfiguration, not an instruction.
pub fn plan_pruning(
    settings: &RetentionSettings,
    now_ms: u64,
    candidates: &[Candidate],
) -> Vec<usize> {
    if settings.keep_all {
        return Vec::new();
    }

    // Newest first. Only records that still have a save are in play.
    let mut order: Vec<usize> = (0..candidates.len())
        .filter(|i| candidates[*i].has_save)
        .collect();
    order.sort_by_key(|i| std::cmp::Reverse(candidates[*i].taken_at_ms));

    let mut keep = vec![false; candidates.len()];
    // The floor: never prune the most recent snapshot.
    if let Some(&newest) = order.first() {
        keep[newest] = true;
    }

    for tier in Tier::ALL {
        let wanted = tier.count(&settings.policy);
        if wanted == 0 {
            continue;
        }
        let now_bucket = tier.bucket(now_ms);
        let mut seen: Vec<i64> = Vec::with_capacity(wanted as usize);

        for &index in &order {
            let bucket = tier.bucket(candidates[index].taken_at_ms);
            // Buckets older than the tier's reach are none of its
            // business; a snapshot from 2019 is not what "keep 24 hourly"
            // is talking about.
            if now_bucket.saturating_sub(bucket) >= i64::from(wanted) {
                continue;
            }
            if seen.contains(&bucket) {
                // A newer snapshot already claimed this bucket, and
                // `order` is newest first, so this one is redundant here.
                continue;
            }
            seen.push(bucket);
            keep[index] = true;
        }
    }

    order.into_iter().filter(|i| !keep[*i]).collect()
}

/// What a policy would do to a set of snapshots, without doing it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RetentionPreview {
    /// Snapshots that currently have a save.
    pub restorable: usize,
    /// How many would still have one afterwards.
    pub kept: usize,
    /// How many would lose their save on the next pass.
    pub pruned: usize,
    /// Records already reduced to history. Unaffected either way.
    pub history_only: usize,
}

/// Summarizes [`plan_pruning`] for the settings UI.
///
/// Showing what a policy will actually do to the archive you have is the
/// difference between five number fields and an informed choice.
pub fn preview(
    settings: &RetentionSettings,
    now_ms: u64,
    candidates: &[Candidate],
) -> RetentionPreview {
    let restorable = candidates.iter().filter(|c| c.has_save).count();
    let pruned = plan_pruning(settings, now_ms, candidates).len();
    RetentionPreview {
        restorable,
        kept: restorable - pruned,
        pruned,
        history_only: candidates.len() - restorable,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 18:30 on a Thursday, deliberately not on an hour or day boundary.
    ///
    /// The first version of these tests used a round number that happened
    /// to land exactly on an hour boundary, which put a "burst within one
    /// hour" across two hourly buckets and made the expectations look
    /// wrong when the algorithm was right. Bucketing is boundary
    /// sensitive by nature, so the reference instant says where it sits.
    const NOW: u64 = 1_800_037_800_000;

    fn tiered(policy: RetentionPolicy) -> RetentionSettings {
        RetentionSettings {
            keep_all: false,
            policy,
        }
    }

    fn none() -> RetentionPolicy {
        RetentionPolicy {
            hourly: 0,
            daily: 0,
            weekly: 0,
            monthly: 0,
            yearly: 0,
        }
    }

    /// Snapshots every `step` back from `now`.
    fn series(now: u64, step: u64, count: usize) -> Vec<Candidate> {
        (0..count)
            .map(|i| Candidate {
                taken_at_ms: now - i as u64 * step,
                has_save: true,
            })
            .collect()
    }

    #[test]
    fn keep_all_prunes_nothing() {
        let candidates = series(NOW, MS_PER_DAY, 1000);
        assert!(plan_pruning(&RetentionSettings::default(), NOW, &candidates).is_empty());
    }

    #[test]
    fn the_default_is_to_keep_everything() {
        assert!(RetentionSettings::default().keep_all);
    }

    /// Hourly snapshots inside the hourly window are all distinct hours,
    /// so all of them survive.
    #[test]
    fn hourly_keeps_one_per_hour() {
        let candidates = series(NOW, MS_PER_HOUR, 24);
        let policy = RetentionPolicy {
            hourly: 24,
            ..none()
        };
        assert!(plan_pruning(&tiered(policy), NOW, &candidates).is_empty());
    }

    /// Several snapshots in the same hour collapse to the newest. This is
    /// what stops a play session from filling the archive.
    #[test]
    fn a_burst_within_one_hour_collapses_to_the_newest() {
        // Ten snapshots a minute apart, all inside NOW's hour.
        let candidates = series(NOW, 60_000, 10);
        let policy = RetentionPolicy {
            hourly: 24,
            ..none()
        };
        let prune = plan_pruning(&tiered(policy), NOW, &candidates);
        assert_eq!(prune.len(), 9);
        assert!(
            !prune.contains(&0),
            "the newest of the hour is the survivor"
        );
    }

    /// The point of the tiers overlapping: a month of daily snapshots
    /// keeps a day each for a week, then a week each for a month.
    #[test]
    fn tiers_overlap_into_a_thinning_curve() {
        let candidates = series(NOW, MS_PER_DAY, 60);
        let policy = RetentionPolicy {
            hourly: 24,
            daily: 7,
            weekly: 4,
            monthly: 12,
            yearly: 2,
        };
        let prune = plan_pruning(&tiered(policy), NOW, &candidates);
        let kept = candidates.len() - prune.len();

        // 7 daily + about 4 weekly + about 2 monthly, with overlap.
        assert!(kept >= 9, "kept only {kept} of 60 daily snapshots");
        assert!(kept <= 20, "kept {kept}, which is barely thinned");
    }

    /// With `hourly` off, twelve hourly snapshots inside one day are no
    /// longer twelve distinct buckets; `daily` sees one, and keeps one.
    #[test]
    fn a_tier_set_to_zero_is_switched_off() {
        // NOW is 18:30, so twelve hours back stays inside the same day.
        let candidates = series(NOW, MS_PER_HOUR, 12);

        let with_hourly = RetentionPolicy {
            hourly: 24,
            daily: 7,
            ..none()
        };
        assert!(
            plan_pruning(&tiered(with_hourly), NOW, &candidates).is_empty(),
            "with hourly on, each hour is its own bucket"
        );

        let without_hourly = RetentionPolicy { daily: 7, ..none() };
        let prune = plan_pruning(&tiered(without_hourly), NOW, &candidates);
        assert_eq!(candidates.len() - prune.len(), 1);
    }

    /// A policy of all zeroes is a misconfiguration, not an instruction to
    /// leave nothing restorable.
    #[test]
    fn the_newest_snapshot_always_survives() {
        let candidates = series(NOW, MS_PER_DAY, 10);
        let prune = plan_pruning(&tiered(none()), NOW, &candidates);
        assert_eq!(prune.len(), 9);
        assert!(!prune.contains(&0));
    }

    /// Records whose `.sav` is already gone are history-only: pruning must
    /// ignore them rather than counting them or trying to prune twice.
    #[test]
    fn already_pruned_records_are_left_alone() {
        let mut candidates = series(NOW, MS_PER_DAY, 20);
        for c in candidates.iter_mut().skip(10) {
            c.has_save = false;
        }
        let policy = RetentionPolicy { daily: 7, ..none() };
        let prune = plan_pruning(&tiered(policy), NOW, &candidates);
        assert!(prune.iter().all(|i| candidates[*i].has_save));
    }

    #[test]
    fn unordered_input_is_handled() {
        let mut candidates = series(NOW, MS_PER_HOUR, 10);
        candidates.reverse();
        let policy = RetentionPolicy {
            hourly: 24,
            ..none()
        };
        assert!(plan_pruning(&tiered(policy), NOW, &candidates).is_empty());
    }

    #[test]
    fn empty_input_is_fine() {
        assert!(plan_pruning(&RetentionSettings::default(), NOW, &[]).is_empty());
        assert!(plan_pruning(&tiered(RetentionPolicy::default()), NOW, &[]).is_empty());
    }

    /// Snapshots older than every tier's reach have nothing keeping them.
    #[test]
    fn snapshots_past_every_tier_are_pruned() {
        let ancient = NOW - 10 * 365 * MS_PER_DAY;
        let candidates = vec![
            Candidate {
                taken_at_ms: NOW,
                has_save: true,
            },
            Candidate {
                taken_at_ms: ancient,
                has_save: true,
            },
        ];
        let prune = plan_pruning(&tiered(RetentionPolicy::default()), NOW, &candidates);
        assert_eq!(prune, vec![1]);
    }

    /// Tier counts are in buckets, not elapsed time: `yearly = 2` means
    /// this calendar year and the one before it. A snapshot two calendar
    /// years back is outside that, however few days ago it was.
    #[test]
    fn yearly_counts_calendar_years_not_elapsed_days() {
        let policy = RetentionPolicy {
            yearly: 2,
            ..none()
        };
        let last_year = vec![
            Candidate {
                taken_at_ms: NOW,
                has_save: true,
            },
            Candidate {
                taken_at_ms: NOW - 200 * MS_PER_DAY,
                has_save: true,
            },
        ];
        assert!(
            plan_pruning(&tiered(policy), NOW, &last_year).is_empty(),
            "the previous calendar year is the second of two buckets"
        );

        let two_years_back = vec![
            Candidate {
                taken_at_ms: NOW,
                has_save: true,
            },
            Candidate {
                taken_at_ms: NOW - 400 * MS_PER_DAY,
                has_save: true,
            },
        ];
        assert_eq!(
            plan_pruning(&tiered(policy), NOW, &two_years_back),
            vec![1],
            "NOW is in January, so 400 days back is two calendar years"
        );
    }

    #[test]
    fn preview_counts_add_up() {
        let mut candidates = series(NOW, MS_PER_DAY, 30);
        candidates[29].has_save = false;

        let settings = tiered(RetentionPolicy::default());
        let p = preview(&settings, NOW, &candidates);
        assert_eq!(p.restorable, 29);
        assert_eq!(p.history_only, 1);
        assert_eq!(p.kept + p.pruned, p.restorable);

        let all = preview(&RetentionSettings::default(), NOW, &candidates);
        assert_eq!(all.pruned, 0);
        assert_eq!(all.kept, 29);
    }

    // --- the calendar ------------------------------------------------------

    #[test]
    fn civil_from_days_matches_known_dates() {
        assert_eq!(civil_from_days(0), (1970, 1, 1));
        assert_eq!(civil_from_days(-1), (1969, 12, 31));
        assert_eq!(civil_from_days(19_723), (2024, 1, 1));
        // A leap day, which a fixed-length month would get wrong.
        assert_eq!(civil_from_days(19_782), (2024, 2, 29));
        assert_eq!(civil_from_days(20_454), (2026, 1, 1));
    }

    /// Months are calendar months, so "12 monthly" is a year rather than
    /// 360 days drifting against one.
    #[test]
    fn monthly_buckets_follow_the_calendar() {
        let jan_31 = 20_484 * MS_PER_DAY; // 2026-01-31
        let feb_01 = 20_485 * MS_PER_DAY; // 2026-02-01
        assert_ne!(Tier::Monthly.bucket(jan_31), Tier::Monthly.bucket(feb_01));
        assert_eq!(
            Tier::Monthly.bucket(feb_01),
            Tier::Monthly.bucket(feb_01 + 27 * MS_PER_DAY)
        );
    }

    #[test]
    fn weekly_buckets_start_on_monday() {
        // 1970-01-01 was a Thursday, so days 0..3 share a week and day 4
        // (Monday the 5th) begins the next.
        assert_eq!(Tier::Weekly.bucket(0), Tier::Weekly.bucket(3 * MS_PER_DAY));
        assert_ne!(
            Tier::Weekly.bucket(3 * MS_PER_DAY),
            Tier::Weekly.bucket(4 * MS_PER_DAY)
        );
    }
}
