//! Secure secret storage. On Windows this is backed by Windows Credential Manager
//! via the `keyring` crate; on other platforms it falls back to the OS-native
//! keyring (Keychain on macOS, libsecret on Linux). We expose a tiny key/value
//! interface so the rest of the codebase doesn't depend on keyring directly.

use anyhow::{Context, Result};
use keyring::Entry;

pub const TRACKER_KEY: &str = "tracker_api_key";
pub const GEMINI_KEY: &str = "gemini_api_key";

const SERVICE: &str = "ai.apexcoach.app";

fn entry(name: &str) -> Result<Entry> {
    Entry::new(SERVICE, name).context("opening keyring entry")
}

pub fn put(name: &str, value: &str) -> Result<()> {
    entry(name)?.set_password(value).context("setting secret")
}

pub fn get(name: &str) -> Result<String> {
    entry(name)?.get_password().context("reading secret")
}

pub fn delete(name: &str) -> Result<()> {
    entry(name)?.delete_credential().context("deleting secret")
}

pub fn has(name: &str) -> bool {
    matches!(entry(name).and_then(|e| e.get_password().context("read")), Ok(s) if !s.is_empty())
}

/// Validate that a secret name is one of the well-known keys to avoid using
/// keyring as an arbitrary store.
pub fn is_known(name: &str) -> bool {
    matches!(name, TRACKER_KEY | GEMINI_KEY)
}
