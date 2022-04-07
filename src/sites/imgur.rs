#![allow(unused)]

use crate::cache;

// just from devtools
const API_ALBUM_URL: &str =
    "https://api.imgur.com/post/v1/albums/{id}?client_id=546c25a59c58ad7&include=media";
const SLUG: &str = "imgur";

pub fn download(urls: Vec<String>, save_folder: String) {}
