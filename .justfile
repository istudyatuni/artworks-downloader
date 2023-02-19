[private]
default:
	just --list

# run checks
check: isort-check yapf-check mypy

# format all
format: isort yapf

[private]
isort:
	isort art_dl

[private]
yapf:
	python -m yapf -i -r art_dl

[private]
isort-check:
	isort art_dl --check

[private]
yapf-check:
	python -m yapf --diff -r art_dl

[private]
mypy:
	mypy -m art_dl
