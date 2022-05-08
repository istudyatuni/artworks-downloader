check: mypy

mypy:
	mypy -m art_dl

requirements: requirements.txt
	pip install -r requirements.txt

requirements-dev: requirements.txt requirements.dev.txt
	pip install -r requirements.dev.txt
