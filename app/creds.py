from json import dump, load
from os.path import exists
from typing import Any

CRED_FILE = 'credentials.json'

def get_creds():
	if exists(CRED_FILE):
		with open(CRED_FILE) as file:
			return load(file)
	return None

def save_creds(obj: dict[str, Any]):
	if (creds := get_creds()) is not None:
		data = {**creds, **obj}
	else:
		data = {**obj}

	with open(CRED_FILE, 'w') as file:
		dump(data, file)
