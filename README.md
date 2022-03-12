# Downloader from artstation.com

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

positional arguments:
  url              URL to download

options:
  -h, --help       show this help message and exit
  --folder FOLDER  Folder to save artworks. Default folder - data
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
