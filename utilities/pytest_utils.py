import logging
import os

import pytest as pytest


LOGGER = logging.getLogger(__name__)


# TODO: Remove once added to openshift-python-utilities
def exit_pytest_execution(
    message,
    return_code=99,
    filename=None,
    junitxml_property=None,
):
    """Exit pytest execution

    Exit pytest execution; invokes pytest_sessionfinish.
    Optionally, log an error message to tests-collected-info/utilities/pytest_exit_errors/<filename>

    Args:
        message (str):  Message to display upon exit and to log in errors file
        return_code (int. Default: 99): Exit return code
        filename (str, optional. Default: None): filename where the given message will be saved
        junitxml_property (pytest plugin): record_testsuite_property
    """
    if filename:
        write_to_extras_file(
            extras_file_name=filename,
            content=message,
            extra_dir_name="pytest_exit_errors",
        )
    if junitxml_property:
        junitxml_property(name="exit_code", value=return_code)
    pytest.exit(msg=message, returncode=return_code)


# TODO: Remove once added to openshift-python-utilities
def write_to_extras_file(extras_file_name, content, extra_dir_name="extras"):
    base_dir = os.environ.get("TEST_DIR_LOG", "/tmp")
    extras_dir = os.path.join(base_dir, extra_dir_name)
    os.makedirs(extras_dir, exist_ok=True)
    extras_file_path = os.path.join(extras_dir, extras_file_name)

    try:
        with open(extras_file_path, "w") as fd:
            fd.write(content)
    except Exception as exp:
        LOGGER.error(f"Failed to write extras to file: {extras_file_path} {exp}")
