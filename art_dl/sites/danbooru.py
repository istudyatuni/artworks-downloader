'''https://danbooru.donmai.us/wiki_pages/help:api'''
from art_dl.utils.proxy import ClientSession, ProxyClientSession


async def fetch_smth(session: ClientSession, url: str):
	async with session.get(url) as response:
		print(response)


async def download(urls: list[str], data_folder: str):
	async with ProxyClientSession() as session:
		for url in urls:
			await fetch_smth(session, url)
