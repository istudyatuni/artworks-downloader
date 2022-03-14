import argparse
import asyncio
import os
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.creds import save_creds
from app.sites import download, register

SLUGS = {
	'www.artstation.com': 'artstation',
	'www.deviantart.com': 'deviantart',
	'www.pixiv.net': 'pixiv',
}

def detect_site(url: str) -> str:
	return SLUGS[urlparse(url).netloc]

def parse_args():
	parser = argparse.ArgumentParser(description='Artworks downloader')

	parser.add_argument('-u', '--url', type=str, help='URL to download')
	parser.add_argument('-l', '--list', type=str, help='File with list of URLs to download', default=None)
	parser.add_argument('--folder', type=str, help='Folder to save artworks. Default folder - data', default='data')

	parser.add_argument('--deviantart', type=str, default=None)

	return parser.parse_args()

async def process(url: str, folder: str):
	site_slug = detect_site(url)
	await download(site_slug)(url, os.path.join(folder, site_slug))

async def process_list(urls: list[str], folder: str):
	if len(urls) == 1 and urls[0] == '':
		print('List is empty')
		return

	mapping = {s: [] for s in SLUGS.values()}
	for u in urls:
		mapping[detect_site(u)].append(u)
	for slug, l in mapping.items():
		if len(l) == 0:
			continue
		try:
			await download(slug)(l, os.path.join(folder, slug))
		except NotImplementedError:
			print('List for', slug, 'not supported, skipping')

def main() -> Optional[Tuple[str | list[str], str]]:
	args = parse_args()
	to_dl = args.url
	urls_file = args.list
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
		return

	if urls_file is not None:
		with open(urls_file) as file:
			content = file.read().strip().split('\n')
			to_dl = map(lambda s: s.strip(), filter(lambda e: bool(e), content))
		to_dl = list(to_dl)

	return to_dl, folder

if __name__ == '__main__':
	if (result := main()) is None:
		quit(0)

	result, folder = result
	if isinstance(result, list):
		asyncio.run(process_list(result, folder))
	else:
		asyncio.run(process(result, folder))
