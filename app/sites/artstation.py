from collections import defaultdict, namedtuple
from functools import reduce
from urllib.parse import urlparse
import aiofiles
import aiohttp
import os

from app.utils import mkdir

BASE_URL = 'https://www.artstation.com'
USER_PROJECTS_URL = '/users/{user}/projects.json'
PROJECT_INFO_URL = '/projects/{hash}.json'

Project = namedtuple('Project', ['title', 'hash_id', 'assets'])

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
		print('Add to queue: artwork', project_hash)
		return (await response.json())

async def fetch_asset(session: aiohttp.ClientSession, asset, save_folder, project = None):
	print_level_prefix = ' ' * 2

	if asset['has_image'] is False:
		return

	# https://cdna.artstation.com/p/assets/images/images/path/to/file.jpg?1593595729 -> .jpg
	file_ext = os.path.splitext(urlparse(asset['image_url']).path.split('/')[-1])[1]
	sep = ' - '
	name = sep.join([
		asset['title'] or '',
		# if project is not empty, in collection only 1 image
		# project name written to file name
		project or '',
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

async def download(urls: list[str], data_folder: str):
	# { '<artist>': [Project(1), ...] }
	projects: dict[str, list[Project]] = defaultdict(list)

	for url in urls:
		parsed = parse_link(url)

		async with aiohttp.ClientSession(BASE_URL) as session:
			if parsed['type'] == 'all':
				artist = parsed['artist']

				# fetch info about all projects
				for project in await list_projects(session, artist):
					p = await fetch_project(session, project)
					projects[artist].append(Project(p['title'], p['hash_id'], p['assets']))
			elif parsed['type'] == 'art':
				# about specified project
				p = await fetch_project(session, parsed['project'])
				name = p['user']['username']
				projects[name].append(Project(p['title'], p['hash_id'], p['assets']))

	print('\nSaving to folder', data_folder)
	for artist in projects.keys():
		mkdir(os.path.join(data_folder, artist))

	print(
		'Started download',
		# summary length of all arrays in projects
		reduce(lambda a, b: a + len(b), projects.values(), 0),
		'albums and',
		# sum all 'assets' arrays lengths from projects
		sum(
			reduce(lambda a, b: a + len(b.assets), p, 0)
			for p in projects.values()
		),
		'assets'
	)

	# download assets
	async with aiohttp.ClientSession() as session:
		for artist, projects_list in projects.items():
			print('\nArtist', artist)
			for project in projects_list:
				save_folder = os.path.join(data_folder, artist)
				sub = f"{project.title} - {project.hash_id}"
				assets = project.assets
				print('Download album:', sub)

				if len(assets) > 1:
					# if count of attachments more than 1, save to sub-folder
					sub_folder = os.path.join(save_folder, sub)
					mkdir(sub_folder)

					for asset in assets:
						await fetch_asset(session, asset, sub_folder)
				elif len(assets) == 1:
					await fetch_asset(session, assets[0], save_folder, sub)
