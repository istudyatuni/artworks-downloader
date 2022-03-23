import aiofiles
import aiohttp
import os
from glob import glob
from typing import Any
from urllib.parse import urlparse

from .service import DAService
from app.utils import mkdir

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
	print_level_prefix = ' ' * 2

	ext = os.path.splitext(urlparse(url).path)[1]
	path = os.path.join(folder, name + ext)
	if os.path.exists(path):
		return print(print_level_prefix + 'Skip existing:', name)

	async with session.get(url) as image:
		async with aiofiles.open(path, 'wb') as file:
			await file.write(await image.read())
			print(print_level_prefix + 'Download:', name)

async def save_art(service: DAService, session: aiohttp.ClientSession, art: Any, folder: str, name: str):
	if (
		art['is_downloadable'] is False or
		art['download_filesize'] == art['content']['filesize']
	):
		return await save_from_url(session, art['content']['src'], folder, name)

	original_url = await service.get_download(art['deviationid'])
	if original_url is not None:
		await save_from_url(session, original_url, folder, name)

# wrappers for common actions

async def download_folder_by_id(service: DAService, save_folder: str, artist: str, folder: str):
	# this session for downloading images
	async with aiohttp.ClientSession() as session:
		async for art in service.list_folder_arts(artist, folder):
			name = art['url'].split('/')[-1]
			await save_art(service, session, art, save_folder, name)

async def find_and_download_folder(
	service: DAService,
	save_folder: str,
	artist: str,
	folder_name: str
):
	folderid = await search_for_folder(service, artist, folder_name)
	if folderid is None:
		print('Not found gallery', f'"{folder_name}"')
		return
	await download_folder_by_id(service, save_folder, artist, folderid)

async def search_for_folder(service: DAService, artist: str, folder_to_find: str) -> str | None:
	folderid = None
	print('Searching for gallery')
	async for folder in service.list_folders(artist):
		if folder['name'] == folder_to_find:
			folderid = folder['id']
			print('Gallery', folder['pretty_name'], f'({folderid})')
			# not breaking now for catching what is the subfolder
			# break

	return folderid

async def search_for_art(service: DAService, artist: str, url_to_find: str) -> Any:
	print('Searching for art')
	async for art in service.list_folder_arts(artist, 'all'):
		if art['url'] == url_to_find:
			return art

async def find_and_download_art(
	service: DAService,
	save_folder: str,
	artist: str,
	url: str,
	name: str
):
	art = await search_for_art(service, artist, url)
	async with aiohttp.ClientSession() as session:
		await save_art(service, session, art, save_folder, name)

# helpers

def is_exists(folder: str, artist: str, name: str):
	return len(glob(f'{folder}/{artist}/{name}.*')) > 0

# main functions

async def download(url: list[str] | str, data_folder: str) -> None:
	if isinstance(url, list):
		return await download_list(url,data_folder)

	service = DAService()

	parsed = parse_link(url)
	artist = parsed['artist']
	save_folder = os.path.join(data_folder, artist)
	mkdir(save_folder)

	print('Artist', artist)
	print('Saving to folder', save_folder, end='\n\n')

	if parsed['type'] == 'all':
		await download_folder_by_id(service, save_folder, artist, 'all')
	elif parsed['type'] == 'folder':
		await find_and_download_folder(service, save_folder, artist, parsed['folder'])
	elif parsed['type'] == 'art':
		await find_and_download_art(service, save_folder, artist, url, parsed['name'])

async def download_list(urls: list[str], data_folder: str):
	service = DAService()

	print('\nSaving to folder', data_folder)

	# ['artist1', ...]
	mapping_all: list[str] = []
	# { '<artist>': ['folder1', ...] }
	mapping_folder: dict[str, list[str]] = {}
	# { '<artist>': [{ 'name': 'name1', 'url': 'url1' }, ...] }
	mapping_art: dict[str, list[dict[str, str]]] = {}

	# group urls by types and artists
	for u in urls:
		parsed = parse_link(u)
		t = parsed['type']
		a = parsed['artist']
		if t == 'all':
			mapping_all.append(a)
		elif t == 'folder':
			if mapping_folder.get(a) is None:
				mapping_folder[a] = []
			mapping_folder[a].append(parsed['folder'])
		elif t == 'art':
			n = parsed['name']
			if is_exists(data_folder, a, n):
				print('Skip existing:', a + '/' + n)
				continue

			if mapping_art.get(a) is None:
				mapping_art[a] = []
			mapping_art[a].append({ 'name': n, 'url': u })

	# process
	for artist in mapping_all:
		save_folder = os.path.join(data_folder, artist)
		mkdir(save_folder)
		print('\nArtist', artist)

		await download_folder_by_id(service, save_folder, artist, 'all')

	for artist, folder_list in mapping_folder.items():
		save_folder = os.path.join(data_folder, artist)
		mkdir(save_folder)
		print('\nArtist', artist)

		async for folder in service.list_folders(artist):
			if folder['name'] in folder_list:
				print('Gallery', folder['pretty_name'])
				await download_folder_by_id(service, save_folder, artist, folder['id'])

	async with aiohttp.ClientSession() as session:
		for artist, art_list in mapping_art.items():
			arts_count = len(art_list)
			save_folder = os.path.join(data_folder, artist)
			mkdir(save_folder)
			print('\nArtist', artist)

			async for art in service.list_folder_arts(artist, 'all'):
				url = art['url']
				if any(filter(lambda a: a['url'] == url, art_list)):
					name = url.split('/')[-1]
					await save_art(service, session, art, save_folder, name)

					arts_count -= 1
					if arts_count == 0:
						break

			if arts_count > 0:
				print('Not found', arts_count, 'arts, artist', artist)
