from aiohttp import ClientSession
from asyncio import sleep
from collections import namedtuple
from enum import Enum
from glob import glob
from typing import Any, Tuple
from urllib.parse import urlparse
import os.path

from art_dl.creds import get_creds
from art_dl.utils.download import download_binary
from art_dl.utils.path import filename_normalize, filename_shortening, mkdir
from art_dl.utils.print import print_inline_end
import art_dl.cache as cache

SLUG = 'wallhaven'

API_URL = 'https://wallhaven.cc/api/v1/w/'

class FetchDataAction(Enum):
	download = 0
	retry_with_key = 1
	skip = 2

Parsed = namedtuple('Parsed', ['id'])

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if parsed.netloc == 'wallhaven.cc':
		# strip 'w'
		path.pop(0)

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
				print('To many requests, sleeping for 10 seconds')
				await sleep(10)
				continue
			elif response.status == 401:
				if with_key:
					print('Invalid api_key')
					return None, FetchDataAction.skip

				if has_api_key:
					print('NSFW', img_id, '- queueing')
					return None, FetchDataAction.retry_with_key

				print('api_key not present, NSFW', img_id, '- skipping')
				return None, FetchDataAction.skip

			data = (await response.json())['data']
			data = {
				'id': data['id'],
				'path': data['path'],
				'tags': list(t['name'] for t in data['tags'])
			}
			return data, FetchDataAction.download

async def download(urls: list[str], data_folder: str, with_key = False):
	mkdir(data_folder)

	retry_with_key = []

	creds = get_creds()
	has_api_key = not (
		creds is None or
		creds.get(SLUG) is None or
		creds[SLUG].get('api_key') is None
	)

	if with_key:
		# second check only for LSP (typechecking)
		if has_api_key and creds is not None:
			print('Downloading with api_key')
			params = { 'apikey': creds[SLUG]['api_key'] }
		else:
			print('You should add api_key')
			return
	else:
		params = {}

	async with ClientSession() as session:
		for url in urls:
			parsed = parse_link(url)
			existing = glob(f'{data_folder}/{parsed.id} - *.*')
			if len(existing) == 1:
				print('Skip existing:', parsed.id)
				continue
			elif len(existing) > 1:
				print('Duplicated files for art', parsed.id)
				continue

			if url in retry_with_key:
				print('Duplicate link:', url)
				continue

			cached = cache.select(SLUG, parsed.id, as_json=True)

			if cached is None:
				data, action = await fetch_data(
					session,
					parsed.id,
					params,
					with_key,
					has_api_key
				)

				if action == FetchDataAction.retry_with_key:
					retry_with_key.append(url)
				if action != FetchDataAction.download:
					continue

				cache.insert(SLUG, parsed.id, data, as_json=True)
			else:
				data = cached

			print_inline_end('Download', data['id'])

			full_url = data['path']
			name = data['id'] + ' - ' + ', '.join(data['tags'])
			name = filename_normalize(name) + os.path.splitext(full_url)[1]
			name = filename_shortening(name, with_ext=True)
			filename = os.path.join(data_folder, name)

			await download_binary(session, full_url, filename)
			print('OK')

	if len(retry_with_key) > 0:
		return await download(retry_with_key, data_folder, True)

def register():
	"""Ask key"""
	creds = get_creds()
	if (
		creds is not None and
		creds.get(SLUG) is not None and
		creds[SLUG].get('api_key') is not None
	):
		ans = input('Key already saved, again? [y/N] ')
		if ans.lower() in ['n', '']:
			return {
				SLUG: { 'api_key': creds[SLUG]['api_key'] }
			}
		elif ans.lower() != 'y':
			print('What?')
			quit(1)
	return {
		SLUG: { 'api_key': input('Enter api_key: ') }
	}
