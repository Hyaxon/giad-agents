.PHONY: all check check-giad-example image test-image images smoke sandbox-smoke lint

PYTHON ?= python3
GIAD_DIR ?= ../giad
VERSION := $(shell cat VERSION)

all: check

check:
	PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

check-giad-example:
	$(PYTHON) tools/sync_giad_example.py --runtime "$(GIAD_DIR)"

image:
	docker build -t giad-agents:$(VERSION) .

test-image:
	docker build -t giad-agents-tests:fixture tests/runner

images: image test-image

# Host processes are used only by these offline integration tests.
smoke:
	$(PYTHON) tools/giad_smoke.py --runtime "$(GIAD_DIR)"

sandbox-smoke: test-image
	$(PYTHON) tools/giad_smoke.py --runtime "$(GIAD_DIR)" --docker-image giad-agents:$(VERSION) --test-image giad-agents-tests:fixture

lint:
	npx --yes markdownlint-cli2@0.23.3
