from aiofiles import open as aopen
from aiohttp import ClientSession
from os import remove

async def download_binary(session: ClientSession, url: str, filename: str):
	async with session.get(url, raise_for_status=True) as response:
		async with aopen(filename, 'wb') as file:
			try:
				await file.write(await response.read())
			except:
				remove(filename)
				print('REMOVING EMPTY FILE')
				raise
