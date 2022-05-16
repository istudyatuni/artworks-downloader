from aiofiles import open as aopen
from aiohttp import ClientSession

from art_dl.utils.cleanup import cleanup


async def download_binary(session: ClientSession, url: str, filename: str):
	async with session.get(url, raise_for_status=True) as response:
		cleanup.set(filename)
		async with aopen(filename, 'wb') as file:
			try:
				await file.write(await response.read())
				cleanup.forget()
			except:
				cleanup.clean()
				print('REMOVING EMPTY FILE')
				raise
