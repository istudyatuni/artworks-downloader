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
from art_dl.utils.retry import retry

SLUG = 'reddit'

JSON_URI = 'https://www.reddit.com/comments/{id}.json'
IMAGE_URI = 'https://i.redd.it/'

DATA_CACHE_POSTFIX = ':data'
SKIP_CACHE_TAG = 'SKIP'

REDDIT_DOMAINS = ['reddit.com', 'i.redd.it', 'v.redd.it']

logger = Logger(prefix=[SLUG, 'download'], inline=True)
progress = Progress()

Parsed = namedtuple('Parsed', ['id'])


class DownloadResult(str, Enum):
	download = 'download'
	skip = 'skip'


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


async def fetch_data(session: ClientSession, url: str) -> Any:
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
	session: ClientSession,
	url: str,
	folder: str,
	name: str,
	log_name: str,
) -> DownloadResult:
	filename = os.path.join(folder, name)
	if os.path.exists(filename):
		logger.info('skip existing', log_name, progress=progress)
		return DownloadResult.skip

	logger.info('download', log_name, progress=progress)
	await download_binary(session, url, filename)
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
				logger.warn('unsupported link', url, progress=progress)
				stats.update(skip=1)
				continue

			cached = cache.select(SLUG, parsed.id)

			if cached == SKIP_CACHE_TAG:
				logger.verbose('skip', url, progress=progress)
				stats.update(skip_video=1)
				continue

			if cached is None:
				data = await fetch_data(session, JSON_URI.format(id=parsed.id))
				cache.insert(SLUG, parsed.id + DATA_CACHE_POSTFIX, data, as_json=True)
			else:
				data = cache.select(SLUG, parsed.id + DATA_CACHE_POSTFIX, as_json=True)

			domain = data['domain']
			if domain not in REDDIT_DOMAINS:
				logger.warn('media is from', domain, url + ':', data['url'], progress=progress)
				if domain == 'imgur.com':
					retry.add(data['url'])
					stats.update(will_retry=1)
				elif domain == 'i.imgur.com':
					imgur_id, _ = os.path.splitext(data['url'].split('/')[-1])
					retry.add('https://imgur.com/' + imgur_id)
					stats.update(will_retry=1)
				else:
					stats.update(skip=1)
				continue

			save_folder = os.path.join(data_folder, data['subreddit'])
			title = sep.join([data['title'], parsed.id])
			title = filename_normalize(title)
			is_gallery: bool = data.get('is_gallery', False)

			if is_gallery:
				folder = os.path.join(save_folder, title)
				mkdir(folder)

				i = 0
				for media_id, ext in data['media_ext'].items():
					url_filename = media_id + '.' + ext
					url = IMAGE_URI + url_filename
					res = await download_art(
						session, url, folder, url_filename, f'{parsed.id}/{media_id} - {i}'
					)
					stats.update({res.value: 1})
					i += 1

				if cached is None:
					cache.insert(SLUG, parsed.id, 'gallery')
			elif data['is_video'] is True:
				logger.verbose('skip video', url, progress=progress)
				cache.insert(SLUG, parsed.id, SKIP_CACHE_TAG)
				cache.delete(SLUG, parsed.id + DATA_CACHE_POSTFIX)
				stats.update(skip_video=1)
			else:
				url = data['url']
				url_filename = urlparse(url).path.lstrip('/')
				if cached is None:
					cache.insert(SLUG, parsed.id, 'image')

				media_id, ext = os.path.splitext(url_filename)
				filename = sep.join([title, media_id]) + ext
				mkdir(save_folder)
				res = await download_art(
					session, url, save_folder, filename, f'{parsed.id}/{media_id}'
				)
				stats.update({res.value: 1})

	logger.info(counter2str(stats))
