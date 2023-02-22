#![allow(unused)]
#![allow(incomplete_features)]
#![feature(async_fn_in_trait)]
#![feature(return_position_impl_trait_in_trait)]

use extractor::common::ExtractorOptions;
use model::error::{CrateError, Result};

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
