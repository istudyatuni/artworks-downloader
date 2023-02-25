use std::{fmt::Display, path::PathBuf};

use crate::Result;

/// Slugs for extractor
#[derive(Debug, PartialEq, Eq, Hash)]
pub enum ExtractorSlug {
    Artstation,
    Danbooru,
    DeviantArt,
    Imgur,
    Pixiv,
    Reddit,
    Twitter,
    Wallhaven,
}

impl Display for ExtractorSlug {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            ExtractorSlug::Artstation => "artstation",
            ExtractorSlug::Danbooru => "danbooru",
            ExtractorSlug::DeviantArt => "deviantart",
            ExtractorSlug::Imgur => "imgur",
            ExtractorSlug::Pixiv => "pixiv",
            ExtractorSlug::Reddit => "reddit",
            ExtractorSlug::Twitter => "twitter",
            ExtractorSlug::Wallhaven => "wallhaven",
        };
        write!(f, "{s}")
    }
}

pub trait Extractor {
    async fn fetch_info(
        urls: &[&str],
        config: &ExtractorOptions,
    ) -> Result<Vec<impl ExtractedInfo>>;
}

#[derive(Debug)]
pub struct ExtractorOptions {
    /// Root folder for saving
    root_save_folder: PathBuf,
}

impl ExtractorOptions {
    pub fn new(save_folder: &str) -> Self {
        Self {
            root_save_folder: PathBuf::from(save_folder),
        }
    }
    /// Get `root_save_folder` with appended `filepath`
    pub fn save_file_to(&self, filepath: &PathBuf) -> PathBuf {
        self.root_save_folder.join(filepath)
    }
}

#[derive(Debug)]
pub struct ExtractedItem {
    pub link: String,
    pub save_path: PathBuf,
}

impl ExtractedItem {
    pub fn new(link: &str, save_path: PathBuf) -> Self {
        let link = link.into();
        Self { link, save_path }
    }
}

/// This marker trait indicates that an object with extracted
/// information can provide information about extracted info
///
/// This also enforces to implement an iterator
///
/// To do this [`IntoIterator`] (and maybe [`Iterator`]) should be implemented
pub trait ExtractedInfo: IntoIterator<Item = ExtractedItem> {}
