# managed-services-integration-tests

This repository contains tests.

The infra for the tests can be found in <https://github.com/RedHatQE/openshift-python-wrapper> and <https://github.com/RedHatQE/openshift-python-utilities>
flake8 plugins defined in .flake8 can be found in <https://github.com/RedHatQE/flake8-plugins>

## How to run

### Setup VirtualEnv

Use [poetry](https://python-poetry.org/docs/) to manage virtualenv.

```bash
pip install poetry
```

After installation, run:

```bash
poetry install
```

To get current env info

```bash
poetry env info
```

To get poetry virtualenv names

```bash
poetry env list
```

To remove current env

```bash
poetry env remove <env name>
```

To clear poetry cache (needed before update if there is an existing update but the package is not updated)

```bash
poetry cache list # get poetry available cache list
poetry cache clear --all <cache name> # delete all cache (except _default_cache)
```

To update one package

```bash
poetry update openshift-python-wrapper
```

### Prepare a cluster

This project runs tests against one or more OCP clusters.
To get the OCM / ROSA / Hypershift cluster's kubeconfig run:

```bash
ocm get clusters -p search="name like '"$CLUSTER_NAME"%'" | jq -r  '.items | .[] | .id' \
| xargs -I {} ocm get /api/clusters_mgmt/v1/clusters/{}/credentials | jq -r .kubeconfig
```

Save the output to a file and export it as `KUBECONFIG`

```bash
export KUBECONFIG=<path to kubeconfig file>
```

Use a specific file path, pass

```bash
poetry run pytest ... --kubeconfig_file_paths="<path to kubeconfig1>"
```

To run against multiple clusters, pass

```bash
poetry run pytest ... --kubeconfig_file_paths="<path to kubeconfig1>,<path to kubeconfig2>"
```

Note: explicit usage of values should be implemented according to the relevant test requirements

## Logging

Log file 'pytest-tests.log' is generated with the full pytest output in the tests root directory.
For each test failure cluster logs are collected and stored under 'tests-collected-info'.

To see verbose logging of a test run, add the following parameter:

```bash
make tests PYTEST_ARGS="-o log_cli=true"
```

To enable data-collector pass data-collector.yaml
YAML format:

```yaml
    data_collector_base_directory: "<base directory for data collection>"
    collect_data_function: "<import path for data collection method>"
```

YAML Example:

```yaml
    data_collector_base_directory: "tests-collected-info"
    collect_data_function: "ocp_wrapper_data_collector.data_collector.collect_data"
    collect_pod_logs: true
```

```bash
poetry run pytest .... --data-collector=data-collector.yaml
```

Logs will be available under tests-collected-info/ folder.

### Setting log level in command line

In order to run a test with a log level that is different from the default,
use the --log-cli-level command line switch.
The full list of possible log level strings can be found [here](https://docs.python.org/3/library/logging.html#logging-levels)

When the switch is not used, we set the default level to INFO.

Example:

```bash
--log-cli-level=DEBUG
````

## Running tests

### Cluster upgrade tests

To run the cluster upgrade test, you will need to provide the cluster name and the OCP target version.

Example:

```bash
poetry run pytest -m upgrade --ocp-target-version 4.10.35 --cluster-name {cluster name} \
--data-collector={path to data collector yaml}
```

If running against a production cluster, add: `--tc=ocm_api_server:production`

### Hypershift cluster installation tests

To run hypershift installation tests make sure the following environment variables are set:
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
OCM_TOKEN

```bash
poetry run pytest ... --ocp-target-version {OCP version} -m hypershift_install
```

## Building and pushing tests container image

Container can be generated and pushed using make targets.

```bash
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
commit-msg use gitlint (<https://jorisroovers.com/gitlint/>)

To check for PEP 8 issues locally run:

```bash
tox
```

## Running with OCM client

Export `OCM_TOKEN` env variable locally or in test container

```bash
export OCM_TOKEN="production or stage OCM token"
```

## Overwrite global_config execution configuration

You can overwrite the api server defined in global_config.py by passing the following in command line:
For example:

```bash
poetry run pytest ... --tc=ocm_api_server:stage
```
