.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help
define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts


clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -not -path "./env/*" -exec rm -fr {} +
	find . -name '*.egg' -not -path "./env/*" -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -not -path "./env/*" -exec rm -f {} +
	find . -name '*.pyo' -not -path "./env/*" -exec rm -f {} +
	find . -name '*~' -not -path "./env/*" -exec rm -f {} +
	find . -name '__pycache__' -not -path "./env/*" -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

lint: ## check style with flake8
	flake8 stackformation tests

test: ## run tests quickly with the default Python
	py.test
	

test-all: ## run tests on every Python version with tox
	tox

__coverage: ## check code coverage quickly with the default Python
	coverage run --source stackformation -m pytest
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

flake8: ## Run flake8 check ( Docker )
	docker build -f Dockerfile-test -t stackformation:test .
	docker run --rm -it -u $(shell id -u):$(shell id -g) \
		-v /etc/passwd:/etc/passwd \
		-v $(shell pwd):$(shell pwd) -w \
		$(shell pwd) stackformation:test flake8 stackformation/

coverage-term: clean flake8 ## test coverage terminal report ( Docker )
	docker build -f Dockerfile-test -t stackformation:test .
	docker run --rm -it -u $(shell id -u):$(shell id -g) \
		-v /etc/passwd:/etc/passwd \
		-v $(shell pwd):$(shell pwd) -w \
		$(shell pwd) stackformation:test python3 setup.py covterm

coverage-html: clean flake8 ## test coverage html report ( Docker )
	docker build -f Dockerfile-test -t stackformation:test .
	docker run --rm -it -u $(shell id -u):$(shell id -g) \
		-v /etc/passwd:/etc/passwd \
		-v $(shell pwd):$(shell pwd) -w \
		$(shell pwd) stackformation:test python3 setup.py covhtml
	$(BROWSER) htmlcov/index.html

docker-build-dev: ## Build the Dockerfile-dev tagged: stackformation:dev
	docker build -f Dockerfile-dev -t stackformation:dev .

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/stackformation.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ stackformation
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: clean ## package and upload a release
	python setup.py sdist upload
	python setup.py bdist_wheel upload

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install
