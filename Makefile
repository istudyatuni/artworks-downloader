check: isort-check yapf-check mypy

format: isort yapf

isort:
	isort art_dl

yapf:
	python -m yapf -i -r art_dl

isort-check:
	isort art_dl --check

yapf-check:
	python -m yapf --diff -r art_dl

mypy:
	mypy -m art_dl
