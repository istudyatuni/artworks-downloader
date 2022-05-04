from argparse import ArgumentParser
from asyncio import new_event_loop, set_event_loop
from typing import Optional, Tuple
from urllib.parse import urlparse
import os.path

from app.creds import save_creds
from app.sites import download, register
from app.utils.retry import retry

SLUGS = {
	'danbooru.donmai.us': 'danbooru',
	'imgur.com': 'imgur',
	'redd.it': 'reddit',
	'safebooru.donmai.us': 'danbooru',
	'wallhaven.cc': 'wallhaven',
	'whvn.cc': 'wallhaven',
	'www.artstation.com': 'artstation',
	'www.deviantart.com': 'deviantart',
	'www.pixiv.net': 'pixiv',
	'www.reddit.com': 'reddit',
	'zettai.moe': 'pixiv',
}

def detect_site(url: str) -> str | None:
	return SLUGS.get(urlparse(url).netloc)

def parse_args():
	parser = ArgumentParser(description='Artworks downloader')

	parser.add_argument('-u', '--url', type=str, help='URL to download')
	parser.add_argument('-l', '--list', type=str, help='File with list of URLs to download', default=None)
	parser.add_argument('--folder', type=str, help='Folder to save artworks. Default folder - data', default='data')

	parser.add_argument('--action', type=str, default=None)

	return parser.parse_args()

async def process_list(urls: list[str], folder: str):
	if len(urls) == 0:
		print('List is empty')
		return

	mapping = {s: [] for s in SLUGS.values()}
	for u in urls:
		site_slug = detect_site(u)
		if site_slug is None:
			print('Unknown link', u)
			continue

		mapping[site_slug].append(u)

	print('Saving to', folder, '\n')
	for slug, l in mapping.items():
		if len(l) == 0:
			continue

		save_folder = os.path.join(folder, slug)
		print(slug.title(), '\n')
		await download(slug)(l, save_folder)
		print()

def prepare() -> Optional[Tuple[list[str], str]]:
	args = parse_args()
	# put to list for handling single url as list when download
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

def run(urls: list[str], folder: str):
	loop = new_event_loop()
	set_event_loop(loop)
	loop.run_until_complete(process_list(urls, folder))

def main():
	if (result := prepare()) is None:
		quit(0)

	urls, folder = result

	run(urls, folder)
	while (to_retry := retry.get()) is not None:
		print('Retrying', len(to_retry), 'urls\n')
		retry.clear()
		run(to_retry, folder)

	retry.clear(force=True)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print('\nExiting')
