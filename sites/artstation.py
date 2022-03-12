import aiohttp
import aiofiles
import os
from urllib.parse import urlparse
from functools import reduce

BASE_URL = 'https://www.artstation.com'
USER_PROJECTS_URL = '/users/{user}/projects.json'
PROJECT_INFO_URL = '/projects/{hash}.json'

def parse_link(url: str):
	parsed = urlparse(url)

	if parsed.path.startswith('/artwork/'):
		# https://www.artstation.com/artwork/<hash>
		return { 'type': 'art', 'project': parsed.path.split('/')[-1] }

	# https://www.artstation.com/<artist>
	return { 'type': 'all', 'artist': parsed.path.lstrip('/') }

async def list_projects(session: aiohttp.ClientSession, user: str):
	async with session.get(USER_PROJECTS_URL.format(user=user)) as response:
		return (await response.json())['data']

async def fetch_project(session: aiohttp.ClientSession, project):
	if isinstance(project, str):
		project_hash = project
	else:
		project_hash = project['hash_id']

	async with session.get(PROJECT_INFO_URL.format(hash=project_hash)) as response:
		print('Add to queue: project', project_hash)
		return (await response.json())

async def fetch_asset(session: aiohttp.ClientSession, asset, save_folder, project = ''):
	print_level_prefix = ' ' * 2

	if asset['has_image'] is False:
		return

	# https://cdna.artstation.com/p/assets/images/images/path/to/file.jpg?1593595729 -> .jpg
	file_ext = os.path.splitext(urlparse(asset['image_url']).path.split('/')[-1])[1]
	sep = ' - '
	name = sep.join([
		asset['title'],
		# if project is not empty, in collection only 1 image
		# project name written to file name
		project,
		str(asset['id']) + file_ext
	]).strip(sep).replace(sep * 2, sep)
	filename = os.path.join(save_folder, name)

	if os.path.exists(filename):
		return print(print_level_prefix + 'Skip existing:', name)

	async with session.get(asset['image_url']) as response:
		if response.ok:
			async with aiofiles.open(filename, 'wb') as file:
				await file.write(await response.read())
			print(print_level_prefix + 'Download:', name)

async def download(url: str, data_folder: str):
	projects = []
	parsed = parse_link(url)

	async with aiohttp.ClientSession(BASE_URL) as session:
		if parsed['type'] == 'all':
			artist = parsed['artist']
			print('Artist', artist)

			# fetch info about all projects
			for project in await list_projects(session, artist):
				projects.append(await fetch_project(session, project))
		else:
			# about specified project
			p = await fetch_project(session, parsed['project'])
			projects.append(p)

			artist = p['user']['username']
			print('Artist', artist)

	save_folder = os.path.join(data_folder, artist)
	os.makedirs(save_folder, exist_ok=True)

	print(
		'Saving to folder',
		save_folder,
		'\n\nStarted download:',
		len(projects),
		'albums and',
		# count all 'assets' arrays lengths from projects
		reduce(lambda a, b: a + len(b), [p['assets'] for p in projects], 0),
		'assets\n'
	)

	# download assets
	async with aiohttp.ClientSession() as session:
		for project in projects:
			sub = f"{project['title']} - {project['hash_id']}"
			assets = project['assets']
			print('Download album:', sub)

			if len(assets) > 1:
				# if count of attacments more than 1, save to subfolder
				sub_folder = os.path.join(save_folder, sub)
				os.makedirs(sub_folder, exist_ok=True)

				for asset in assets:
					await fetch_asset(session, asset, sub_folder)
			elif len(assets) == 1:
				await fetch_asset(session, assets[0], save_folder, sub)
