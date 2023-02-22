use std::fmt::Display;

use far::Render;
use reqwest::{header::AUTHORIZATION, Client};
use serde::Deserialize;
use url::Url;

use crate::{CrateError, Result};
use super::common::{ExtractedInfo, Extractor, ExtractorOptions};

const API_ALBUM_URL: &str = "https://api.imgur.com/3/{{link_type}}/{{id}}";
// just from devtools
const AUTHORIZATION_KEY: &str = "Client-ID 546c25a59c58ad7";

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
    ext: Option<String>,
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
        let api_url_template = far::find(API_ALBUM_URL).map_err(CrateError::FarError)?;
        let client = Client::new();

        let mut extracted = vec![];
        for &url in urls {
            let parsed = match Parsed::try_from(url) {
                Ok(p) => p,
                Err(e) => {
                    eprintln!("cannot parse url: {e}");
                    continue;
                },
            };
            let url = api_url_template.replace(&parsed);
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
