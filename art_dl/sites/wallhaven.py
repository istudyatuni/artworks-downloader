import os.path
from asyncio import sleep
from collections import Counter, namedtuple
from enum import Enum
from glob import glob
from typing import Any, Tuple
from urllib.parse import urlparse

from art_dl.cache import cache
from art_dl.log import Logger, Progress
from art_dl.utils.credentials import creds
from art_dl.utils.download import download_binary
from art_dl.utils.path import filename_normalize, filename_shortening, mkdir
from art_dl.utils.print import counter2str
from art_dl.utils.proxy import ClientSession, ProxyClientSession

SLUG = 'wallhaven'
CREDS_PATH = [SLUG, 'api_key']

API_URL = 'https://wallhaven.cc/api/v1/w/'

logger = Logger(prefix=[SLUG, 'download'], inline=True)
progress = Progress()


class FetchDataAction(Enum):
	download = 0
	retry_with_key = 1
	skip = 2


Parsed = namedtuple('Parsed', ['id'])


def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if parsed.netloc == 'wallhaven.cc':
		# https://wallhaven.cc/w/<id>
		# strip 'w'
		path.pop(0)

	# https://whvn.cc/<id>
	return Parsed(path[0])


async def fetch_data(
	session: ClientSession,
	img_id: str,
	params: dict,
	with_key: bool,
	has_api_key: bool,
) -> Tuple[Any, FetchDataAction]:
	# loop for retrying on rate limit
	while True:
		async with session.get(API_URL + img_id, params=params) as response:
			if response.status == 429:
				logger.info('to many requests, sleeping for 10 seconds', progress=progress)
				await sleep(10)
				continue
			elif response.status == 401:
				if with_key:
					logger.warn('invalid api_key, skip')
					return None, FetchDataAction.skip

				if has_api_key:
					logger.verbose('queueing NSFW', img_id)
					return None, FetchDataAction.retry_with_key

				logger.warn('skip NSFW', img_id, '(api_key not present)')
				return None, FetchDataAction.skip

			data = (await response.json())['data']
			data = {
				'id': data['id'],
				'path': data['path'],
				'tags': list(t['name'] for t in data['tags'])
			}
			return data, FetchDataAction.download


async def download(urls: list[str], data_folder: str, with_key=False):
	mkdir(data_folder)

	stats = Counter()  # type: ignore
	progress.set(0, len(urls))

	retry_with_key = []

	api_key = creds.get(CREDS_PATH)
	has_api_key = api_key is not None
	params = {}
	if with_key:
		if has_api_key:
			logger.info('using api_key', end='\n')
			params = {
				'apikey': api_key
			}
		else:
			logger.warn('you should add api_key')
			return

	async with ProxyClientSession() as session:
		for url in urls:
			progress.i += 1
			should_skip = False

			parsed = parse_link(url)
			existing = glob(f'{data_folder}/{parsed.id} - *.*')
			if len(existing) == 1:
				logger.verbose('skip existing', parsed.id)
				should_skip = True
			elif len(existing) > 1:
				logger.warn('duplicated files for art', parsed.id)
				should_skip = True

			if url in retry_with_key:
				logger.verbose('duplicate link', url)
				should_skip = True

			if should_skip:
				stats.update(skip=1)
				continue

			cached = cache.select(SLUG, parsed.id, as_json=True)

			if cached is None:
				data, action = await fetch_data(session, parsed.id, params, with_key, has_api_key)

				if action == FetchDataAction.retry_with_key:
					stats.update(will_retry=1)
					retry_with_key.append(url)
				elif action == FetchDataAction.skip:
					stats.update(skip=1)
				if action != FetchDataAction.download:
					continue

				cache.insert(SLUG, parsed.id, data, as_json=True)
			else:
				data = cached

			logger.info('download', data['id'], progress=progress)

			full_url = data['path']
			name = data['id'] + ' - ' + ', '.join(data['tags'])
			name = filename_normalize(name) + os.path.splitext(full_url)[1]
			name = filename_shortening(name, with_ext=True)
			filename = os.path.join(data_folder, name)

			await download_binary(session, full_url, filename)
			stats.update(download=1)

	logger.info(counter2str(stats))

	if len(retry_with_key) > 0:
		logger.newline(normal=True)
		return await download(retry_with_key, data_folder, True)


def register():
	"""Ask key"""
	api_key = creds.get(CREDS_PATH)
	if api_key is not None:
		ans = input('Key already saved, again? [y/N] ')
		if ans.lower() in ['n', '']:
			return
		elif ans.lower() != 'y':
			print('What?')
			quit(1)
	creds.save(CREDS_PATH, input('Enter api_key: '))
	logger.info('saved')
