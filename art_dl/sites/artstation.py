import os.path
from collections import Counter, defaultdict, namedtuple
from enum import Enum
from functools import reduce
from urllib.parse import urlparse

from art_dl.cache import cache
from art_dl.log import Logger, Progress
from art_dl.utils.download import download_binary
from art_dl.utils.path import mkdir
from art_dl.utils.print import counter2str
from art_dl.utils.proxy import ClientSession, ProxyClientSession

SLUG = 'artstation'
BASE_URL = 'https://www.artstation.com'
USER_PROJECTS_URL = '/users/{user}/projects.json'
PROJECT_INFO_URL = '/projects/{hash}.json'

logger = Logger(inline=True)
progress = Progress()

Project = namedtuple('Project', ['title', 'hash_id', 'assets'])


class DownloadResult(str, Enum):
	download = 'download'
	no_image = 'no_image'
	skip = 'skip'


def parse_link(url: str):
	parsed = urlparse(url)

	if parsed.path.startswith('/artwork/'):
		# https://www.artstation.com/artwork/<hash>
		return {
			'type': 'art',
			'project': parsed.path.split('/')[-1]
		}

	# https://www.artstation.com/<artist>
	return {
		'type': 'all',
		'artist': parsed.path.lstrip('/')
	}


async def list_projects(session: ClientSession, user: str):
	async with session.get(USER_PROJECTS_URL.format(user=user)) as response:
		return (await response.json())['data']


async def fetch_project(session: ClientSession, project: str):
	async with session.get(PROJECT_INFO_URL.format(hash=project)) as response:
		logger.info('add', project, progress=progress)
		result = await response.json()

	return {
		'assets': list({
			'has_image': a['has_image'],
			'id': a['id'],
			'image_url': a['image_url'],
			'title': a['title'],
		} for a in result['assets']),
		'hash_id': result['hash_id'],
		'title': result['title'],
		'user': {
			'username': result['user']['username']
		},
	}


async def fetch_asset(
	session: ClientSession,
	project_hash: str,
	asset,
	save_folder,
	project_prefix=None
) -> DownloadResult:
	if asset['has_image'] is False:
		logger.info('no image', project_hash)
		return DownloadResult.no_image

	asset_id = asset['id']
	# https://cdna.artstation.com/p/assets/images/images/path/to/file.jpg?1593595729 -> .jpg
	file_ext = os.path.splitext(urlparse(asset['image_url']).path.split('/')[-1])[1]
	sep = ' - '
	name = sep.join([
		asset['title'] or '',
		# if project_prefix is not empty, in collection only 1 image
		# project name written to file name
		project_prefix or '',
		str(asset_id) + file_ext
	]).strip(sep).replace(sep * 2, sep)
	filename = os.path.join(save_folder, name)

	if os.path.exists(filename):
		logger.verbose('skip existing', project_hash, asset_id, progress=progress)
		return DownloadResult.skip

	logger.info('download', project_hash, asset_id, progress=progress)
	await download_binary(session, asset['image_url'], filename)
	return DownloadResult.download


async def download(urls: list[str], data_folder: str):
	stats = Counter()  # type: ignore
	progress.total = len(urls)

	# { '<artist>': [Project(1), ...] }
	projects: dict[str, list[Project]] = defaultdict(list)

	logger.configure(prefix=[SLUG, 'queue'], inline=True)
	for url in urls:
		progress.i += 1

		parsed = parse_link(url)

		async with ProxyClientSession(BASE_URL) as session:
			if parsed['type'] == 'all':
				artist = parsed['artist']
				projects_list = await list_projects(session, artist)
				stats.update(artist=1)
			elif parsed['type'] == 'art':
				projects_list = [parsed['project']]
				stats.update(art=1)
			else:
				# this should never be called
				logger.verbose('error parsing')
				continue

			for project in projects_list:
				if isinstance(project, str):
					project_hash = project
				else:
					project_hash = project['hash_id']

				cached: dict = cache.select(SLUG, project_hash, as_json=True)
				if cached is None:
					p = await fetch_project(session, project_hash)
					cache.insert(SLUG, project_hash, p, as_json=True)
				else:
					p = cached

				artist = p['user']['username']
				projects[artist].append(Project(p['title'], p['hash_id'], p['assets']))

	for artist in projects.keys():
		mkdir(os.path.join(data_folder, artist))

	logger.info(counter2str(stats), end='\n')

	# download assets
	logger.configure(prefix=[SLUG, 'download'], inline=True)
	stats = Counter()
	progress.i = 0
	progress.total = sum(reduce(lambda a, b: a + len(b.assets), p, 0) for p in projects.values())
	async with ProxyClientSession() as session:
		for artist, projects_list in projects.items():
			for project in projects_list:
				save_folder = os.path.join(data_folder, artist)
				sub = f"{project.title} - {project.hash_id}"

				if len(project.assets) > 1:
					# save to sub-folder
					save_folder = os.path.join(save_folder, sub)
					mkdir(save_folder)
					# do not append 'sub' to files names in sub-folder
					sub = None  # type: ignore

				for asset in project.assets:
					progress.i += 1

					res = await fetch_asset(session, project.hash_id, asset, save_folder, sub)
					stats.update({res.value: 1})

	logger.configure(prefix=[SLUG], inline=True)
	logger.info(counter2str(stats))
