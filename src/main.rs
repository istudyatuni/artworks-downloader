#![allow(incomplete_features)]
#![feature(async_fn_in_trait)]
#![feature(return_position_impl_trait_in_trait)]
#![feature(type_alias_impl_trait)]

use std::{env::args, fs::read_to_string};

use extractor::common::ExtractorOptions;
pub use model::error::{CrateError, Result};

mod cache;
mod download;
mod extractor;
mod model;
mod utils;

#[tokio::main]
async fn main() -> Result<()> {
    let a: Vec<_> = args().skip(1).collect();
    if a.len() == 0 {
        return Err(CrateError::plain("please provide path to file with urls"));
    }
    let urls = read_to_string(&a[0])?;
    let urls: Vec<_> = urls.lines().map(|s| s.trim()).collect();
    let config = ExtractorOptions::new("test");
    extractor::download_urls(urls, &config).await
}
