test:
	tox

clean:
	find -regex '.*\.pyc' -exec rm {} \;
	find -regex '.*~' -exec rm {} \;
	rm -rf reg-settings.py
	rm -rf MANIFEST dist build *.egg-info
	rm -rf rows.1
	rm -rf .tox

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

man:
	head -1 rows.1.txt > rows.1
	txt2man rows.1.txt | egrep -v '^\.TH' >> rows.1

release:
	python setup.py bdist bdist_wheel bdist_egg upload

.PHONY:	test clean lint lint-tests install uninstall man release
