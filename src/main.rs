#![allow(unused)]

use extractor::ExtractorConfig;

mod cache;
mod extractor;

#[tokio::main]
async fn main() {
    let urls = vec!["https://imgur.com"];
    let config = ExtractorConfig::new("test");
    extractor::download_urls(urls, &config);
}
