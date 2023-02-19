#![allow(unused)]

use model::error::{CrateError, Result};

use extractor::common::ExtractorOptions;

mod cache;
mod download;
mod extractor;
mod model;

#[tokio::main]
async fn main() -> Result<()> {
    let urls = vec!["https://imgur.com"];
    let config = ExtractorOptions::new("test");
    extractor::download_urls(urls, &config).await
}
