.DEFAULT_GOAL := all

.PHONY: install
install:
	pip install -U setuptools pip==18.1 pipenv==2018.10.9
	pipenv sync
	pip install -U .

.PHONY: isort
isort:
	isort -rc -w 120 argantic
	isort -rc -w 120 tests

.PHONY: lint
lint:
	python setup.py check -rms
	flake8 argantic/ tests/
	pytest argantic -p no:sugar -q

.PHONY: test
test:
	pytest --cov=argantic

.PHONY: mypy
mypy:
	mypy --ignore-missing-imports --follow-imports=skip --strict-optional -p argantic

.PHONY: testcov
testcov:
	pytest --cov=argantic
	@echo "building coverage html"
	@coverage html

.PHONY: all
all: testcov mypy lint

#.PHONY: benchmark-all
#benchmark-all:
#	python benchmarks/run.py
#
#.PHONY: benchmark-argantic
#benchmark-argantic:
#	python benchmarks/run.py argantic-only

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	python setup.py clean
	make -C docs clean

#.PHONY: docs
#docs:
#	make -C docs html
#
#.PHONY: publish
#publish: docs
#	cd docs/_build/ && cp -r html site && zip -r site.zip site
#	@curl -H "Content-Type: application/zip" -H "Authorization: Bearer ${NETLIFY}" \
#	      --data-binary "@docs/_build/site.zip" https://api.netlify.com/api/v1/sites/argantic-docs.netlify.com/deploys
