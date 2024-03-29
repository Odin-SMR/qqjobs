import os
from subprocess import check_call

import requests
from requests.exceptions import RequestException
import pytest

WAIT_FOR_SERVICE_TIME = 60 * 5
PAUSE_TIME = 0.1


def pytest_addoption(parser):
    """Adds the integrationtest option"""
    parser.addoption(
        "--runslow", action="store_true", help="run slow tests")
    parser.addoption(
        "--runsystem", action="store_true", help="run system tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--runslow'):
        skip_slow = pytest.mark.skip(reason='need --runslow option to run')
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if not config.getoption('--runsystem'):
        skip_system = pytest.mark.skip(reason='need --runsystem option to run')
        for item in items:
            if "system" in item.keywords:
                item.add_marker(skip_system)


def is_responsive(odinapi, microq):
    try:
        # ODIN
        r = requests.get(
            '{}'.format(odinapi),
            timeout=5,
        )
        r.raise_for_status()
        # MICROQ
        r = requests.get(
            "{}".format(microq),
            timeout=5,
        )
        r.raise_for_status()
    except RequestException as msg:
        print(msg)
        return False
    return True


@pytest.fixture(scope='session')
def docker_compose_file(pytestconfig):
    return os.path.join(
        str(pytestconfig.rootdir),
        'docker-compose.systemtest.yml',
    )


@pytest.fixture(scope='session')
def odin_and_microq(docker_ip, docker_services):
    odinport = docker_services.port_for('odinapi', 5000)
    microqport = docker_services.port_for('microq', 5000)
    odinurl = "http://{}:{}".format(docker_ip, odinport)
    microqurl = "http://{}:{}".format(docker_ip, microqport)
    docker_services.wait_until_responsive(
        timeout=WAIT_FOR_SERVICE_TIME,
        pause=PAUSE_TIME,
        check=lambda: is_responsive(odinurl, microqurl),
    )
    return odinurl, microqurl


@pytest.fixture(scope='session')
def microq_admin():
    check_call(['./build.sh'])


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow, use --runslow to run",
    )
    config.addinivalue_line(
        "markers",
        "system: mark test as system, use --runsystem to run",
    )
