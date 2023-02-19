use std::{collections::HashMap, path::PathBuf};

use anyhow::{bail, Result};
use async_trait::async_trait;
use url::Url;

mod imgur;

#[async_trait]
trait Extractor {
    async fn download(urls: &[&str], config: &ExtractorOptions) -> Result<()>;
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
    fn save_file_with(&self, filepath: PathBuf) -> PathBuf {
        self.save_folder.join(filepath)
    }
}

fn detect_site(url: &str) -> Result<&str> {
    let Ok(parsed) = Url::parse(url) else {
        bail!("invalid url: {url}");
    };
    let Some(host) = parsed.host_str() else {
        bail!("cannot parse host from url: {url}");
    };
    let slug = match host {
        "danbooru.donmai.us" => "danbooru",
        "imgur.com" => "imgur",
        "mobile.twitter.com" => "twitter",
        "nitter.net" => "twitter",
        "redd.it" => "reddit",
        "safebooru.donmai.us" => "danbooru",
        "twitter.com" => "twitter",
        "wallhaven.cc" => "wallhaven",
        "whvn.cc" => "wallhaven",
        "www.artstation.com" => "artstation",
        "www.deviantart.com" => "deviantart",
        "www.pixiv.net" => "pixiv",
        "www.reddit.com" => "reddit",
        "zettai.moe" => "pixiv",
        _ => {
            bail!("unsupported url: {url}");
        }
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
            "imgur" => imgur::ImgurExtractor::download(&urls, &config).await?,
            _ => continue,
        }
    }
    Ok(())
}
