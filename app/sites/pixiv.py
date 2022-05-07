from aiohttp import ClientSession, ServerDisconnectedError
from asyncio import sleep
from collections import namedtuple
from urllib.parse import parse_qs, urlparse
import json
import os.path

from app.utils.download import download_binary
from app.utils.log import DownloadStats, Logger, Progress
from app.utils.path import filename_normalize, filename_unhide, mkdir
from app.utils.url import parse_range
import app.cache as cache

SLUG = 'pixiv'
HEADERS = {
	'referer': 'https://www.pixiv.net/',
}
URL = 'https://www.pixiv.net/en/artworks/'

logger = Logger(prefix=['download', SLUG], inline=True)
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

	return Parsed()

async def fetch_info(session: ClientSession, parsed: Parsed):
	url = URL + parsed.id
	logger.info('fetch info', parsed.id, progress=progress)
	async with session.get(url) as response:
		data = await response.text()

	id_ind = data.find('meta-preload-data')
	script_ind = data.find('<script async', id_ind)

	# 28 is len of meta-preload-data" content='
	# 3 is back-offset from <script
	json_data = json.loads(data[id_ind + 28:script_ind - 3])
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
	session: ClientSession,
	art_info: Parsed,
	info: dict,
	save_folder: str
) -> DownloadStats:
	stats = DownloadStats()

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
			stats.skip += 1
			continue

		logger.info('download', *log_info, progress=progress)
		url = base_url + str(i) + ext
		await download_binary(session, url, filename)
		stats.download += 1

	return stats

async def download(urls: list[str], data_folder: str):
	stats = DownloadStats()
	progress.total = len(urls)

	async with ClientSession(headers=HEADERS) as session:
		for url in urls:
			progress.i += 1

			parsed = parse_link(url)
			if parsed.id is None:
				logger.info('unsupported link:', url, end='\n')
				continue

			cached: dict = cache.select(SLUG, parsed.id, as_json=True)

			if cached is None:
				info = await fetch_info(session, parsed)
				cache.insert(SLUG, parsed.id, info, as_json=True)
			else:
				info = cached

			save_folder = os.path.join(data_folder, info['artist'])
			mkdir(save_folder)

			while True:
				try:
					dl_stats = await download_art(session, parsed, info, save_folder)
					stats += dl_stats
					break
				except ServerDisconnectedError:
					logger.info('error, retrying in 5 seconds')
					await sleep(5)

	logger.info(stats)
