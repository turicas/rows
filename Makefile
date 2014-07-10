test:
	nosetests -dsv --with-yanc --with-coverage --cover-package rows tests/*.py

clean:
	find -regex '.*\.pyc' -exec rm {} \;
	find -regex '.*~' -exec rm {} \;
	rm -rf reg-settings.py
	rm -rf MANIFEST dist build *.egg-info

lint:
	pylint rows/*.py

lint-tests:
	pylint tests/*.py

.PHONY:	test clean lint lint-tests
