#![allow(unused)]

use anyhow::Result;
// use model::error::Result;

use extractor::ExtractorOptions;

mod cache;
mod extractor;
mod model;

#[tokio::main]
async fn main() -> Result<()> {
    let urls = vec!["https://imgur.com"];
    let config = ExtractorOptions::new("test");
    extractor::download_urls(urls, &config).await
}
