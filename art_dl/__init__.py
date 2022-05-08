from argparse import ArgumentParser
from asyncio import new_event_loop, set_event_loop
from typing import Optional, Tuple
from urllib.parse import urlparse
import os.path

from art_dl.creds import save_creds
from art_dl.sites import download, register
from art_dl.utils.cleanup import cleanup
from art_dl.utils.log import Logger, set_verbosity
from art_dl.utils.retry import retry

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

logger = Logger(prefix=['main'])

def detect_site(url: str) -> str | None:
	return SLUGS.get(urlparse(url).netloc)

def parse_args():
	parser = ArgumentParser(description='Artworks downloader')

	parser.add_argument('-u', '--url', type=str, help='URL to download')
	parser.add_argument('-l', '--list', type=str, help='File with list of URLs to download', default=None)
	parser.add_argument('--folder', type=str, help='Folder to save artworks. Default folder - data', default='data')

	parser.add_argument('--action', type=str, default=None)

	parser.add_argument('-q', '--quiet', action='store_true', help='Do not show logs')
	parser.add_argument('-v', '--verbose', action='store_true', help='Show more logs')

	return parser.parse_args()

async def process_list(urls: list[str], folder: str):
	if len(urls) == 0:
		logger.info('list is empty')
		return
	elif len(urls) == 1 and urls[0] is None:
		logger.info('no link')
		return

	mapping = {s: [] for s in SLUGS.values()}
	for u in urls:
		site_slug = detect_site(u)
		if site_slug is None:
			logger.info('unknown link', u)
			continue

		mapping[site_slug].append(u)

	logger.info('saving to', folder)
	for slug, l in mapping.items():
		if len(l) == 0:
			continue

		save_folder = os.path.join(folder, slug)
		await download(slug)(l, save_folder)
		logger.newline(normal=True)

def prepare() -> Optional[Tuple[list[str], str]]:
	args = parse_args()
	# put to list for handling single url as list when download
	to_dl = [args.url]
	urls_file = args.list
	folder = os.path.abspath(args.folder)
	action = tuple(args.action.split(':')) if args.action else None

	if args.quiet and args.verbose:
		print('You must specify either --verbose or --quiet, not both')
		quit(1)
	set_verbosity(args.quiet, args.verbose)

	if action == ('deviantart', 'register'):
		creds = register('deviantart')()
		if creds is not None:
			save_creds(creds)
			logger.info('authorized')
		return
	elif action == ('wallhaven', 'key'):
		creds = register('wallhaven')()
		if creds is not None:
			save_creds(creds)
			logger.info('saved')
		return
	elif action is not None:
		logger.info('unknown action:', args.action)
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

def _real_main():
	if (result := prepare()) is None:
		quit(0)

	urls, folder = result

	run(urls, folder)
	while (to_retry := retry.get()) is not None:
		logger.info('retrying', len(to_retry), 'urls')
		retry.clear()
		run(to_retry, folder)

	retry.clear(force=True)

def main():
	cleanup.clean()
	try:
		_real_main()
	except KeyboardInterrupt:
		logger.set_prefix(inline=True)
		logger.warn('interrupted by user, exiting')
	cleanup.clean()

if __name__ == '__main__':
	main()
