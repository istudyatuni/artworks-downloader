from importlib import import_module
from typing import Any, Callable, Coroutine

MODULE = 'app.sites.'

def download(slug: str) -> Callable[[list[str] | str, str], Coroutine[Any, Any, None]]:
	return import_module(MODULE + slug).download

def register(slug: str) -> Callable[[], dict[str, Any] | None]:
	return import_module(MODULE + slug).register
