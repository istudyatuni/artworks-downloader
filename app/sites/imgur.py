from collections import namedtuple
from typing import Any
from urllib.parse import urlparse
import aiofiles
import aiohttp
import os.path

from app.utils import filename_normalize, mkdir
import app.cache as cache

# client_id just from devtools
API_ALBUM_URL = 'https://api.imgur.com/post/v1/albums/{id}?client_id=546c25a59c58ad7&include=media'
SLUG = 'imgur'

Parsed = namedtuple('Parsed', ['id'])

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if path[0] == 'a' or path[0] == 'gallery':
		# https://imgur.com/a/<id>
		# https://imgur.com/gallery/<id>
		return Parsed(path[1])

	if path[0] == 't':
		# https://imgur.com/t/<tag>/<id>
		return Parsed(path[2])

	return Parsed(None)

async def fetch_info(session: aiohttp.ClientSession, album_id: str) -> Any:
	async with session.get(API_ALBUM_URL.format(id=album_id)) as response:
		if response.ok:
			return await response.json()
		response.raise_for_status()

async def download_art(
	session: aiohttp.ClientSession,
	url: str,
	save_folder: str,
	name: str,
	indent=False
):
	indent_str = '  ' if indent else ''
	filename = os.path.join(save_folder, name)
	if os.path.exists(filename):
		return print(indent_str + 'Skip existing:', name)

	async with session.get(url) as response:
		if response.ok:
			async with aiofiles.open(filename, 'wb') as file:
				print(indent_str + 'Download', name)
				return await file.write(await response.read())
		response.raise_for_status()

async def download(urls: list[str], data_folder: str):
	sep = ' - '

	async with aiohttp.ClientSession() as session:
		for url in urls:
			parsed = parse_link(url)

			if parsed.id is None:
				print('Unsupported link', url)
				continue

			cached = cache.select(SLUG, parsed.id, as_json=True)

			if cached is None:
				info = await fetch_info(session, parsed.id)
				cache_info = {
					'id': info['id'],
					'title': info['title'],
					'media': list({
						'id': image['id'],
						'url': image['url'],
						'ext': image['ext'],
						'metadata': { 'title': image['metadata']['title'] }
					} for image in info['media'])
				}
				cache.insert(SLUG, parsed.id, cache_info, as_json=True)
			else:
				info = cached

			media = info['media']
			one_media = len(media) == 1
			title = sep.join([info['title'], info['id']]).strip(sep)
			title = filename_normalize(title)

			if one_media:
				save_folder = data_folder
			else:
				print(title)
				save_folder = os.path.join(data_folder, title)
				title = ''
			mkdir(save_folder)

			for image in media:
				title = (
					sep
					.join([title, image['metadata']['title'], image['id']])
					.strip(sep)
					.replace(sep * 2, sep)
				)
				await download_art(
					session,
					image['url'],
					save_folder,
					title + '.' + image['ext'],
					indent=not one_media
				)
