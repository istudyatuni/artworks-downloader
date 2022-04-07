mod cache;
mod sites;

fn main() {
    let urls = vec!["https://imgur.com"];
    sites::process_urls(urls, "save_folder".to_string());
}
