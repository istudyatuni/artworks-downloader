// use crate::cache;

use super::{Extractor, ExtractorConfig};

// just from devtools
const API_ALBUM_URL: &str =
    "https://api.imgur.com/post/v1/albums/{id}?client_id=546c25a59c58ad7&include=media";
const SLUG: &str = "imgur";

#[derive(Debug)]
pub struct ImgurExtractor {
    // urls: Vec<String>,
}

/*impl ImgurExtractor {
    pub fn new() -> Self {
        Self {
            // urls: todo!(),
        }
    }
}*/

impl Extractor for ImgurExtractor {
    fn download(urls: &[&str], config: &ExtractorConfig) {
        println!("urls: {urls:#?}")
    }
}
