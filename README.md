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
