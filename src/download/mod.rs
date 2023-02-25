use std::{
    fs::{create_dir_all, write},
    path::PathBuf,
};

use reqwest::Client;

use crate::{extractor::common::ExtractorOptions, CrateError, Result};

async fn download_binary(client: &Client, url: &str) -> Result<Vec<u8>> {
    Ok(client
        .get(url)
        .send()
        .await?
        .error_for_status()?
        .bytes()
        .await?
        .into())
}

/// Download file from `url` and save it to `path`
pub async fn download_and_save(
    client: &Client,
    config: &ExtractorOptions,
    url: &str,
    path: &PathBuf,
) -> Result<()> {
    let path = config.save_file_to(path);
    if path.exists() {
        return Err(CrateError::skip_existing(url));
    }
    if let Some(dir) = path.parent() {
        create_dir_all(dir)?;
    }
    Ok(write(path, download_binary(client, url).await?)?)
}
