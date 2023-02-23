use std::{fmt::Display, path::PathBuf};

use far::Render;
use nanotemplate::template;
use reqwest::{header::AUTHORIZATION, Client};
use serde::Deserialize;
use url::Url;

use super::common::{ExtractedInfo, ExtractedItem, Extractor, ExtractorOptions, ExtractorSlug};
use crate::{CrateError, Result};

const API_ALBUM_URL: &str = "https://api.imgur.com/3/{{link_type}}/{{id}}";
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
    // is this necessary?
    // ext: Option<String>,
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

#[derive(Debug, Render)]
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
        let parsed = Url::parse(value).map_err(|s| CrateError::InvalidURL(s.to_string()))?;
        let Some(segments) = parsed.path_segments().map(|c| c.collect::<Vec<_>>()) else {
            let msg = format!("cannot get path segments from {value}");
            return Err(CrateError::Plain(msg));
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

impl Extractor for ImgurExtractor {
    async fn fetch_info(
        urls: &[&str],
        config: &ExtractorOptions,
    ) -> Result<Vec<impl ExtractedInfo>> {
        let url_template = far::find(API_ALBUM_URL).map_err(CrateError::FarError)?;
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
            let url = url_template.replace(&parsed);
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
            ImgurInfoData::Single(image) => image.into(),
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
        self.into()
    }
}

#[derive(Debug)]
struct ImgurInfoIter {
    data: ImgurInfo,
    template: String,
    at: usize,
}

impl From<ImgurInfo> for ImgurInfoIter {
    fn from(value: ImgurInfo) -> Self {
        let template = if value.images.len() == 1 {
            SAVE_SINGLE_FILE_PATTERN
        } else {
            SAVE_ALBUM_PATTERN
        }
        .to_string();
        Self {
            data: value,
            template,
            at: 0,
        }
    }
}

impl Iterator for ImgurInfoIter {
    type Item = ExtractedItem;

    fn next(&mut self) -> Option<Self::Item> {
        let Some(image) = self.data.images.get(self.at) else {
            return None;
        };

        let folder = PathBuf::from(SLUG.to_string());
        let ext = PathBuf::from(image.link.clone());
        let sub: [(&str, &str); 6] = [
            ("album_title", &self.data.title.clone().unwrap_or("".into())),
            ("album_id", &self.data.id),
            ("image_title", &image.title.clone().unwrap_or("".into())),
            ("image_id", &image.id),
            ("sep", " - "),
            ("ext", ext.extension().unwrap_or_default().to_str().unwrap_or_default()),
        ];

        self.at += 1;
        let f = template(&self.template, &sub).expect("cannot parse template");
        let f = f.replace(" -  - ", " - ");
        Some(Self::Item::new(&image.link, folder.join(f)))
    }
}
