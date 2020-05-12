# Copyright (c) 2020 Machine Zone, Inc. All rights reserved.

all: flake

update_version:
	python tools/compute_version_from_git.py > DOCKER_VERSION

dev: update_version
	@echo "--> Installing Python dependencies"
	# order matters here, base package must install first
	pip install -U pip
	pip install --requirement requirements.txt
	pip install --requirement tests/requirements.txt
	pip install pre-commit
	pre-commit install
	pip install -e .
	pip install "file://`pwd`#egg=rcc[dev]"

upload: update_version
	rm -rf dist/*
	python setup.py sdist bdist_wheel
	twine upload dist/*.whl
	rm -rf build/

lint: flake

indent:
	black -S rcc tests

format: indent

flake:
	flake8 --max-line-length=88 `find rcc -name '*.py'`

test:
	py.test -sv -n 1 --disable-warnings tests/*.py

mypy:
	mypy --ignore-missing-imports rcc/*.py

pylint:
	pylint -E -j 10 -r n -d C0301 -d C0103 -d C0111 -d C0330 -d W1401 -d W1203 -d W1202 `find rcc -name '*.py'`

coverage:
	py.test -n 1 --disable-warnings --cov=rcc --cov-report html --cov-report term tests

isort:
	isort `find rcc tests -name '*.py'`

release:
	git push ; make upload

# this is helpful to remove trailing whitespaces
trail:
	test `uname` = Linux || sed -E -i '' -e 's/[[:space:]]*$$//' `find src tests -name '*.py'`
	test `uname` = Darwin || sed -i 's/[ \t]*$$//' `find src tests -name '*.py'`

#  python -m venv venv
#  source venv/bin/activate
#  pip install mkdocs
doc:
	mkdocs gh-deploy

clean:
	find . -name __pycache__ -delete
	find rcc tests -name '*.pyc' -delete
	rm -f *.pyc
	rm -rf rcc.egg-info
	rm -rf build

#
# Docker
#
DOCKER_REPO := docker.pkg.github.com/machinezone/rcc
NAME        := ${DOCKER_REPO}/rcc
TAG         := $(shell python tools/compute_version_from_git.py)
IMG         := ${NAME}:${TAG}
BUILD       := ${NAME}:build
PROD        := ${NAME}:production

docker_tag:
	docker tag ${IMG} ${PROD}
	docker push ${PROD}
	docker push ${IMG}

docker: update_version
	git clean -dfx -e venv -e cobras.egg-info/ -e DOCKER_VERSION
	docker build -t ${IMG} .
	docker tag ${IMG} ${BUILD}
	docker tag ${IMG} ${PROD}

docker_push: docker_tag

deploy: docker docker_push

dummy: docker
