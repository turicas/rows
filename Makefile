MAKEFLAGS += --always-make
PYTHON_VERSIONS = 27 35 36 37 38 39 310 311 312 313 debian
TEST_PY_TARGETS = $(foreach version, $(PYTHON_VERSIONS), test-py$(version))
BUILD_PY_TARGETS = $(foreach version, $(PYTHON_VERSIONS), build-py$(version))
TAGS_FILE = .tags

help:					# List all make commands
	@awk -F ':.*#' '/^[a-zA-Z_-]+:.*?#/ { printf "\033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

test-local:						# Run tests on host machine (not inside containers)
	python -m coverage run -m pytest $(TEST_ARGS) && python -m coverage report

test-all: $(TEST_PY_TARGETS)	# Run tests on for all Python versions

	@echo "Running tests for all Python versions"

build-py%:						# Build the container for a specific Python version
	@echo "Running py$*"
	docker compose build py$*

test-py%:						# Run tests inside a container for a specific Python version
	@echo "Running tests for py$*"
	@COMPOSE_PROFILES=py$* docker compose run --rm -it py$* bash -c "python -m coverage run -m pytest $(TEST_ARGS) && python -m coverage report"

py%:							# Run Python shell inside the container for a specific Python version
	@echo "Running Python shell in version py$*"
	@COMPOSE_PROFILES=py$* docker compose run --rm -it py$* python

bash-py%:						# Run bash inside the container for a specific Python version
	@echo "Running bash in version py$*"
	@COMPOSE_PROFILES=py$* docker compose run --rm -it py$* bash

bash-root-py%:					# Run bash as root inside the container for a specific Python version
	@echo "Running bash in version py$*"
	@COMPOSE_PROFILES=py$* docker compose run --rm -itu root py$* bash

clean:							# Clean temporary files
	rm -f $(TAGS_FILE)
	find -regex '.*\.pyc' -exec rm {} \;
	find -regex '.*~' -exec rm {} \;
	rm -rf reg-settings.py MANIFEST dist build *.egg-info rows.1 .tox
	rm -rf docs-build docs/reference docs/man $(TAGS_FILE)
	python -m coverage erase

fix-imports:					# Run linters
	autoflake --in-place --recursive --remove-unused-variables --remove-all-unused-imports .
	isort .
	black .

install:						# Clean temporary files, uninstall and install (locally) using `pip`
	make clean
	make uninstall
	python setup.py install

uninstall:						# Uninstall the package (locally)
	pip uninstall -y rows

# TODO: move to use black
lint:							# Execute pylint only for package files
	pylint rows/*.py

lint-tests:						# Execute pylint only for test files
	pylint tests/*.py

docs:							# Build the docs
	make clean install
	click-man --target=docs/man/ rows
	pycco --directory=docs/reference --generate_index --skip-bad-files rows/*.py
	pycco --directory=docs/reference/plugins --generate_index --skip-bad-files rows/plugins/*.py
	mkdocs build --strict --site-dir=docs-build
	rm -rf docs/man docs/reference

docs-serve: docs				# Build the docs and serve them in a HTTP server
	cd docs-build && python3 -m http.server

docs-upload: docs				# Build the docs and push to `gh-pages` branch
	-git branch --delete --force --quiet gh-pages
	-git push turicas :gh-pages
	ghp-import --no-jekyll --message="Docs automatically built from $(shell git rev-parse HEAD)" --branch=gh-pages --push --force --remote=turicas docs-build/

release:						# Release a new version on PyPI
	python setup.py bdist bdist_wheel --universal bdist_egg upload

tags:							# Generate tags file for the entire project (requires universal-ctags)
	@git ls-files | ctags -L - --tag-relative=yes --quiet --append -f "$(TAGS_FILE)"

.PHONY: bash-py% bash-root-py% build-py% clean docs docs-serve docs-upload fix-imports help install lint lint-tests py% release tags test-all test-local test-py% uninstall
