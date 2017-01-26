"""Base module for tests"""
import os
import pytest


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'testdata')

slow = pytest.mark.skipif(  # pylint: disable=invalid-name
    not pytest.config.getoption("--runslow"),
    reason="need --runslow option to run"
)

system = pytest.mark.skipif(  # pylint: disable=invalid-name
    not pytest.config.getoption("--runsystem"),  # pylint: disable=no-member
    reason="need --runsystem option to run"
)

disable = pytest.mark.skipif(  # pylint: disable=invalid-name
    not pytest.config.getoption("--rundisabled"),
    reason="need --rundisabled option to run"
)
