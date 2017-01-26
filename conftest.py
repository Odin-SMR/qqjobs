"""Unittests"""

from time import sleep
from subprocess import check_output, Popen
import pytest


def pytest_addoption(parser):
    """Adds the integrationtest option"""
    parser.addoption(
        "--runslow", action="store_true", help="run slow tests")
    parser.addoption(
        "--runsystem", action="store_true", help="run system tests")
    parser.addoption(
        "--rundisabled", action="store_true", help="run disabled tests")
    parser.addoption(
        "--no-system-restart", action="store_true",
        help="do not restart the system")


def call_docker_compose(cmd, root_path, args=None, wait=True):
    cmd = ['docker-compose', cmd] + (args or [])
    popen = Popen(cmd, cwd=root_path)
    if wait:
        popen.wait()
    return popen


@pytest.yield_fixture(scope='module')
def dockercompose():
    """Set up the full system"""
    root_path = check_output(['git', 'rev-parse', '--show-toplevel']).strip()

    if not pytest.config.getoption("--no-system-restart"):
        call_docker_compose('stop', root_path)
        call_docker_compose('rm', root_path, args=['--force'])
        call_docker_compose('pull', root_path)
        call_docker_compose('build', root_path)

    args = ['--abort-on-container-exit', '--remove-orphans']
    system = call_docker_compose('up', root_path, args=args, wait=False)

    # TODO: Replace with something better that checks that the system is up
    sleep(30)

    yield system.pid

    if not pytest.config.getoption("--no-system-restart"):
        call_docker_compose('stop', root_path)
        if system.poll() is None:
            system.kill()
            system.wait()
