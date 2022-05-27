# Artworks downloader

## Supported sites

- artstation.com [#usage](#sites-with-simple-usage)
- deviantart.com [#usage](#deviantart)
- imgur.com [#usage](#sites-with-simple-usage)
- pixiv.net [#usage](#sites-with-simple-usage) [#notes](#pixiv)
  - zettai.moe
- reddit.com [#usage](#sites-with-simple-usage)
- twitter.com [#usage](#sites-with-simple-usage) [#notes](#twitter)
- wallhaven.cc [#usage](#sites-with-simple-usage) [#notes](#wallhaven)

[Supported URL types](#supported-url-types)

## Install

### With `pip`

```sh
pip install -U art-dl
```

Then run as `art-dl`: [#usage](#usage)

### Build from source

You need poetry, [install](https://python-poetry.org/docs/#installation) it, then run from inside the project

```sh
poetry install --no-dev

# run with poetry
poetry run python -m art_dl

# enter venv created with poetry
poetry shell
# run inside it as
python -m art_dl
# or
art-dl

# create and activate venv, e.g. with virtualenvwrapper, then
poetry install --no-dev
art-dl
```

Alternatively, build binary with [nuitka](https://github.com/Nuitka/Nuitka):

```sh
poetry install
poetry shell
python -m nuitka art_dl
```

After that you will have binary in the root directory.

## Usage

```
usage: art-dl [-h] [-u URL] [-l LIST] [--folder FOLDER] [--action ACTION] [-q] [-v] [--version]

Artworks downloader

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     URL to download
  -l LIST, --list LIST  File with list of URLs to download, one URL per line
  --folder FOLDER       Folder to save artworks. Default folder - data
  --action ACTION
  -q, --quiet           Do not show logs
  -v, --verbose         Show more logs
  --version             Show version
```

### Sites with simple usage

Just run

```sh
# download single url
art-dl -u [URL]
# download urls from file with list of urls, one url per line
art-dl -l [file with list of urls]
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
  art-dl --action deviantart:register
  ```

  - paste needed values

- authorize application
  - open suggested link
  - click "Authorize"

After that you can use it as other sites: [#usage](#sites-with-simple-usage)

### Proxy

Create `config.json` file with this content and fill "proxy":

```json
{
  "proxy": "proxy-url"
}
```

For example, `socks5://localhost:1080`

## Notes

### Pixiv

If the artwork has more one image, you can specify which images should be downloaded, for example, if the artwork has 10 images and you want to download 1, 3, 4, 5 and 7 image, you can add `#1,3-5,7` to the link for that: `https://www.pixiv.net/<lang>/artworks/<id>#1,3-5,7`.

### Twitter

Here we use an alternative frontend for Twitter: https://nitter.net ([Github](https://github.com/zedeus/nitter))

### Wallhaven

NSFW images supported only with API key, to use it, get it from [account settings](https://wallhaven.cc/settings/account), then run

```sh
art-dl --action wallhaven:key
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
- **imgur.com**
  - `https://imgur.com/a/<id>`
  - `https://imgur.com/gallery/<id>`
  - `https://imgur.com/t/<tag>/<id>`
- **pixiv.net**
  - `https://www.pixiv.net/artworks/<id>`
  - `https://www.pixiv.net/<lang>/artworks/<id>`

  - Other sites with the same content as pixiv:
    - `https://zettai.moe/detail?id=<id>`
- **reddit.com**
  - `https://redd.it/<id>`
  - `https://www.reddit.com/comments/<id>`
  - `https://www.reddit.com/r/<subreddit>/comments/<id>/<any name>`
- **twitter.com**
  - `https://(mobile.)twitter.com/<account>/status/<id>`
  - `https://nitter.net/<account>/status/<id>`
- **wallhaven.cc**
  - `https://wallhaven.cc/w/<id>`
  - `https://whvn.cc/<id>`
