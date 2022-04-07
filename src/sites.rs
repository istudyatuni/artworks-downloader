#![allow(unused)]

use phf::phf_map;
use url::Url;

pub mod imgur;

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

pub fn process_urls(urls: Vec<&str>, save_folder: String) {
    for u in urls {
        match detect_site(u) {
            Some(slug) => println!("{}", slug),
            None => println!("Unsupported URL: {u}"),
        }
    }
}

fn download(slug: String, urls: Vec<String>, save_folder: String) {
    match slug.as_str() {
        "imgur" => imgur::download(urls, save_folder),
        _ => (),
    }
}
