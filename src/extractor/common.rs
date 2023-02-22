use std::path::PathBuf;

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

/*impl ExtractorSlug {
    pub fn get_extractor(&self) -> impl Extractor {
        match self {
            ExtractorSlug::Artstation => todo!(),
            ExtractorSlug::Danbooru => todo!(),
            ExtractorSlug::DeviantArt => todo!(),
            ExtractorSlug::Imgur => ImgurExtractor{},
            ExtractorSlug::Pixiv => todo!(),
            ExtractorSlug::Reddit => todo!(),
            ExtractorSlug::Twitter => todo!(),
            ExtractorSlug::Wallhaven => todo!(),
        }
    }
}*/

pub trait Extractor {
    async fn fetch_info(urls: &[&str], config: &ExtractorOptions) -> Result<Vec<impl ExtractedInfo>>;
}

#[derive(Debug)]
pub struct ExtractorOptions {
    /// Root folder for saving
    save_folder: PathBuf,
}

impl ExtractorOptions {
    pub fn new(save_folder: &str) -> Self {
        Self {
            save_folder: PathBuf::from(save_folder),
        }
    }
    /// Get `save_folder` with appended `filepath`
    fn save_file_to(&self, filepath: PathBuf) -> PathBuf {
        self.save_folder.join(filepath)
    }
}

pub trait ExtractedInfo {}
