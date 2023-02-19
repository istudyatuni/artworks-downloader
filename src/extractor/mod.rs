use std::{collections::HashMap, path::PathBuf};
use url::Url;

mod imgur;

trait Extractor {
    fn download(urls: &[&str], config: &ExtractorConfig);
}

#[derive(Debug)]
pub struct ExtractorConfig {
    save_folder: PathBuf,
}

impl ExtractorConfig {
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

fn detect_site(url: &str) -> Option<&str> {
    let Ok(parsed) = Url::parse(url) else {
        println!("invalid url: {url}");
        return None;
    };
    if let Some(host) = parsed.host_str() {
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
                println!("unsupported url: {url}");
                return None;
            }
        };
        return Some(slug);
    }
    None
}

pub fn download_urls(urls: Vec<&str>, config: &ExtractorConfig) {
    let mut map = HashMap::new();
    for u in urls {
        if let Some(slug) = detect_site(u) {
            map.entry(slug).or_insert(vec![]).push(u);
        }
    }
    for (slug, urls) in map {
        match slug {
            "imgur" => imgur::ImgurExtractor::download(&urls, &config),
            _ => (),
        }
    }
}
