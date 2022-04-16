#![allow(unused)]

use std::collections::HashMap;

use phf::phf_map;
use url::Url;

mod imgur;

static SLUGS: phf::Map<&'static str, &'static str> = phf_map! {
    "imgur.com" => "imgur",
};

fn detect_site(url: &str) -> Option<&str> {
    if let Ok(parsed) = Url::parse(url) {
        if let Some(host) = parsed.host_str() {
            return SLUGS.get(host).cloned();
        }
    }
    None
}

pub fn process_urls(urls: Vec<&str>, save_folder: &str) {
    let mut map = HashMap::new();
    for u in urls {
        match detect_site(u) {
            Some(slug) => {
                let list = map.entry(slug).or_insert(vec![]);
                (*list).push(u);
            }
            None => println!("Unsupported URL: {u}"),
        }
    }
    for (slug, urls) in map {
        download(slug, urls, save_folder)
    }
}

fn download(slug: &str, urls: Vec<&str>, save_folder: &str) {
    match slug {
        "imgur" => imgur::download(urls, save_folder),
        _ => (),
    }
}
