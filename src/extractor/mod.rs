use std::collections::HashMap;

use crate::{CrateError, Result};

use url::Url;

use common::{Extractor, ExtractorOptions, ExtractorSlug};

pub mod common;

mod imgur;

fn detect_site(url: &str) -> Result<ExtractorSlug> {
    let Ok(parsed) = Url::parse(url) else {
        return Err(CrateError::InvalidURL(url.to_string()))
    };
    let Some(host) = parsed.host_str() else {
        // cannot parse host from url
        return Err(CrateError::InvalidURL(url.to_string()))
    };
    let slug = match host {
        "danbooru.donmai.us" | "safebooru.donmai.us" => ExtractorSlug::Danbooru,
        "imgur.com" => ExtractorSlug::Imgur,
        "redd.it" | "www.reddit.com" => ExtractorSlug::Reddit,
        "twitter.com" | "mobile.twitter.com" | "nitter.net" => ExtractorSlug::Twitter,
        "wallhaven.cc" | "whvn.cc" => ExtractorSlug::Wallhaven,
        "www.artstation.com" => ExtractorSlug::Artstation,
        "www.deviantart.com" => ExtractorSlug::DeviantArt,
        "www.pixiv.net" | "zettai.moe" => ExtractorSlug::Pixiv,
        _ => return Err(CrateError::UnsupportedURL(url.to_string())),
    };
    Ok(slug)
}

pub async fn download_urls(urls: Vec<&str>, config: &ExtractorOptions) -> Result<()> {
    let mut map = HashMap::new();
    for u in urls {
        match detect_site(u) {
            Ok(slug) => map.entry(slug).or_insert(vec![]).push(u),
            Err(err) => eprintln!("{err}"),
        }
    }
    for (slug, urls) in map {
        match slug {
            ExtractorSlug::Imgur => imgur::ImgurExtractor::fetch_info(&urls, &config).await?,
            _ => continue,
        }
    }
    Ok(())
}
