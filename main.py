import argparse
import asyncio
import os
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.creds import save_creds
from app.sites import download, register

SLUGS = {
	'redd.it': 'reddit',
	'wallhaven.cc': 'wallhaven',
	'whvn.cc': 'wallhaven',
	'www.artstation.com': 'artstation',
	'www.deviantart.com': 'deviantart',
	'www.pixiv.net': 'pixiv',
	'www.reddit.com': 'reddit',
}

def detect_site(url: str) -> str | None:
	return SLUGS.get(urlparse(url).netloc)

def parse_args():
	parser = argparse.ArgumentParser(description='Artworks downloader')

	parser.add_argument('-u', '--url', type=str, help='URL to download')
	parser.add_argument('-l', '--list', type=str, help='File with list of URLs to download', default=None)
	parser.add_argument('--folder', type=str, help='Folder to save artworks. Default folder - data', default='data')

	parser.add_argument('--action', type=str, default=None)

	return parser.parse_args()

async def process_list(urls: list[str], folder: str):
	if len(urls) == 1 and urls[0] == '':
		print('List is empty')
		return

	mapping = {s: [] for s in SLUGS.values()}
	for u in urls:
		site_slug = detect_site(u)
		if site_slug is None:
			print('Unknown link', u)
			continue

		mapping[site_slug].append(u)
	for slug, l in mapping.items():
		if len(l) == 0:
			continue
		try:
			await download(slug)(l, os.path.join(folder, slug))
		except NotImplementedError:
			print('List for', slug, 'not supported, skipping')

def prepare() -> Optional[Tuple[list[str], str]]:
	args = parse_args()
	# put to list for hanling single url as list when download
	to_dl = [args.url]
	urls_file = args.list
	folder = os.path.abspath(args.folder)
	action = tuple(args.action.split(':')) if args.action else None

	if action == ('deviantart', 'register'):
		creds = register('deviantart')()
		if creds is not None:
			save_creds(creds)
			print('Authorized')
		return
	elif action == ('wallhaven', 'key'):
		creds = register('wallhaven')()
		if creds is not None:
			save_creds(creds)
			print('Saved')
		return
	elif action is not None:
		print('Unknown action:', args.action)
		return

	if urls_file is not None:
		with open(urls_file) as file:
			content = file.read().strip().split('\n')
			to_dl = map(lambda s: s.strip(), filter(lambda e: bool(e), content))
		to_dl = list(to_dl)

	return to_dl, folder

def main():
	if (result := prepare()) is None:
		quit(0)

	asyncio.run(process_list(*result))

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print('\nExiting')
