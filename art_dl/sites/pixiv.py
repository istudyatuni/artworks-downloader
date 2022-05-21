import json
import os.path
from asyncio import sleep
from collections import Counter, namedtuple
from urllib.parse import parse_qs, urlparse

from aiohttp import ServerDisconnectedError
from lxml import etree

from art_dl.cache import cache
from art_dl.log import Logger, Progress
from art_dl.utils.download import download_binary
from art_dl.utils.path import filename_normalize, filename_unhide, mkdir
from art_dl.utils.print import counter2str
from art_dl.utils.proxy import ClientSession, ProxyClientSession
from art_dl.utils.url import parse_range

SLUG = 'pixiv'
HEADERS = {
	'referer': 'https://www.pixiv.net/',
}
URL = 'https://www.pixiv.net/en/artworks/'

ERROR_MESSAGES = {
	'404': 'work has been deleted or the ID does not exist'
}

logger = Logger(prefix=[SLUG, 'download'], inline=True)
progress = Progress()

Parsed = namedtuple('Parsed', ['id', 'range'], defaults=[None, None])


def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	imgs_range = parse_range(parsed.fragment)
	if imgs_range is not None:
		# convert pixiv indexing, which starts from 1,
		# to indexing like range() function, which starts from 0
		imgs_range = list(map(lambda i: i - 1, imgs_range))

	if parsed.netloc == 'zettai.moe':
		# https://zettai.moe/detail?id=<id>
		query = parse_qs(parsed.query)
		return Parsed(query['id'][0], imgs_range)

	if path[1] == 'artworks':
		# https://www.pixiv.net/<lang>/artworks/<id>
		return Parsed(path[2], imgs_range)

	if path[0] == 'artworks':
		# https://www.pixiv.net/artworks/<id>
		return Parsed(path[1], imgs_range)

	return Parsed()


async def fetch_info(session: ClientSession, parsed: Parsed):
	url = URL + parsed.id
	logger.info('fetch info', parsed.id, progress=progress)
	async with session.get(url) as response:
		if response.status == 404:
			return {
				'error': 404
			}
		data = await response.text()

	root = etree.HTML(data)
	json_data = json.loads(root.xpath('//meta[@name=\'preload-data\']/@content')[0])
	art = json_data['illust'][parsed.id]

	return {
		'count': art['pageCount'],
		'first_url': art['urls']['original'],
		'id': parsed.id,
		# username can begin with a dot
		'artist': filename_unhide(filename_normalize(art['userName'])),
		'title': filename_normalize(art['title']),
	}


async def download_art(
	session: ClientSession, art_info: Parsed, info: dict, save_folder: str
) -> Counter:
	stats = Counter()  # type: ignore

	# https://i.pximg.net/img-original/img/.../xxx_p0.png
	base_url, ext = os.path.splitext(info['first_url'])
	base_url = base_url[:-1]

	total_imgs_count = info['count']
	ind_range = art_info.range or range(total_imgs_count)

	name_prefix = art_info.id + ' - ' + info['title']
	for i in ind_range:
		if i >= total_imgs_count:
			# prevent range bigger than images count
			# equal because all images indexes are in [0, 'count' - 1]
			break

		log_info = [art_info.id]
		if total_imgs_count > 1:
			# log image number only if more then one image
			log_info.extend(['/', i + 1])

		name = name_prefix + f'_p{i}' + ext
		filename = os.path.join(save_folder, name)
		if os.path.exists(filename):
			logger.verbose('skip existing', *log_info, progress=progress)
			stats.update(skip=1)
			continue

		logger.info('download', *log_info, progress=progress)
		url = base_url + str(i) + ext
		await download_binary(session, url, filename)
		stats.update(download=1)

	return stats


async def download(urls: list[str], data_folder: str):
	stats = Counter()  # type: ignore
	progress.total = len(urls)

	async with ProxyClientSession(headers=HEADERS) as session:
		for url in urls:
			progress.i += 1

			parsed = parse_link(url)
			if parsed.id is None:
				logger.warn('unsupported link:', url)
				stats.update(skip=1)
				continue

			cached: dict = cache.select(SLUG, parsed.id, as_json=True)

			if cached is None:
				info = await fetch_info(session, parsed)

				# do not cache because it can be just wrong url, not deleted
				if 'error' in info:
					logger.warn(parsed.id, 'error:', ERROR_MESSAGES[str(info['error'])])
					continue

				cache.insert(SLUG, parsed.id, info, as_json=True)
			else:
				info = cached

			save_folder = os.path.join(data_folder, info['artist'])
			mkdir(save_folder)

			while True:
				try:
					dl_stats = await download_art(session, parsed, info, save_folder)
					stats.update(dl_stats)
					break
				except ServerDisconnectedError:
					logger.info('error, retrying in 5 seconds')
					await sleep(5)

	logger.info(counter2str(stats))
