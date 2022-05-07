from enum import Enum
from aiohttp import ClientSession
from collections import namedtuple
from typing import Any
from urllib.parse import urlparse
import os.path

from app.utils.download import download_binary
from app.utils.path import filename_normalize, mkdir
from app.utils.print import print_inline_end
import app.cache as cache

SLUG = 'imgur'
API_URL = 'https://api.imgur.com/3/{type}/{id}'
# client_id just from devtools
HEADERS = {
	'authorization': 'Client-ID 546c25a59c58ad7'
}

Parsed = namedtuple('Parsed', ['id', 'type'], defaults=[None, None])

class LinkType(str, Enum):
	album = 'album'
	image = 'image'

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if path[0] == 'a' or path[0] == 'gallery':
		# https://imgur.com/a/<id>
		# https://imgur.com/gallery/<id>
		return Parsed(path[1], LinkType.album)

	if path[0] == 't':
		# https://imgur.com/t/<tag>/<id>
		return Parsed(path[2], LinkType.album)

	if len(path) == 1:
		# https://imgur.com/<id>
		return Parsed(path[0], LinkType.image)

	return Parsed()

async def fetch_info(session: ClientSession, album: Parsed) -> Any:
	url = API_URL.format(id=album.id, type=album.type)
	async with session.get(url, headers=HEADERS) as response:
		response.raise_for_status()
		info = (await response.json())['data']

	if info.get('is_album', False) is False:
		# the same model, so just put to array
		info['images'] = [info]

	return {
		'id': info['id'],
		'title': info['title'] or '',
		'images': list({
			'id': image['id'],
			'link': image['link'],
			'ext': os.path.splitext(image['link'])[-1],
			'title': image['title'] or '',
		} for image in info['images']),
	}

async def download_art(
	session: ClientSession,
	link: str,
	save_folder: str,
	name: str,
	indent=False
):
	indent_str = '  ' if indent else ''
	filename = os.path.join(save_folder, name)
	if os.path.exists(filename):
		return print(indent_str + 'Skip existing:', name)

	print_inline_end(indent_str + 'Download', name)
	await download_binary(session, link, filename)
	print('OK')

async def download(urls: list[str], data_folder: str):
	sep = ' - '

	async with ClientSession() as session:
		for url in urls:
			parsed = parse_link(url)

			if parsed.id is None:
				print('Unsupported link', url)
				continue

			cached = cache.select(SLUG, parsed.id, as_json=True)

			if cached is None:
				info = await fetch_info(session, parsed)
				cache.insert(SLUG, parsed.id, info, as_json=True)
			else:
				info = cached

			images = info['images']
			one_image = len(images) == 1
			title_prefix = sep.join([info['title'], info['id']]).strip(sep)
			title_prefix = filename_normalize(title_prefix)

			if one_image:
				save_folder = data_folder
			else:
				print(title_prefix)
				# save to sub-folder
				save_folder = os.path.join(data_folder, title_prefix)
				title_prefix = ''
			mkdir(save_folder)

			for image in images:
				title = (
					sep
					.join([title_prefix, image['title'], image['id']])
					.strip(sep)
					.replace(sep * 2, sep)
				)
				await download_art(
					session,
					image['link'],
					save_folder,
					title + image['ext'],
					indent=not one_image
				)
