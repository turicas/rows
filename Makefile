envtest: clean
	nosetests tests/

test:
	tox

clean:
	find -regex '.*\.pyc' -exec rm {} \;
	find -regex '.*~' -exec rm {} \;
	rm -rf reg-settings.py MANIFEST dist build *.egg-info rows.1 .tox
	rm -rf docs-build docs/reference docs/man
	coverage erase

fix-imports:
	autoflake --in-place --recursive --remove-unused-variables --remove-all-unused-imports .
	isort -rc .
	black .

install:
	make clean
	make uninstall
	python setup.py install

uninstall:
	pip uninstall -y rows

lint:
	pylint rows/*.py

lint-tests:
	pylint tests/*.py

docs:
	make clean install
	click-man --target=docs/man/ rows
	pycco --directory=docs/reference --generate_index --skip-bad-files rows/*.py
	pycco --directory=docs/reference/plugins --generate_index --skip-bad-files rows/plugins/*.py
	mkdocs build --strict --site-dir=docs-build
	rm -rf docs/man docs/reference

docs-serve: docs
	cd docs-build && python3 -m http.server

docs-upload: docs
	-git branch --delete --force --quiet gh-pages
	-git push turicas :gh-pages
	ghp-import --no-jekyll --message="Docs automatically built from $(shell git rev-parse HEAD)" --branch=gh-pages --push --force --remote=turicas docs-build/

release:
	python setup.py bdist bdist_wheel --universal bdist_egg upload

.PHONY:	test clean docs docs-serve docs-upload fix-imports lint lint-tests install uninstall release
