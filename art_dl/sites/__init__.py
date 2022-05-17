from importlib import import_module
from typing import Any, Callable, Coroutine

MODULE = 'art_dl.sites.'


def download(slug: str) -> Callable[[list[str], str], Coroutine[Any, Any, None]]:
	return import_module(MODULE + slug).download


def register(slug: str) -> Callable[[], None]:
	return import_module(MODULE + slug).register
