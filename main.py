import argparse
import asyncio
import os
from typing import Optional, Tuple
from urllib.parse import urlparse

from creds import save_creds
from sites import download, register

SLUGS = {
	'www.artstation.com': 'artstation',
	'www.deviantart.com': 'deviantart',
}

def detect_site(url: str) -> str:
	return SLUGS[urlparse(url).netloc]

def parse_args():
	parser = argparse.ArgumentParser(description='Artworks downloader')

	parser.add_argument('-u', '--url', type=str, help='URL to download')
	parser.add_argument('--folder', type=str, help='Folder to save artworks. Default folder - data', default='data')

	parser.add_argument('--deviantart', type=str, default=None)

	return parser.parse_args()

async def process(url, folder):
	site_slug = detect_site(url)
	await download(site_slug)(url, os.path.join(folder, site_slug))

def main() -> Optional[Tuple[str, str]]:
	args = parse_args()
	url = args.url
	folder = os.path.abspath(args.folder)
	deviantart_action = args.deviantart

	if deviantart_action == 'register':
		creds = register('deviantart')()
		if creds is not None:
			save_creds(creds)
			print('Authorized')
		return
	elif deviantart_action is not None:
		print('Unknown deviantart action:', deviantart_action)
		quit(1)

	return url, folder

if __name__ == '__main__':
	if (result := main()) is None:
		quit(0)

	url, folder = result
	asyncio.run(process(url, folder))
