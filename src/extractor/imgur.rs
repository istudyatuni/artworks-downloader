use std::{fmt::Display, path::PathBuf};

use reqwest::{header::AUTHORIZATION, Client};
use serde::Deserialize;
use url::Url;

use super::common::{ExtractedInfo, ExtractedItem, Extractor, ExtractorOptions, ExtractorSlug};
use crate::utils::template::Template;
use crate::{CrateError, Result};

const API_ALBUM_URL: &str = "https://api.imgur.com/3/{type}/{id}";
// just from devtools
const AUTHORIZATION_KEY: &str = "Client-ID 546c25a59c58ad7";

const SLUG: ExtractorSlug = ExtractorSlug::Imgur;
const SAVE_SINGLE_FILE_PATTERN: &str =
    "{album_title}{sep}{album_id}{sep}{image_title}{sep}{image_id}.{ext}";
const SAVE_ALBUM_PATTERN: &str = "{album_title}{sep}{album_id}/{image_title}{sep}{image_id}.{ext}";

#[derive(Debug)]
pub struct ImgurExtractor {}

#[derive(Debug, Deserialize)]
struct ImgurInfoWrapper {
    data: ImgurInfoData,
}

#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum ImgurInfoData {
    Multiple(ImgurInfo),
    Single(ImgurInfoImage),
}

#[derive(Debug, Default, Deserialize)]
struct ImgurInfo {
    id: String,
    title: Option<String>,
    images: Vec<ImgurInfoImage>,
}

#[derive(Debug, Deserialize)]
struct ImgurInfoImage {
    id: String,
    link: String,
    #[serde(rename(deserialize = "type"))]
    content_type: String,
    title: Option<String>,
}

impl From<ImgurInfoImage> for ImgurInfo {
    /// Put single image to array, because it the same model
    fn from(value: ImgurInfoImage) -> Self {
        Self {
            id: value.id.clone(),
            title: value.title.clone(),
            images: vec![value],
        }
    }
}

#[derive(Debug)]
enum LinkType {
    Album,
    Image,
}

impl Display for LinkType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match &self {
            Self::Album => "album",
            Self::Image => "image",
        };
        write!(f, "{s}")
    }
}

#[derive(Debug)]
struct Parsed {
    id: String,
    link_type: LinkType,
}

impl Parsed {
    fn new(id: &str, link_type: LinkType) -> Self {
        let id = id.into();
        Self { id, link_type }
    }
}

impl TryFrom<&str> for Parsed {
    type Error = CrateError;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        let parsed = Url::parse(value).map_err(|s| CrateError::invalid_url(s.to_string()))?;
        let Some(segments) = parsed.path_segments().map(|c| c.collect::<Vec<_>>()) else {
            let msg = format!("cannot get path segments from {value}");
            return Err(CrateError::plain(msg));
        };

        match segments.as_slice() {
            ["" | "a" | "gallery" | "t"] | ["t", _] => Err(CrateError::invalid_url(value)),

            // https://imgur.com/<id>
            [id] => Ok(Parsed::new(id, LinkType::Image)),

            // https://imgur.com/a/<id>
            // https://imgur.com/gallery/<id>
            // https://imgur.com/t/<tag>/<id>
            ["a" | "gallery", id] | ["t", _, id] => Ok(Parsed::new(id, LinkType::Album)),

            _ => Err(CrateError::unsupported_url(value)),
        }
    }
}

impl Extractor for ImgurExtractor {
    async fn fetch_info(
        urls: &[&str],
        config: &ExtractorOptions,
    ) -> Result<Vec<impl ExtractedInfo>> {
        let url_template = Template::try_from(API_ALBUM_URL)?;
        let client = Client::new();

        let mut extracted = vec![];
        for &url in urls {
            let parsed = match Parsed::try_from(url) {
                Ok(p) => p,
                Err(e) => {
                    eprintln!("cannot parse url: {e}");
                    continue;
                }
            };
            let sub = [("id", parsed.id), ("type", parsed.link_type.to_string())];
            let url = url_template.render(sub)?;
            match Self::fetch_info_inner(&client, &url).await {
                Ok(info) => extracted.push(info),
                Err(e) => eprintln!("cannot fetch info: {e}"),
            }
        }
        Ok(extracted)
    }
}

impl ImgurExtractor {
    async fn fetch_info_inner(client: &Client, url: &str) -> Result<ImgurInfo> {
        let res = client
            .get(url)
            .header(AUTHORIZATION, AUTHORIZATION_KEY)
            .send()
            .await
            .map_err(CrateError::ReqwestError)?;
        let res: ImgurInfoWrapper = res.json().await.map_err(CrateError::ReqwestError)?;
        let data = match res.data {
            ImgurInfoData::Single(image) => ImgurInfo::from(image),
            ImgurInfoData::Multiple(info) => info,
        };
        Ok(data)
    }
}

impl ExtractedInfo for ImgurInfo {}

impl IntoIterator for ImgurInfo {
    type Item = ExtractedItem;
    type IntoIter = ImgurInfoIter;

    fn into_iter(self) -> Self::IntoIter {
        let template = if self.images.len() == 1 {
            SAVE_SINGLE_FILE_PATTERN
        } else {
            SAVE_ALBUM_PATTERN
        };
        let template = Template::try_from(template).unwrap();
        Self::IntoIter {
            data: self,
            template,
            at: 0,
        }
    }
}

#[derive(Debug)]
struct ImgurInfoIter {
    data: ImgurInfo,
    template: Template,
    at: usize,
}

impl Iterator for ImgurInfoIter {
    type Item = ExtractedItem;

    fn next(&mut self) -> Option<Self::Item> {
        let Some(image) = self.data.images.get(self.at) else {
            return None;
        };

        let folder = PathBuf::from(SLUG.to_string());
        let ext = image.content_type.split('/').last().unwrap_or_default();
        let sub: [(&str, &str); 6] = [
            ("album_title", &self.data.title.clone().unwrap_or("".into())),
            ("album_id", &self.data.id),
            ("image_title", &image.title.clone().unwrap_or("".into())),
            ("image_id", &image.id),
            ("sep", " - "),
            ("ext", ext),
        ];

        self.at += 1;
        let f = self.template.render(sub).unwrap();
        let f = f.replace(" -  - ", " - ");
        Some(Self::Item::new(&image.link, folder.join(f)))
    }
}
