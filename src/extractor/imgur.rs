use crate::{CrateError, Result};
use async_trait::async_trait;
use far::Render;
use url::Url;

use super::common::{Extractor, ExtractorOptions};

// just from devtools
const API_ALBUM_URL: &str =
    "https://api.imgur.com/post/v1/albums/{{id}}?client_id=546c25a59c58ad7&include=media";

#[derive(Debug)]
pub struct ImgurExtractor {}

#[derive(Debug)]
struct ImgurInfo {
    id: String,
    title: String,
    images: Vec<ImgurInfoImages>,
}

#[derive(Debug)]
struct ImgurInfoImages {
    id: String,
    link: String,
    ext: String,
    title: String,
}

#[derive(Debug, Render)]
struct ApiURLReplacements {
    id: String,
}

#[derive(Debug)]
enum LinkType {
    Album,
    Image,
}

#[derive(Debug)]
struct Parsed {
    id: String,
    link_type: LinkType,
}

impl Parsed {
    fn new(id: &str, link_type: LinkType) -> Self {
        let id = id.to_string();
        Self { id, link_type }
    }
}

impl TryFrom<&str> for Parsed {
    type Error = CrateError;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        let Ok(parsed) = Url::parse(value) else {
            println!("invalid url: {value}");
            return Err(CrateError::InvalidURL(value.to_string()));
        };

        let Some(segments) = parsed.path_segments().map(|c| c.collect::<Vec<_>>()) else {
            return Err(CrateError::Plain("cannot get path segments".to_string()));
        };

        match segments.as_slice() {
            // https://imgur.com/<id>
            [id] => Ok(Parsed::new(id, LinkType::Image)),

            // https://imgur.com/a/<id>
            // https://imgur.com/gallery/<id>
            // https://imgur.com/t/<tag>/<id>
            ["a", id] | ["gallery", id] | ["t", _, id] => Ok(Parsed::new(id, LinkType::Album)),

            _ => Err(CrateError::UnsupportedURL(value.to_string())),
        }
    }
}

#[async_trait]
impl Extractor for ImgurExtractor {
    async fn fetch_info(urls: &[&str], config: &ExtractorOptions) -> Result<()> {
        let api_url_template = far::find(API_ALBUM_URL).map_err(CrateError::FarError)?;
        for &url in urls {
            let Ok(parsed) = Parsed::try_from(url) else {
                continue;
            };
            println!(
                "{}",
                api_url_template.replace(&ApiURLReplacements { id: parsed.id })
            );
        }
        Ok(())
    }
}
