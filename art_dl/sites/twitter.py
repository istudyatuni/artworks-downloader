import os.path
from collections import Counter, namedtuple
from enum import Enum
from urllib.parse import unquote, urlparse

from lxml import etree

from art_dl.cache import cache
from art_dl.log import Logger, Progress
from art_dl.utils.download import download_binary
from art_dl.utils.path import filename_normalize, filename_shortening, mkdir
from art_dl.utils.print import counter2str
from art_dl.utils.proxy import ClientSession, ProxyClientSession

SLUG = 'twitter'
BASE_URL = 'https://nitter.net'
COOKIES = {
	# hide replies and images in replies
	'hideReplies': 'on',
	# just reduce response a little
	'hideTweetStats': 'on',
}

Parsed = namedtuple('Parsed', ['id', 'account', 'path'], defaults=[None, None, None])

logger = Logger(prefix=[SLUG, 'download'], inline=True)
progress = Progress()


class DownloadResult(str, Enum):
	download = 'download'
	skip = 'skip'


def parse_link(url: str) -> Parsed:
	parsed = urlparse(url)
	original_path = parsed.path
	path = original_path.lstrip('/').split('/')

	if len(path) > 2 and path[1] == 'status':
		# https://(mobile.)twitter.com/<account>/status/<id>
		return Parsed(path[2], path[0], original_path)

	return Parsed()


async def fetch_info(session: ClientSession, parsed: Parsed):
	logger.info('fetch info', f'{parsed.account}/{parsed.id}', progress=progress)
	# wait for api: https://github.com/zedeus/nitter/issues/192
	async with session.get(parsed.path) as response:
		data = await response.text()

	root = etree.HTML(data)
	description = root.xpath('//meta[@property=\'og:description\']/@content')[0]
	images_urls = root.xpath(
		'//div[@class="attachments"]/div/div[@class="attachment image"]/a/@href'
	)

	return {
		'description': description,
		# save original url (non unquoted) bc when make request like /pic/media/...?name=orig
		# it will return not original image, but if make request /pic/media%2F...%3Fname%3Dorig
		# it will return original image
		'images': [{
			'url': i,
			'ext': os.path.splitext(urlparse(unquote(i)).path)[1],
		} for i in images_urls],
		'count': len(images_urls),
	}


async def download_image(
	session: ClientSession, url: str, save_folder: str, name: str, log_info: str
) -> DownloadResult:
	filename = os.path.join(save_folder, name)
	if os.path.exists(filename):
		logger.verbose('skip existing', log_info, progress=progress)
		return DownloadResult.skip

	logger.info('download', log_info, progress=progress)
	await download_binary(session, url, filename)
	return DownloadResult.download


async def download(urls: list[str], data_folder: str):
	stats = Counter()  # type: ignore
	progress.total = len(urls)
	sep = ' - '

	async with ProxyClientSession(BASE_URL, cookies=COOKIES) as session:
		for url in urls:
			progress.i += 1

			parsed = parse_link(url)
			if parsed.id is None:
				logger.warn('unsupported link:', url)
				stats.update(skip=1)
				continue

			cache_key = parsed.account + ':' + parsed.id
			cached: dict = cache.select(SLUG, cache_key, as_json=True)

			if cached is None:
				info = await fetch_info(session, parsed)
				cache.insert(SLUG, cache_key, info, as_json=True)
			else:
				info = cached

			title_prefix = sep.join([parsed.account, parsed.id, info['description']]).strip(sep)
			# 245 = 255 - len('.xxxx') - len(' - xx')
			title_prefix = filename_shortening(filename_normalize(title_prefix), 245)
			add_index = (info['count']) > 1

			save_folder = os.path.join(data_folder, parsed.account)
			mkdir(save_folder)

			i = 0
			for image in info['images']:
				filename = (title_prefix + sep + str(i)) if add_index else title_prefix
				filename += image['ext']
				i += 1

				log_info = f'{parsed.account}/{parsed.id}'
				if add_index:
					log_info += sep + str(i)
				res = await download_image(session, image['url'], save_folder, filename, log_info)
				stats.update({res.value: 1})

	logger.info(counter2str(stats))
