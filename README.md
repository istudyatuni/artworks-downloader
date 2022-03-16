# Artworks downloader

- artstation.com [#info](#sites-with-simple-usage)
- deviantart.com [#info](#deviantart)
- pixiv.net [#info](#sites-with-simple-usage)
- wallhaven.cc [#info](#sites-with-simple-usage) [#notes](#wallhaven)

[Supported URL types](#supported-url-types)

## Install

Clone this repo, then from inside the project

```sh
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Usage

```
usage: python main.py [-h] [--folder FOLDER] url

Artworks downloader

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     URL to download
  -l LIST, --list LIST  File with list of URLs to download
  --folder FOLDER       Folder to save artworks. Default folder - data
  --deviantart DEVIANTART
```

### Sites with simple usage

Just run

```sh
python main.py -u [URL here]
```

### DeviantArt

You should have deviantart.com account, login to it, then

- register an application
  - go to https://www.deviantart.com/developers/apps
  - click "Register Application"
  - in field "OAuth2 Redirect URI Whitelist (Required)" under "Application Settings" block paste `http://localhost:23445`
  - scroll to bottom and check "I have read and agree to the API License Agreement."
  - click "Save"
  - in the block with newly created application click "Publish"

- save `client_id` and `client_secret` in this application
  - run

  ```sh
  python main.py --action deviantart:register
  ```

  - paste needed values

- authorize application
  - open suggested link
  - click "Authorize"

After that you can use it just like

```sh
python main.py -u [URL here]
```

## Notes

### Wallhaven

NSFW images supported only with API key, to use it, get it from [account settings](https://wallhaven.cc/settings/account), then run

```sh
python main.py --action wallhaven:key
```

## Supported URL types

- **artstation.com**
  - `https://www.artstation.com/artwork/<hash>`
  - `https://www.artstation.com/<artist>`
- **deviantart.com**
  - All deviations
    - `https://www.deviantart.com/<artist>`
    - `https://www.deviantart.com/<artist>/gallery/all`
  - "Featured" collection
    - `https://www.deviantart.com/<artist>/gallery`
  - `https://www.deviantart.com/<artist>/gallery/<some number>/<gallery name>`
  - `https://www.deviantart.com/<artist>/art/<name>`
- **pixiv.net**
  - `https://www.pixiv.net/<lang>/artworks/<id>`
- **wallhaven.cc**
  - `https://wallhaven.cc/w/<id>`
  - `https://whvn.cc/<id>`
