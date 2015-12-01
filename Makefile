SHELL:=/bin/bash

pypi: clean
	python3 setup.py bdist_wheel --universal
	for f in dist/*.whl ; do \
	    gpg --detach-sign -a $$f; \
	done
	python3 setup.py register
	twine upload dist/*.{whl,asc}

clean:
	rm -rf dist/*.{whl,asc}

.PHONY: pypi clean
