#!/usr/bin/env python

"""

Releases failed jobs in uservice, making them available for processing again.

Takes one parameter - uservice project name:

 ./delete_claims.py MESO19VDS4

This tool reads ~/.odin.cfg and looks for the followign sections.

...

[uservice-api]
base_uri = http://malachite.rss.chalmers.se:8080/rest_api
version = v4

[auth]
user = user
password = password
...
"""

import Queue
import threading
from sys import argv
from os.path import join, expanduser
from ConfigParser import ConfigParser
import requests


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
            print status.url, status.status_code
            self.queue.task_done()


def delete_claim(project):
    config_parser = ConfigParser()
    config_parser.read(expanduser('~/.odin.cfg'))

    project_uri = join(
        config_parser.get('uservice-api', 'base_uri'),
        config_parser.get('uservice-api', 'version'),
        project
    )
    auth = (
        config_parser.get('auth', 'user'),
        config_parser.get('auth', 'password')
    )
    response = requests.get(project_uri + '/jobs')
    jobs = response.json()['Jobs']
    if jobs == []:
        exit("delete_clams.py: No project called {}".format(project))

    queue = Queue.Queue()

    for _ in range(10):
        thread = ThreadDelete(queue, auth)
        thread.setDaemon(True)
        thread.start()

    for job in jobs:
        if job['Status'] == 'FAILED':
            url_claim = project_uri + '/jobs' + '/' + job['Id'] + '/claim'
            queue.put(url_claim)
    queue.join()


if __name__ == '__main__':
    if len(argv) == 2:
        delete_claim(argv[1])
    else:
        exit("delete_claims.py: takes one uservice project as a parameter")
