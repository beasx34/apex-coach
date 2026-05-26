//! Google Gemini client — uses the `generateContent` REST endpoint of the
//! Google AI Studio API directly (no SDK). The free tier requires only an API
//! key obtained at https://aistudio.google.com/app/apikey.

use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};

use crate::game_state::GameContext;
use crate::tracker::Profile;

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub enum Priority {
    Low,
    #[default]
    Med,
    High,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub enum Category {
    Combat,
    #[default]
    Positioning,
    Loot,
    Rotation,
    Ult,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CoachAdvice {
    pub tip: String,
    pub priority: Priority,
    pub category: Category,
    pub at_ms: u64,
}

pub struct GeminiClient {
    http: reqwest::Client,
    api_key: String,
    model: String,
    language: String,
}

impl GeminiClient {
    pub fn new(api_key: String, model: String, language: String) -> Self {
        let http = reqwest::Client::builder()
            .user_agent(concat!("apex-coach/", env!("CARGO_PKG_VERSION")))
            .timeout(std::time::Duration::from_secs(20))
            .build()
            .expect("reqwest client");
        Self {
            http,
            api_key,
            model,
            language,
        }
    }

    /// Cheap ping that asks Gemini to echo "ok".
    pub async fn ping(&self) -> Result<String> {
        let payload = serde_json::json!({
            "contents": [{
                "parts": [{ "text": "Reply with the single word: ok" }]
            }],
            "generationConfig": { "temperature": 0.0, "maxOutputTokens": 8 }
        });
        let v = self.post(payload).await?;
        Ok(extract_text(&v).unwrap_or_else(|| "ok".to_string()))
    }

    /// Build a tight prompt and ask Gemini for a single tactical tip.
    pub async fn coach(&self, ctx: &GameContext, profile: Option<&Profile>) -> Result<CoachAdvice> {
        let lang = match self.language.as_str() {
            "en" => "English",
            _ => "Russian",
        };
        let system = format!(
            "You are an Apex Legends coach. Respond with ONE short actionable tactical tip in {lang}. \
            Strict format: respond ONLY with JSON matching {{\"tip\":string,\"priority\":\"Low\"|\"Med\"|\"High\",\"category\":\"Combat\"|\"Positioning\"|\"Loot\"|\"Rotation\"|\"Ult\"}}. \
            The tip must be <= 18 words. Do not include markdown code fences.",
        );
        let user = serde_json::json!({
            "game_context": ctx,
            "profile_summary": profile.map(|p| serde_json::json!({
                "display_name": p.display_name,
                "level": p.level,
                "rank": p.br_rank.division,
                "rank_score": p.br_rank.score,
                "selected_legend": p.selected_legend,
            })),
        });
        let payload = serde_json::json!({
            "systemInstruction": { "parts": [{ "text": system }] },
            "contents": [{
                "parts": [{ "text": user.to_string() }]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 200,
                "responseMimeType": "application/json",
            }
        });
        let v = self.post(payload).await?;
        let text = extract_text(&v).ok_or_else(|| anyhow!("gemini returned no text: {v}"))?;
        let mut advice: CoachAdvice =
            serde_json::from_str(&text).with_context(|| format!("parse gemini json: {text}"))?;
        advice.at_ms = now_ms();
        Ok(advice)
    }

    async fn post(&self, body: serde_json::Value) -> Result<serde_json::Value> {
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.model, self.api_key
        );
        let resp = self
            .http
            .post(&url)
            .json(&body)
            .send()
            .await
            .context("gemini POST")?;
        let status = resp.status();
        let raw = resp.text().await.unwrap_or_default();
        if !status.is_success() {
            return Err(anyhow!(
                "gemini request failed (HTTP {}): {}",
                status,
                raw.chars().take(300).collect::<String>()
            ));
        }
        serde_json::from_str(&raw).context("parse gemini response")
    }
}

fn extract_text(v: &serde_json::Value) -> Option<String> {
    v.get("candidates")?
        .as_array()?
        .first()?
        .get("content")?
        .get("parts")?
        .as_array()?
        .iter()
        .filter_map(|p| p.get("text").and_then(|t| t.as_str()))
        .collect::<Vec<_>>()
        .join(" ")
        .into()
}

fn now_ms() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}
