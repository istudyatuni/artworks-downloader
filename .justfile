[private]
default:
	just --list --unsorted

format:
	cargo fmt

clippy:
	cargo clippy

# generate doc
doc:
	cargo doc --document-private-items --no-deps

# generate and open doc
doc-open:
	cargo doc --document-private-items --no-deps --open
