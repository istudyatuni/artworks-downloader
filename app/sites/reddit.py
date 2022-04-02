from collections import namedtuple
from typing import Any
from urllib.parse import urlparse
import aiohttp
import os.path

from app.utils.download import download_binary
from app.utils.path import filename_normalize, mkdir
import app.cache as cache

SLUG = 'reddit'

JSON_URI = 'https://www.reddit.com/comments/{id}.json'
IMAGE_URI = 'https://i.redd.it/'

DATA_CACHE_POSTFIX = ':data'
SKIP_CACHE_TAG = 'SKIP'

REDDIT_DOMAINS = ['reddit.com', 'i.redd.it', 'v.redd.it']

Parsed = namedtuple('Parsed', ['id'])

def parse_link(url: str) -> Parsed:
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if len(path) == 1 and parsed.netloc == 'redd.it':
		# https://redd.it/<id>
		return Parsed(id=path[0])

	if len(path) == 2 and path[0] == 'comments':
		# https://www.reddit.com/comments/<id>
		return Parsed(id=path[1])

	if len(path) >= 4 and path[0] == 'r' and path[2] == 'comments':
		# https://www.reddit.com/r/<subreddit>/comments/<id>/<any name>
		return Parsed(id=path[3])

	return Parsed(id=None)

async def fetch_data(session: aiohttp.ClientSession, url: str) -> Any:
	async with session.get(url) as response:
		response.raise_for_status()
		data = (await response.json())[0]['data']['children'][0]['data']

	media_metadata = data.get('media_metadata')
	data = {
		'domain': data['domain'],
		'is_gallery': data.get('is_gallery', False),
		'is_video': data['is_video'],
		'subreddit': data['subreddit'],
		'title': data['title'],
		'url': data['url'],
	}
	if data['is_gallery'] is True:
		data['media_ext'] = {
			# info['m'] is mime type
			media_id: info['m'].split('/')[1]
			for media_id, info in media_metadata.items()
		}
	return data

async def download_art(
	session: aiohttp.ClientSession,
	url: str,
	folder: str,
	name: str,
	indent = False
):
	indent_str = '  ' if indent else ''
	filename = os.path.join(folder, name)
	if os.path.exists(filename):
		return print(indent_str + 'Skip existing:', name)

	await download_binary(session, url, filename)
	print(indent_str + 'Download:', name)

async def download(urls: list[str], data_folder: str):
	sep = ' - '

	can_retry_other_site = []

	async with aiohttp.ClientSession() as session:
		for url in urls:
			parsed = parse_link(url)

			if parsed.id is None:
				print('Unsupported link:', url)
				continue

			cached = cache.select(SLUG, parsed.id)

			if cached == SKIP_CACHE_TAG:
				print('Skip cached:', url)
				continue

			if cached is None:
				data = await fetch_data(session, JSON_URI.format(id=parsed.id))
				cache.insert(SLUG, parsed.id + DATA_CACHE_POSTFIX, data, as_json=True)
			else:
				data = cache.select(SLUG, parsed.id + DATA_CACHE_POSTFIX, as_json=True)

			domain = data['domain']
			if domain not in REDDIT_DOMAINS:
				print('Media is from', domain, url + ':', data['url'])
				if domain == 'imgur.com':
					can_retry_other_site.append(data['url'])
				continue

			save_folder = os.path.join(data_folder, data['subreddit'])
			title = sep.join([data['title'], parsed.id])
			is_gallery: bool = data.get('is_gallery', False)

			if is_gallery:
				folder = os.path.join(save_folder, filename_normalize(title))
				mkdir(folder)
				print(title)

				for media_id, ext in data['media_ext'].items():
					url_filename = media_id + '.' + ext
					await download_art(
						session,
						IMAGE_URI + url_filename,
						folder,
						url_filename,
						indent=True
					)

				if cached is None:
					cache.insert(SLUG, parsed.id, 'gallery')
			elif data['is_video'] is True:
				print('Skip video:', url)
				cache.insert(SLUG, parsed.id, SKIP_CACHE_TAG)
				cache.delete(SLUG, parsed.id + DATA_CACHE_POSTFIX)
			else:
				img_url = data['url']
				url_filename = urlparse(img_url).path.lstrip('/')
				if cached is None:
					cache.insert(SLUG, parsed.id, 'image')

				media_id, ext = os.path.splitext(url_filename)
				filename = sep.join([title, media_id]) + ext
				mkdir(save_folder)
				await download_art(session, img_url, save_folder, filename)

	if len(can_retry_other_site) > 0:
		print('\nYou can rerun script for these urls:', *can_retry_other_site, sep='\n')
