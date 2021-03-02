
VIRTUALENV ?= .venv
RELEASE_TEST_VENV ?= .release-test-venv
PYCODESTYLE ?= $(VIRTUALENV)/bin/python3 -m pycodestyle
AUTOPEP8 ?= $(VIRTUALENV)/bin/python3 -m autopep8
FLAKE8 ?= $(VIRTUALENV)/bin/python3 -m flake8
MYPY ?= $(VIRTUALENV)/bin/python3 -m mypy


# Auto format by coding style check
.PHONY: autocs
autocs: dev
	$(AUTOPEP8) --in-place --recursive .

# Auto format diff by coding style check
.PHONY: autocs-diff
autocs-diff: dev
	$(AUTOPEP8) --diff --recursive .

# Coding style check
.PHONY: cs
cs: dev
	$(PYCODESTYLE)

.PHONY: lint
lint: dev
	$(FLAKE8)
	$(MYPY)

# Run tests
.PHONY: check
check: dev
	. $(VIRTUALENV)/bin/activate && pytest

# Run tests with specific docker-image
.PHONY: check-docker-image
check-docker-image: dev
	. $(VIRTUALENV)/bin/activate && pytest --docker-image=$(DOCKER_IMAGE)

# Run tests on one selected docker image
.PHONY: quick-check
quick-check:
	. $(VIRTUALENV)/bin/activate && pytest --docker-image=ubuntu:bionic

# Update requirements files for setup.py
.PHONY: update-requirements
update-requirements: $(VIRTUALENV)/bin/python3
	$(VIRTUALENV)/bin/pip3 install --upgrade pip-tools
	$(VIRTUALENV)/bin/pip-compile --no-emit-trusted-host --no-emit-index-url --upgrade --output-file requirements.txt requirements.in
	$(VIRTUALENV)/bin/pip-compile --no-emit-trusted-host --no-emit-index-url --upgrade --output-file requirements-dev.txt requirements-dev.in

# Create a virtualenv in .venv or the directory given in the following form: 'make VIRTUALENV=.venv2 install'
$(VIRTUALENV)/bin/python3:
	python3 -m venv $(VIRTUALENV)
	$(VIRTUALENV)/bin/pip install --upgrade pip

.PHONY: venv
venv: $(VIRTUALENV)/bin/python3

.PHONY: release
release:
	make venv VIRTUALENV=$(RELEASE_TEST_VENV)
	$(RELEASE_TEST_VENV)/bin/pip3 install wheel
	$(RELEASE_TEST_VENV)/bin/python3 setup.py sdist bdist_wheel
	$(RELEASE_TEST_VENV)/bin/pip install dist/*.whl
	$(RELEASE_TEST_VENV)/bin/pip3 install -r requirements-dev.txt

.PHONY: release-test
release-test: release
	. $(RELEASE_TEST_VENV)/bin/activate && pytest --docker-image=ubuntu:bionic

# Install development dependencies (for testing) in virtualenv
.PHONY: dev
dev: venv
	$(VIRTUALENV)/bin/pip3 install -e '.[dev]'

# Clean directory and delete virtualenv
.PHONY: clean
clean:
	-$(VIRTUALENV)/bin/python3 setup.py clean --all
	-$(RELEASE_TEST_VENV)/bin/python3 setup.py clean --all
	rm -rf $(VIRTUALENV)
	rm -rf $(RELEASE_TEST_VENV)

.PHONY: get-version
get-version:
	cat bldr/VERSION

.PHONY: bump-version
bump-version:
	@./bump_version.py
