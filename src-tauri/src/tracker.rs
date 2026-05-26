//! Apex tracker API client.
//!
//! By default we target the Mozambiquehe.re (apexlegendsapi.com) endpoint
//! because it offers a free tier with a single API key. Tracker.gg is supported
//! as an alternative (the user provides a key and selects the provider in
//! Settings).

use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};

use crate::config::{Platform, TrackerProvider};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RankInfo {
    pub division: String,
    pub score: u32,
    #[serde(default)]
    pub percentile: Option<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LegendStats {
    pub name: String,
    pub kills: u32,
    pub damage: u64,
    pub wins: u32,
    pub matches: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatchRow {
    pub legend: String,
    pub kills: u32,
    pub damage: u32,
    pub placement: u32,
    pub time_ms: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Profile {
    pub platform: Platform,
    pub display_name: String,
    pub level: u32,
    pub br_rank: RankInfo,
    pub legends: Vec<LegendStats>,
    pub selected_legend: Option<String>,
}

pub struct TrackerClient {
    http: reqwest::Client,
    api_key: String,
    provider: TrackerProvider,
}

impl TrackerClient {
    pub fn new(api_key: String, provider: TrackerProvider) -> Self {
        let http = reqwest::Client::builder()
            .user_agent(concat!("apex-coach/", env!("CARGO_PKG_VERSION")))
            .timeout(std::time::Duration::from_secs(15))
            .build()
            .expect("reqwest client");
        Self {
            http,
            api_key,
            provider,
        }
    }

    pub async fn fetch_profile(&self, platform: Platform, name: &str) -> Result<Profile> {
        match self.provider {
            TrackerProvider::Mozambique => self.mozambique_profile(platform, name).await,
            TrackerProvider::TrackerGg => self.tracker_gg_profile(platform, name).await,
        }
    }

    pub async fn fetch_match_history(
        &self,
        platform: Platform,
        name: &str,
    ) -> Result<Vec<MatchRow>> {
        match self.provider {
            TrackerProvider::Mozambique => self.mozambique_matches(platform, name).await,
            TrackerProvider::TrackerGg => self.tracker_gg_matches(platform, name).await,
        }
    }

    async fn mozambique_profile(&self, platform: Platform, name: &str) -> Result<Profile> {
        // GET https://api.mozambiquehe.re/bridge?auth=...&player=...&platform=...
        let url = "https://api.mozambiquehe.re/bridge";
        let resp = self
            .http
            .get(url)
            .query(&[
                ("auth", self.api_key.as_str()),
                ("player", name),
                ("platform", platform.as_provider_str()),
            ])
            .send()
            .await
            .context("mozambique GET /bridge")?;
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        if !status.is_success() {
            return Err(anyhow!(
                "tracker request failed (HTTP {}): {}",
                status,
                body.chars().take(200).collect::<String>()
            ));
        }
        let v: serde_json::Value = serde_json::from_str(&body).context("parse mozambique json")?;
        if let Some(err) = v.get("Error").and_then(|e| e.as_str()) {
            return Err(anyhow!("tracker error: {err}"));
        }
        Ok(map_mozambique_profile(&v, platform))
    }

    async fn mozambique_matches(&self, _platform: Platform, _name: &str) -> Result<Vec<MatchRow>> {
        // Mozambiquehe.re exposes per-player session history only to paid plans.
        // For the free tier we return an empty list and let the UI surface the
        // limitation — see README.
        Ok(Vec::new())
    }

    async fn tracker_gg_profile(&self, platform: Platform, name: &str) -> Result<Profile> {
        // https://public-api.tracker.gg/v2/apex/standard/profile/{platform}/{name}
        let segment = match platform {
            Platform::Origin => "origin",
            Platform::Xbl => "xbl",
            Platform::Psn => "psn",
            Platform::Switch => "switch",
        };
        let url = format!(
            "https://public-api.tracker.gg/v2/apex/standard/profile/{segment}/{}",
            urlencoding::encode(name)
        );
        let resp = self
            .http
            .get(&url)
            .header("TRN-Api-Key", &self.api_key)
            .send()
            .await
            .context("tracker.gg GET profile")?;
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        if !status.is_success() {
            return Err(anyhow!(
                "tracker.gg request failed (HTTP {}): {}",
                status,
                body.chars().take(200).collect::<String>()
            ));
        }
        let v: serde_json::Value = serde_json::from_str(&body).context("parse tracker.gg json")?;
        Ok(map_tracker_gg_profile(&v, platform))
    }

    async fn tracker_gg_matches(&self, _platform: Platform, _name: &str) -> Result<Vec<MatchRow>> {
        // tracker.gg sessions endpoint is gated behind a paid tier; same fallback.
        Ok(Vec::new())
    }
}

fn map_mozambique_profile(v: &serde_json::Value, platform: Platform) -> Profile {
    let global = v.get("global").cloned().unwrap_or_default();
    let level = global.get("level").and_then(|x| x.as_u64()).unwrap_or(0) as u32;
    let display_name = global
        .get("name")
        .and_then(|x| x.as_str())
        .unwrap_or_default()
        .to_string();
    let br = global.get("rank").cloned().unwrap_or_default();
    let rank = RankInfo {
        division: br
            .get("rankName")
            .and_then(|x| x.as_str())
            .unwrap_or("Unranked")
            .to_string(),
        score: br.get("rankScore").and_then(|x| x.as_u64()).unwrap_or(0) as u32,
        percentile: None,
    };
    let selected_legend = v
        .get("legends")
        .and_then(|l| l.get("selected"))
        .and_then(|l| l.get("LegendName"))
        .and_then(|x| x.as_str())
        .map(|s| s.to_string());

    let legends = v
        .get("legends")
        .and_then(|l| l.get("all"))
        .and_then(|l| l.as_object())
        .map(|map| {
            map.iter()
                .map(|(name, body)| {
                    let trackers = body
                        .get("data")
                        .and_then(|d| d.as_array())
                        .cloned()
                        .unwrap_or_default();
                    let mut kills = 0u32;
                    let mut damage = 0u64;
                    let mut wins = 0u32;
                    let mut matches = 0u32;
                    for t in trackers {
                        let key = t.get("key").and_then(|x| x.as_str()).unwrap_or("");
                        let val = t.get("value").and_then(|x| x.as_u64()).unwrap_or(0);
                        match key {
                            "kills" | "specialEvent_kills" => kills += val as u32,
                            "damage" | "specialEvent_damage" => damage += val,
                            "wins" | "specialEvent_wins" => wins += val as u32,
                            "games_played" => matches = val as u32,
                            _ => {}
                        }
                    }
                    LegendStats {
                        name: name.clone(),
                        kills,
                        damage,
                        wins,
                        matches,
                    }
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    Profile {
        platform,
        display_name,
        level,
        br_rank: rank,
        legends,
        selected_legend,
    }
}

fn map_tracker_gg_profile(v: &serde_json::Value, platform: Platform) -> Profile {
    let data = v.get("data").cloned().unwrap_or_default();
    let user_info = data.get("platformInfo").cloned().unwrap_or_default();
    let display_name = user_info
        .get("platformUserHandle")
        .and_then(|x| x.as_str())
        .unwrap_or_default()
        .to_string();

    let segments = data
        .get("segments")
        .and_then(|x| x.as_array())
        .cloned()
        .unwrap_or_default();

    let mut level = 0u32;
    let mut rank = RankInfo {
        division: "Unranked".into(),
        score: 0,
        percentile: None,
    };
    let mut legends: Vec<LegendStats> = Vec::new();

    for seg in segments {
        let seg_type = seg.get("type").and_then(|x| x.as_str()).unwrap_or_default();
        let stats = seg.get("stats").cloned().unwrap_or_default();
        match seg_type {
            "overview" => {
                level = stats
                    .get("level")
                    .and_then(|x| x.get("value"))
                    .and_then(|x| x.as_u64())
                    .unwrap_or(0) as u32;
                if let Some(rank_seg) = stats.get("rankScore") {
                    rank.score = rank_seg.get("value").and_then(|x| x.as_u64()).unwrap_or(0) as u32;
                    rank.division = rank_seg
                        .get("metadata")
                        .and_then(|m| m.get("rankName"))
                        .and_then(|x| x.as_str())
                        .unwrap_or("Unranked")
                        .to_string();
                    rank.percentile = rank_seg
                        .get("percentile")
                        .and_then(|x| x.as_f64())
                        .map(|f| f as f32);
                }
            }
            "legend" => {
                let name = seg
                    .get("metadata")
                    .and_then(|m| m.get("name"))
                    .and_then(|x| x.as_str())
                    .unwrap_or_default()
                    .to_string();
                let kills = stats
                    .get("kills")
                    .and_then(|x| x.get("value"))
                    .and_then(|x| x.as_u64())
                    .unwrap_or(0) as u32;
                let damage = stats
                    .get("damage")
                    .and_then(|x| x.get("value"))
                    .and_then(|x| x.as_u64())
                    .unwrap_or(0);
                let wins = stats
                    .get("wins")
                    .and_then(|x| x.get("value"))
                    .and_then(|x| x.as_u64())
                    .unwrap_or(0) as u32;
                let matches = stats
                    .get("games_played")
                    .and_then(|x| x.get("value"))
                    .and_then(|x| x.as_u64())
                    .unwrap_or(0) as u32;
                legends.push(LegendStats {
                    name,
                    kills,
                    damage,
                    wins,
                    matches,
                });
            }
            _ => {}
        }
    }

    Profile {
        platform,
        display_name,
        level,
        br_rank: rank,
        legends,
        selected_legend: None,
    }
}

mod urlencoding {
    pub fn encode(s: &str) -> String {
        let mut out = String::with_capacity(s.len());
        for c in s.chars() {
            match c {
                'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' | '.' | '~' => out.push(c),
                _ => {
                    for b in c.to_string().as_bytes() {
                        out.push_str(&format!("%{:02X}", b));
                    }
                }
            }
        }
        out
    }
}
