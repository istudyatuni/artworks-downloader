# from aiohttp import ClientSession
import os.path
from collections import Counter, defaultdict
from glob import glob
from typing import Any
from urllib.parse import urlparse

from art_dl.cache import cache
from art_dl.sites.deviantart.common import SLUG, make_cache_key
from art_dl.utils.download import download_binary
from art_dl.utils.path import mkdir
from art_dl.utils.print import counter2str
from art_dl.utils.proxy import ClientSession, ProxyClientSession

from .common import logger, progress
from .service import DAService


def parse_link(url: str) -> dict[str, str]:
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')
	artist = path[0]

	if len(path) == 1 or (len(path) > 2 and path[2] == 'all'):
		# https://www.deviantart.com/<artist>
		# https://www.deviantart.com/<artist>/gallery/all
		return {
			'type': 'all',
			'artist': artist
		}

	if len(path) == 2 and path[1] == 'gallery':
		# https://www.deviantart.com/<artist>/gallery
		# it's "Featured" collection
		return {
			'type': 'folder',
			'folder': 'featured',
			'artist': artist
		}

	if path[1] == 'gallery':
		# https://www.deviantart.com/<artist>/gallery/<some number>/<gallery name>
		# gallery name in format one-two-etc
		return {
			'type': 'folder',
			'folder': path[3],
			'artist': artist
		}

	if path[1] == 'art':
		# https://www.deviantart.com/<artist>/art/<name>
		return {
			'type': 'art',
			'url': url,
			'artist': artist,
			'name': path[2]
		}

	return {
		'type': 'unknown',
		'artist': artist
	}


# download images


async def save_from_url(session: ClientSession, url: str, folder: str, name: str):
	ext = os.path.splitext(urlparse(url).path)[1]
	filename = os.path.join(folder, name + ext)
	if os.path.exists(filename):
		return logger.info('skip existing file', name, progress=progress)

	logger.info('download file', name, progress=progress)
	await download_binary(session, url, filename)


async def save_art(service: DAService, session: ClientSession, art: Any, folder: str):
	url: str = art['url']
	name = url.rsplit('/', 1)[-1]

	if (premium_folder_data := art.get('premium_folder_data')) is not None:
		if premium_folder_data['has_access'] is False:
			logger.warn('no access to', name + ',', 'downloading preview', progress=progress)

	if art['is_downloadable'] is False or art['download_filesize'] == art['content']['filesize']:
		return await save_from_url(session, art['content']['src'], folder, name)

	original_url = await service.get_download(art['deviationid'])
	if original_url is not None:
		await save_from_url(session, original_url, folder, name)


# wrappers for common actions


async def download_folder_by_id(service: DAService, save_folder: str, artist: str, folder_id: str):
	# this session for downloading images
	async with ProxyClientSession() as session:
		async for art in service.list_folder_arts(artist, folder_id):
			await save_art(service, session, art, save_folder)


async def download_art_by_id(service: DAService, deviationid: str, folder: str):
	art = await service.get_art_info(deviationid)
	async with ProxyClientSession() as session:
		await save_art(service, session, art, folder)


# helpers


def is_art_exists(folder: str, artist: str, name: str):
	return len(glob(f'{folder}/{artist}/{name}.*')) > 0


# main functions


async def download(urls: list[str], data_folder: str):
	stats = Counter()  # type: ignore
	progress.total = len(urls)

	service = DAService()

	# ['artist1', ...]
	mapping_all: list[str] = []
	# { '<artist>': ['folder1', ...] }
	mapping_folder: dict[str, list[str]] = defaultdict(list)
	# { '<artist>': [{ 'name': 'name1', 'url': 'url1' }, ...] }
	mapping_art: dict[str, list[dict[str, str]]] = defaultdict(list)

	# group urls by types and artists
	for u in urls:
		parsed = parse_link(u)
		t = parsed['type']
		a = parsed['artist']
		if t == 'all':
			mapping_all.append(a)
		elif t == 'folder':
			mapping_folder[a].append(parsed['folder'])
		elif t == 'art':
			n = parsed['name']
			if is_art_exists(data_folder, a, n):
				stats.update(skip=1)
				progress.i += 1

				logger.info('skip existing', a + '/' + n, progress=progress)
				continue

			deviationid = cache.select(SLUG, make_cache_key(a, u))
			if deviationid is not None:
				stats.update(download=1)
				progress.i += 1

				logger.info('download cached', a + '/' + n, progress=progress)
				save_folder = os.path.join(data_folder, a)
				mkdir(save_folder)
				await download_art_by_id(service, deviationid, save_folder)
				continue

			mapping_art[a].append({
				'name': n,
				'url': u
			})
		elif t == 'unknown':
			stats.update(skip=1)
			progress.i += 1

			logger.warn('unsupported link', u, progress=progress)
			continue

	# process

	# save artists all arts
	for artist in mapping_all:
		stats.update(download=1)
		progress.i += 1

		save_folder = os.path.join(data_folder, artist)
		mkdir(save_folder)
		logger.info('artist', artist, progress=progress)

		await download_folder_by_id(service, save_folder, artist, 'all')

	# save collections
	for artist, folder_list in mapping_folder.items():
		stats.update(download=1)
		progress.i += 1

		save_folder = os.path.join(data_folder, artist)
		mkdir(save_folder)
		logger.info('artist', artist, progress=progress)

		async for folder in service.list_folders(artist):
			if folder['name'] in folder_list:
				logger.info('gallery', folder['pretty_name'], progress=progress)
				await download_folder_by_id(service, save_folder, artist, folder['id'])

	# save single arts
	async with ProxyClientSession() as session:
		for artist, art_list in mapping_art.items():
			progress.i += 1

			all_urls = set(map(lambda a: a['url'], art_list))

			save_folder = os.path.join(data_folder, artist)
			mkdir(save_folder)
			logger.info('artist', artist, progress=progress)

			async for art in service.list_folder_arts(artist, 'all'):
				url = art['url']
				if any(filter(lambda a: a['url'] == url, art_list)):  # type: ignore
					await save_art(service, session, art, save_folder)

					all_urls.remove(url)
					if len(all_urls) == 0:
						break

			if len(all_urls) > 0:
				stats.update(partial_download=1)
				logger.warn('not found', len(all_urls), f'arts ({artist}):', progress=progress)
				for u in all_urls:
					logger.warn(' ', u)
			else:
				stats.update(download=1)

	logger.info(counter2str(stats))
