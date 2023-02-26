use std::path::PathBuf;

use crate::Result;

pub trait SepCleaner {
    fn try_clear_separator(&self, sep: &str) -> Result<Self>
    where
        Self: Sized;
}

impl SepCleaner for PathBuf {
    /// Remove extra separator from each path component
    fn try_clear_separator(&self, sep: &str) -> Result<Self> {
        let Some(s) = self.to_str() else {
            return Err(crate::CrateError::plain("cannot convert to utf-8 string"))
        };
        // "{sep}{sep}" -> "{sep}"
        let s = s.replace(&(sep.to_owned() + sep), sep);
        Ok(s.split('/')
            .map(|s| s.strip_prefix(sep).unwrap_or(s))
            .map(|s| s.strip_suffix(sep).unwrap_or(s))
            .collect::<Vec<_>>()
            .join("/")
            .into())
    }
}
