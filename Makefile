# Building cluster-sanity container
IMAGE_BUILD_CMD ?= "docker"
IMAGE_REGISTRY ?= "quay.io"
REGISTRY_NAMESPACE ?= "interop_qe_ms"
OPERATOR_IMAGE_NAME="ms-interop-tests"
IMAGE_TAG ?= "latest"

FULL_OPERATOR_IMAGE ?= "$(IMAGE_REGISTRY)/$(REGISTRY_NAMESPACE)/$(OPERATOR_IMAGE_NAME):$(IMAGE_TAG)"

all: check pipenv run_tests build-container push-container

check:
	tox

pipenv:
	-pipenv --rm # '-' for ignore error when pipenv venv is not exists
	pipenv install --skip-lock
	pipenv run pip freeze

run_tests:
	pipenv run pytest tests/cluster_sanity

build-container:
	$(IMAGE_BUILD_CMD) build --no-cache -f builder/Dockerfile -t $(FULL_OPERATOR_IMAGE) .

push-container:
	$(IMAGE_BUILD_CMD) push $(FULL_OPERATOR_IMAGE)

.PHONY: all
