from os import remove
import aiofiles
import aiohttp

async def download_binary(session: aiohttp.ClientSession, url: str, filename: str):
	async with session.get(url) as response:
		response.raise_for_status()
		async with aiofiles.open(filename, 'wb') as file:
			try:
				await file.write(await response.read())
			except:
				remove(filename)
				print('REMOVING EMPTY FILE')
				raise
