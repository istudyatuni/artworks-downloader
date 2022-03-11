# Downloader for artstation.com

## Install

Clone this repo, then from inside the project

```sh
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Usage

```
python main.py [-h] [-a ARTIST] [--album ALBUM] [--folder FOLDER]

options:
  -h, --help            show this help message and exit
  -a ARTIST, --artist ARTIST
                        Artist id
  --album ALBUM         Album id to download. If not specified, all albums downloaded
  --folder FOLDER       Folder to save artworks. Default folder - data
```

The `artist` option is mandatory, the others are optional. If the `album` option is not specified, all albums of the artist will be downloaded.

Default folder is `data`.
