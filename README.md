# managed-services-integration-tests

This repository contains tests.

The infra for the tests can be found in https://github.com/RedHatQE/openshift-python-wrapper and https://github.com/RedHatQE/openshift-python-utilities
flake8 plugins defined in .flake8 can be found in https://github.com/RedHatQE/flake8-plugins

##Setup VirtualEnv

```bash
pip3 install pipenv
pipenv install --skip-lock
```

# Getting started

## Prepare a cluster

This project runs tests against an OCP cluster running on OSD / ROSA.
Export the cluster's kubeconfig file as KUBECONFIG
```bash
ocm get clusters -p search="name like '"<clustrer name>"%'" | jq -r  '.items | .[] | .id' | xargs -I {} ocm get /api/clusters_mgmt/v1/clusters/{}/credentials | jq -r .kubeconfig > ~/kubeconfig ; export KUBECONFIG=~/kubeconfig
```

### Logging
Log file 'pytest-tests.log' is generated with the full pytest output in the tests root directory.
For each test failure cluster logs are collected and stored under 'tests-collected-info'.

To see verbose logging of a test run, add the following parameter:

```bash
make tests PYTEST_ARGS="-o log_cli=true"
```
To enable log-collector set TEST_COLLECT_LOGS
To change the destination folder of collected logs set TEST_COLLECT_LOGS_DIR
```bash
export TEST_COLLECT_LOGS=1
export TEST_COLLECT_LOGS_DIR=/my/logs/dir
```
Logs will be available under tests-collected-info/ folder.

#### Cluster upgrade tests
`TODO`

### Setting log level in command line

In order to run a test with a log level that is different from the default,
use the --log-cli-level command line switch.
The full list of possible log level strings can be found here:
https://docs.python.org/3/library/logging.html#logging-levels

When the switch is not used, we set the default level to INFO.

Example:
```bash
--log-cli-level=DEBUG
````

### Building and pushing tests container image

Container can be generated and pushed using make targets.

```
make -f Makefile
```

## How-to verify your patch

### Check the code
We use checks tools that are defined in .pre-commit-config.yaml file
To install pre-commit:
```bash
pip install pre-commit --user
pre-commit install
pre-commit install --hook-type commit-msg
```
pre-commit will try to fix the error.
If some error where fixed git add & git commit is needed again.
commit-msg use gitlint (https://jorisroovers.com/gitlint/)

To check for PEP 8 issues locally run:
```bash
tox
```

### Run functional tests via Jenkins job
`TODO`

##### Known Issues
pycurl may fail with error:
ImportError: pycurl: libcurl link-time ssl backend (nss) is different from compile-time ssl backend (none/other)

To fix it:
```bash
export PYCURL_SSL_LIBRARY=nss # or openssl. depend on the error (link-time ssl backend (nss))
pipenv run pip uninstall pycurl
pipenv run pip install pycurl --no-cache-dir
```

# Running with OCM client
Either export `ANSIBLE_HASHI_VAULT_SECRET_ID` when working locally or set `OCM_TOKEN` env variable in test container
