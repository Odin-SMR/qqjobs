import argparse
import queue
import sys
import requests
import threading

from ..utils import load_config, validate_config
from ..projectsgenerator.qsmrprojects import is_project

DESCRIPTION = """Release Claim

Releases failed and/or claimed jobs in uservice,
making them available for processing again.
"""

NUMBER_OF_THREADS = 10


class BadProjectError(ValueError):
    pass


class ThreadDelete(threading.Thread):
    """Threaded Url Grab"""
    def __init__(self, jobqueue, auth):
        threading.Thread.__init__(self)
        self.jobqueue = jobqueue
        self.auth = auth

    def run(self):
        while True:
            url_claim = self.jobqueue.get()
            status = requests.delete(url_claim, auth=self.auth)
            print("DELETE-CLAIM {} {}".format(status.url, status.status_code))
            self.jobqueue.task_done()


def get_project_uri_and_auth(project, config):
    project_uri = "{}/{}/{}".format(
        config['JOB_API_ROOT'],
        config.get('JOB_API_VERSION', 'v4'),
        project,
    )
    auth = (config['JOB_API_USERNAME'], config['JOB_API_PASSWORD'])
    return project_uri, auth


def get_project_jobs(project, project_uri, config):
    try:
        response = requests.get(project_uri + '/jobs')
    except requests.ConnectionError:
        raise BadProjectError(
            'Could not connect to MicroQ service, '
            'validate that the url is correct '
            'and that you have internet connection.'
        )
    try:
        response.raise_for_status()
    except requests.HTTPError as err:
        raise BadProjectError(str(err))

    if not is_project(project, config):
        raise BadProjectError("No project called {}".format(project))

    jobs = response.json()['Jobs']
    if not jobs:
        raise BadProjectError("Project {} has no jobs".format(project))
    return jobs


def delete_claim(project, config_file=None, force=False):
    config = load_config(config_file)
    if not validate_config(config):
        return 1

    project_uri, auth = get_project_uri_and_auth(project, config)

    try:
        jobs = get_project_jobs(project, project_uri, config)
    except BadProjectError as err:
        return str(err)

    jobqueue = queue.Queue()

    for _ in range(NUMBER_OF_THREADS):
        thread = ThreadDelete(jobqueue, auth)
        thread.setDaemon(True)
        thread.start()

    deleteable = ['FAILED', 'CLAIMED'] if force else ['FAILED']
    for job in jobs:
        status = job['Status']
        if status in deleteable:
            url_claim = "{}/jobs/{}/claim".format(project_uri, job['Id'])
            jobqueue.put(url_claim)
    jobqueue.join()
    return 0


def main(argv=None, config_file=None, prog=None):
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'PROJECT',
        help="""The project for which to release claims"""
    )
    parser.add_argument(
        '--force',
        help='Force making claimed jobs available too, not only failed jobs',
        action='store_true',
    )
    args = parser.parse_args(argv)
    return delete_claim(args.PROJECT, config_file, force=args.force)
