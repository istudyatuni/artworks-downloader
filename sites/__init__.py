from importlib import import_module

def download(slug: str):
	return import_module('sites.' + slug).download
