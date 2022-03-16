import asyncio
from glob import glob
from urllib.parse import urlparse
import aiofiles
import aiohttp
import os
from app.creds import get_creds

from app.utils import filename_normalize, mkdir

SLUG = 'wallhaven'

API_URL = 'https://wallhaven.cc/api/v1/w/'

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if parsed.netloc == 'wallhaven.cc':
		# strip 'w'
		path.pop(0)

	return { 'id': path[0] }

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

async def download(urls_to_download: list[str] | str, data_folder: str, with_key = False):
	urls = urls_to_download if isinstance(urls_to_download, list) else [urls_to_download]
	mkdir(data_folder)

	retry_with_key = []

	creds = get_creds()
	has_api_key = not (
		creds is None or
		creds.get(SLUG) is None or
		creds[SLUG]['api_key'] is None
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

			# loop for retrying on rate limit
			while True:
				async with session.get(API_URL + parsed['id'], params=params) as response:
					if response.status == 429:
						print('To many requests, sleeping for 10 seconds')
						await asyncio.sleep(10)
						continue
					elif response.status == 401:
						if not with_key:
							data = None
							if not has_api_key:
								print('api_key not present, NSFW', parsed['id'], '- skipping')
								break
							print('NSFW', parsed['id'], '- queueing')
							retry_with_key.append(url)
							break
						else:
							print('Invalid api_key')
							return

					data = (await response.json())['data']
					break

			if data is None:
				continue

			print('Download', data['id'], '', end='', flush=True)

			full_url = data['path']
			name = (
				data['id']
				+ ' - '
				+ ', '.join(map(lambda tag: tag['name'], data['tags']))
			)
			name = filename_normalize(name) + os.path.splitext(full_url)[1]
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
