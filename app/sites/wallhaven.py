from enum import Enum
from glob import glob
from typing import Any, Tuple
from urllib.parse import urlparse
import aiofiles
import aiohttp
import asyncio
import os

from app.creds import get_creds
from app.utils import filename_normalize, filename_shortening, mkdir

SLUG = 'wallhaven'

API_URL = 'https://wallhaven.cc/api/v1/w/'

class FetchDataAction(Enum):
	download = 0
	retry_with_key = 1
	skip = 2

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if parsed.netloc == 'wallhaven.cc':
		# strip 'w'
		path.pop(0)

	return { 'id': path[0] }

async def fetch_data(
	session: aiohttp.ClientSession,
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
				await asyncio.sleep(10)
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

			return (await response.json())['data'], FetchDataAction.download

async def fetch_image(session: aiohttp.ClientSession, url: str, name: str, folder: str):
	filename = os.path.join(folder, name)
	async with session.get(url) as response:
		async with aiofiles.open(filename, 'wb') as file:
			try:
				await file.write(await response.read())
			except:
				os.remove(filename)
				# \b\b for print above ^C
				print('\b\bREMOVING EMPTY FILE')
				raise
			print('OK')

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
			print('Please add api_key')
			return
	else:
		params = {}

	async with aiohttp.ClientSession() as session:
		for url in urls:
			parsed = parse_link(url)
			existing = glob(f'{data_folder}/{parsed["id"]} - *.*')
			if len(existing) == 1:
				print('Skip existing:', parsed['id'])
				continue
			if url in retry_with_key:
				print('Duplicate link:', url)
				continue

			data, action = await fetch_data(
				session,
				parsed['id'],
				params,
				with_key,
				has_api_key
			)

			if action == FetchDataAction.retry_with_key:
				retry_with_key.append(url)
			if action != FetchDataAction.download:
				continue

			print('Download', data['id'], '', end='', flush=True)

			full_url = data['path']
			name = (
				data['id']
				+ ' - '
				+ ', '.join(map(lambda tag: tag['name'], data['tags']))
			)
			name = filename_normalize(name) + os.path.splitext(full_url)[1]
			name = filename_shortening(name, with_ext=True)
			await fetch_image(session, full_url, name, data_folder)

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
