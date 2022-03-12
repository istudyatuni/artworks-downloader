import argparse
import asyncio
import os
from urllib.parse import urlparse

from sites import download

SLUGS = {
	'www.artstation.com': 'artstation',
	'www.deviantart.com': 'deviantart',
}

def detect_site(url: str) -> str:
	return SLUGS[urlparse(url).netloc]

def parse_args():
	parser = argparse.ArgumentParser(description='Artworks downloader')

	parser.add_argument('url', type=str, help='URL to download')
	parser.add_argument('--folder', type=str, help='Folder to save artworks. Default folder - data', default='data')

	return parser.parse_args()

async def main():
	args = parse_args()
	url = args.url
	folder = os.path.abspath(args.folder)

	await download(detect_site(url))(url, folder)

if __name__ == '__main__':
	asyncio.run(main())
