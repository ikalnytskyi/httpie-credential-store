import os
import tempfile

import mock
import pytest


@pytest.fixture(scope="session", autouse=True)
def _httpie_config_dir():
    """Set path to HTTPie configuration directory."""

    # HTTPie can optionally read a path to configuration directory from
    # environment variable. In order to avoid messing with user's local
    # configuration, HTTPIE_CONFIG_DIR environment variable is patched to point
    # to a temporary directory instead. But here's the thing, HTTPie is not ran
    # in subprocess in these tests, and so the environment variable is read
    # only once on first package import. That's why it must be set before
    # HTTPie package is imported and that's why the very same value must be
    # used for all tests (session scope). Otherwise, tests may fail because
    # they will look for credentials file in different directory.
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"HTTPIE_CONFIG_DIR": tmpdir}):
            yield tmpdir
