# Artworks downloader

From artstation.com and deviantart.com

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

### Artstation

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
  python main.py --deviantart register
  ```

  - paste needed values

- authorize application
  - open suggested link
  - click "Authorize"

After that you can use it just like

```sh
python main.py -u [URL here]
```

## Supported URLs

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
