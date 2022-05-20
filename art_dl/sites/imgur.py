import os.path
from collections import Counter, namedtuple
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from art_dl.cache import cache
from art_dl.log import Logger, Progress
from art_dl.utils.download import download_binary
from art_dl.utils.path import filename_normalize, mkdir
from art_dl.utils.print import counter2str
from art_dl.utils.proxy import ClientSession, ProxyClientSession

SLUG = 'imgur'
API_URL = 'https://api.imgur.com/3/{type}/{id}'
# client_id just from devtools
HEADERS = {
	'authorization': 'Client-ID 546c25a59c58ad7'
}

logger = Logger(prefix=[SLUG, 'download'], inline=True)
progress = Progress()

Parsed = namedtuple('Parsed', ['id', 'type'], defaults=[None, None])


class LinkType(str, Enum):
	album = 'album'
	image = 'image'


class DownloadResult(str, Enum):
	download = 'download'
	skip = 'skip'


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
	logger.verbose('fetch info', album.id, progress=progress)

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
	session: ClientSession, link: str, save_folder: str, name: str
) -> DownloadResult:
	filename = os.path.join(save_folder, name)
	if os.path.exists(filename):
		logger.verbose('skip existing', name, progress=progress)
		return DownloadResult.skip

	logger.info('download', name, progress=progress)
	await download_binary(session, link, filename)
	return DownloadResult.download


async def download(urls: list[str], data_folder: str):
	stats = Counter()  # type: ignore
	progress.total = len(urls)

	sep = ' - '

	async with ProxyClientSession() as session:
		for url in urls:
			progress.i += 1

			parsed = parse_link(url)

			if parsed.id is None:
				logger.warn('unsupported link', url)
				stats.update(skip=1)
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
				# save to sub-folder
				save_folder = os.path.join(data_folder, title_prefix)
				title_prefix = ''
			mkdir(save_folder)

			for image in images:
				title = (
					sep.join([title_prefix, image['title'],
								image['id']]).strip(sep).replace(sep * 2, sep)
				)
				name = title + image['ext']
				res = await download_art(session, image['link'], save_folder, name)
				stats.update({res.value: 1})

	logger.info(counter2str(stats))
