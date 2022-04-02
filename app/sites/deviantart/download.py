from collections import defaultdict
import aiofiles
import aiohttp
import os
from glob import glob
from typing import Any
from urllib.parse import urlparse

import app.cache as cache
from app.sites.deviantart.common import SLUG, make_cache_key
from .service import DAService
from app.utils.path import mkdir

def parse_link(url: str) -> dict[str, str]:
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')
	artist = path[0]

	if len(path) == 1 or (len(path) > 2 and path[2] == 'all'):
		# https://www.deviantart.com/<artist>
		# https://www.deviantart.com/<artist>/gallery/all
		return { 'type': 'all', 'artist': artist }

	if len(path) == 2 and path[1] == 'gallery':
		# https://www.deviantart.com/<artist>/gallery
		# it's "Featured" collection
		return { 'type': 'folder', 'folder': 'featured', 'artist': artist }

	if path[1] == 'gallery':
		# https://www.deviantart.com/<artist>/gallery/<some number>/<gallery name>
		# gallery name in format one-two-etc
		return { 'type': 'folder', 'folder': path[3], 'artist': artist }

	if path[1] == 'art':
		# https://www.deviantart.com/<artist>/art/<name>
		return { 'type': 'art', 'url': url, 'artist': artist, 'name': path[2] }

	print('Unsupported link:', url)
	return { 'type': 'unknown', 'artist': artist }

# download images

async def save_from_url(session: aiohttp.ClientSession, url: str, folder: str, name: str):
	ext = os.path.splitext(urlparse(url).path)[1]
	path = os.path.join(folder, name + ext)
	if os.path.exists(path):
		return print(' ', 'Skip existing:', name)

	async with session.get(url) as image:
		async with aiofiles.open(path, 'wb') as file:
			await file.write(await image.read())
			print(' ', 'Download:', name)

async def save_art(
	service: DAService,
	session: aiohttp.ClientSession,
	art: Any,
	folder: str
):
	name = art['url'].split('/')[-1]

	if (premium_folder_data := art.get('premium_folder_data')) is not None:
		if premium_folder_data['has_access'] is False:
			print('  No access to', name + ':', 'downloading preview')

	if (
		art['is_downloadable'] is False or
		art['download_filesize'] == art['content']['filesize']
	):
		return await save_from_url(session, art['content']['src'], folder, name)

	original_url = await service.get_download(art['deviationid'])
	if original_url is not None:
		await save_from_url(session, original_url, folder, name)

# wrappers for common actions

async def download_folder_by_id(
	service: DAService,
	save_folder: str,
	artist: str,
	folder: str
):
	# this session for downloading images
	async with aiohttp.ClientSession() as session:
		async for art in service.list_folder_arts(artist, folder):
			await save_art(service, session, art, save_folder)

async def download_art_by_id(service: DAService, deviationid: str, folder: str):
	art = await service.get_art_info(deviationid)
	async with aiohttp.ClientSession() as session:
		await save_art(service, session, art, folder)

# helpers

def is_art_exists(folder: str, artist: str, name: str):
	return len(glob(f'{folder}/{artist}/{name}.*')) > 0

# main functions

async def download(urls: list[str], data_folder: str):
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
				print('Skip existing:', a + '/' + n)
				continue

			deviationid = cache.select(SLUG, make_cache_key(a, u))
			if deviationid is not None:
				print('Download cached:', a + '/' + n)
				save_folder = os.path.join(data_folder, a)
				mkdir(save_folder)
				await download_art_by_id(service, deviationid, save_folder)
				continue

			mapping_art[a].append({ 'name': n, 'url': u })

	# process

	# save artists all arts
	for artist in mapping_all:
		save_folder = os.path.join(data_folder, artist)
		mkdir(save_folder)
		print('\nArtist', artist)

		await download_folder_by_id(service, save_folder, artist, 'all')

	# save collections
	for artist, folder_list in mapping_folder.items():
		save_folder = os.path.join(data_folder, artist)
		mkdir(save_folder)
		print('\nArtist', artist)

		async for folder in service.list_folders(artist):
			if folder['name'] in folder_list:
				print('Gallery', folder['pretty_name'])
				await download_folder_by_id(service, save_folder, artist, folder['id'])

	# save single arts
	async with aiohttp.ClientSession() as session:
		for artist, art_list in mapping_art.items():
			all_urls = set(map(lambda a: a['url'], art_list))

			save_folder = os.path.join(data_folder, artist)
			mkdir(save_folder)
			print('\nArtist', artist)

			async for art in service.list_folder_arts(artist, 'all'):
				url = art['url']
				if any(filter(lambda a: a['url'] == url, art_list)):
					await save_art(service, session, art, save_folder)

					all_urls.remove(url)
					if len(all_urls) == 0:
						break

			if len(all_urls) > 0:
				print('Not found', len(all_urls), 'arts (' + artist + '):')
				for u in all_urls:
					print(' ', u)
