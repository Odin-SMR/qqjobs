#!/usr/bin/env python

import argparse
import Queue
import threading
import sys
from os.path import join, expanduser
from ConfigParser import ConfigParser
import requests

from ..utils import load_config, validate_config
from ..projectsgenerator.qsmrprojects import is_project

DESCRIPTION = """Release Claim

Releases failed and/or claimed jobs in uservice,
making them available for processing again.
"""

NUMBER_OF_THREADS = 10


class ThreadDelete(threading.Thread):
    """Threaded Url Grab"""
    def __init__(self, queue, auth):
        threading.Thread.__init__(self)
        self.queue = queue
        self.auth = auth

    def run(self):
        while True:
            url_claim = self.queue.get()
            status = requests.delete(url_claim, auth=self.auth)
            print("DELETE-CLAIM {} {}".format(status.url, status.status_code))
            self.queue.task_done()


def delete_claim(project, config_file=None, force=False):
    config = load_config(config_file)
    if not validate_config(config):
        return 1

    project_uri = join(
        config['JOB_API_ROOT'],
        config.get('JOB_API_VERSION', 'v4'),
        project,
    )
    auth = (config['JOB_API_USERNAME'], config['JOB_API_PASSWORD'])
    try:
        response = requests.get(project_uri + '/jobs')
    except requests.ConnectionError:
        return (
            'Could not connect to MicroQ service, '
            'validate that the url is correct '
            'and that you have internet connection.'
        )
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        return str(e)

    if not is_project(project, config):
        return "No project called {}".format(project)

    jobs = response.json()['Jobs']
    if not jobs:
        return "Project {} has no jobs".format(project)

    queue = Queue.Queue()

    for _ in range(NUMBER_OF_THREADS):
        thread = ThreadDelete(queue, auth)
        thread.setDaemon(True)
        thread.start()

    deleteable = ['FAILED', 'CLAIMED'] if force else ['FAILED']
    for job in jobs:
        status = job['Status']
        if status in deleteable:
            url_claim = "{}/jobs/{}/claim".format(project_uri, job['Id'])
            queue.put(url_claim)
    queue.join()


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


if __name__ == '__main__':
    exit(main())
