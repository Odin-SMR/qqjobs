#!/usr/bin/env python2
"""
usage: qsmrjobs.py [-h] [--freq-mode FREQ_MODE] [--all]
                   [--start-day START_DAY] [--end-day END_DAY] [--vds]
                   [--jobs-file JOBS_FILE] [--skip SKIP]
                   PROJECT_NAME ODIN_PROJECT CONFIG_FILE

Add qsmr jobs to the microq job service.
Choose between adding all scans in the freqmode, all scans between
two timestamps or all scans in the vds dataset.
If no jobs arguments are provided, the configuration and project name
are validated.

positional arguments:
  PROJECT_NAME          Microq service project name, must only contain ascii
                        letters and digits and start with an ascii letter
  ODIN_PROJECT          the project name used in the odin api
  CONFIG_FILE           path to configuration file

optional arguments:
  -h, --help            show this help message and exit
  --freq-mode FREQ_MODE
                        freq mode of the jobs
  --all                 add all scan ids for this freq mode
  --start-day START_DAY
                        together with --all, only add scans from this day and
                        forward (yyyy-mm-dd)
  --end-day END_DAY     together with --all, only add scans up to this day
                        (yyyy-mm-dd, exclusive)
  --vds                 add all scan ids in the vds dataset for this freq mode
  --jobs-file JOBS_FILE
                        add the scan ids in this file, one scan id per row
  --skip SKIP           number of rows to skip in the jobs file

The configuration file should contain these settings:
ODIN_API_ROOT=https://example.com/odin_api
ODIN_SECRET=<secret encryption key>
JOB_API_ROOT=https://example.com/job_api
JOB_API_USERNAME=<username>
JOB_API_PASSWORD=<password>
"""
from __future__ import print_function
import json
import base64
import argparse
from sys import stderr
from collections import defaultdict

import requests
from Crypto.Cipher import AES

from jobsgenerator.scanids import ScanIDs

CONFIG_FILE_DOCS = """The configuration file should contain these settings:
ODIN_API_ROOT=https://example.com/odin_api
ODIN_SECRET=<secret encryption key>
JOB_API_ROOT=https://example.com/job_api
JOB_API_USERNAME=<username>
JOB_API_PASSWORD=<password>"""

DESCRIPTION = ("Add qsmr jobs to the microq job service.\n"
               "Choose between adding all scans in the freqmode, all scans "
               "between two timestamps or all scans in the vds dataset.\n"
               "If no jobs arguments are provided, the configuration and "
               "project name are validated.")


def make_argparser():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION, epilog=CONFIG_FILE_DOCS,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'PROJECT_NAME', help=(
            'Microq service project name, must only contain ascii letters '
            'and digits and start with an ascii letter'))
    parser.add_argument('ODIN_PROJECT', help=(
        'the project name used in the odin api'))
    parser.add_argument('CONFIG_FILE', help='path to configuration file')
    parser.add_argument('--freq-mode', help='freq mode of the jobs')
    parser.add_argument('--all', action='store_true', help=(
        'add all scan ids for this freq mode'))
    parser.add_argument('--start-day', help=(
        'together with --all, only add scans from this day and forward '
        '(yyyy-mm-dd)'))
    parser.add_argument('--end-day', help=(
        'together with --all, only add scans up to this day '
        '(yyyy-mm-dd, exclusive)'))
    parser.add_argument('--vds', action='store_true', help=(
        'add all scan ids in the vds dataset for this freq mode'))
    parser.add_argument('--jobs-file', help=(
        'add the scan ids in this file, one scan id per row'))
    parser.add_argument('--skip', help=(
        'number of rows to skip in the jobs file'))
    return parser


def main(args=None):
    args = make_argparser().parse_args(args)
    if not validate_project_name(args.PROJECT_NAME):
        stderr.write((
            'Project name must only contain ascii letters and digits and '
            'start with an ascii letter\n'))
        return 1
    if not validate_project_name(args.ODIN_PROJECT):
        stderr.write((
            'Odin project name must only contain ascii letters and digits and '
            'start with an ascii letter\n'))
        return 1
    config = load_config(args.CONFIG_FILE)
    if not validate_config(config):
        return 1
    if not args.freq_mode:
        return 0
    if not any([args.vds, args.all, args.jobs_file]):
        return 0

    freqmode = int(args.freq_mode)
    adder = AddQsmrJobs(
        args.PROJECT_NAME, args.ODIN_PROJECT, config['ODIN_API_ROOT'],
        config['ODIN_SECRET'], config['JOB_API_ROOT'],
        config['JOB_API_USERNAME'], config['JOB_API_PASSWORD'])
    skip = 0
    if args.skip:
        skip = int(args.skip)
        print('Skipping the first {} scanids'.format(skip))

    scanids = ScanIDs(config['ODIN_API_ROOT'])
    if args.vds:
        print('Adding all in vds dataset')
        ids = scanids.generate_vds(freqmode)
    elif args.all:
        print('Adding all between {start} and {end}'.format(
            start=args.start_day or ScanIDs.FIRST_DAY,
            end=args.end_day or ScanIDs(
                config['ODIN_API_ROOT']).get_latest_ecmf_day()))
        ids = scanids.generate_all(
            freqmode, start_day=args.start_day, end_day=args.end_day)
    elif args.jobs_file:
        print('Adding from file')
        ids = scanids.generate_from_file(args.jobs_file)

    return int(not adder.add_jobs(ids, freqmode, skip=skip))


class JobServiceError(Exception):
    pass


class AddQsmrJobs(object):
    # TODO: Should use uclient
    JOB_TYPE = 'qsmr'

    def __init__(self, project, odin_project, odin_api_root, odin_secret,
                 job_api_root, job_api_user, job_api_password):
        self.project = project
        self.odin_project = odin_project
        self.odin_api_root = odin_api_root
        self.job_api_root = job_api_root
        self.job_api_user = job_api_user
        self.job_api_password = job_api_password
        self.odin_secret = odin_secret

        self.session = requests.Session()
        self.token = None

    def make_job_data(self, scanid, freqmode):
        return {
            'id': '%s:%s' % (freqmode, scanid),
            'type': self.JOB_TYPE,
            'source_url': (self.odin_api_root +
                           '/v4/l1_log/{freqmode}/{scanid}/'.format(
                               scanid=scanid, freqmode=freqmode)),
            'target_url': self.odin_api_root + '/v5/level2?d={}'.format(
                encode_level2_target_parameter(
                    scanid, freqmode, self.odin_project, self.odin_secret)),
            'view_result_url': (
                self.odin_api_root +
                '/v5/level2/development/{project}/{freqmode}/{scanid}'.format(
                    project=self.odin_project, freqmode=freqmode, scanid=scanid
                ))
        }

    def add_job(self, scanid, freqmode):
        job = self.make_job_data(scanid, freqmode)
        return self._post_job(job)

    def _post_job(self, job):
        return self.session.post(
            self.job_api_root + '/v4/{}/jobs'.format(self.project),
            headers={'Content-Type': "application/json"},
            json=job, auth=(self.token, ''))

    def get_token(self):
        r = self.session.get(
            self.job_api_root + '/token',
            auth=(self.job_api_user, self.job_api_password)
        )
        if r.status_code != 200:
            raise JobServiceError('Get token returned %s' % r.status_code)
        self.token = r.json()['token']

    def add_jobs(self, scanids, freqmode, skip=0):
        self.get_token()

        def print_status(nr_processed, status_codes):
            print('%d jobs added (skipped %d)' % (nr_processed, skip))
            for k in sorted(status_codes.keys()):
                print('  Status code %s: %d' % (k, len(status_codes[k])))

        status_codes = defaultdict(list)
        i = 0
        for i, scanid in enumerate(scanids):
            if i < skip:
                continue
            try:
                response = self.add_job(scanid, freqmode)
                status_code = response.status_code
                if status_code == 401:
                    print('Fetching new token')
                    self.get_token()
                    response = self.add_job(scanid, freqmode)
                    status_code = response.status_code
                status_codes[status_code].append(scanid)
            except Exception as err:  # pylint: disable=broad-except
                stderr.write('Add job failed: %s\n' % err)
                print_status(i, status_codes)
                print(('Exiting, you can try add_jobs.py again with --skip=%s'
                       '') % i)
                return False
            if not (i+1) % 10:
                print_status(i+1, status_codes)
        print_status(i+1, status_codes)
        print('Done')
        return True


def load_config(config_file):
    with open(config_file) as inp:
        conf = dict(row.strip().split('=') for row in inp if row.strip())
    for k, v in conf.items():
        conf[k] = v.strip('"')
    return conf


def validate_config(config):
    """Return True if ok, else False"""
    def error(msg):
        stderr.write(msg + '\n')
        error.ok = False
    error.ok = True

    required = ['ODIN_API_ROOT', 'ODIN_SECRET',
                'JOB_API_ROOT', 'JOB_API_USERNAME',
                'JOB_API_PASSWORD']
    for key in required:
        if key not in config or not config[key]:
            error('Missing in config: %s' % key)
    if not error.ok:
        return False

    for api_root in ('ODIN_API_ROOT', 'JOB_API_ROOT'):
        url = config[api_root]
        if not url.startswith('http'):
            error('%s does not look like an url: %s' % (api_root, url))
        if url.endswith('/'):
            error('%s must not end with /' % api_root)
    return error.ok


def validate_project_name(project_name):
    """Must be ascii alnum and start with letter"""
    if not project_name:
        return False
    if isinstance(project_name, unicode):
        project_name = project_name.encode('utf-8')
    if not project_name[0].isalpha():
        return False
    if not project_name.isalnum():
        return False
    return True


def encrypt(msg, secret):
    msg = msg + ' '*(16 - (len(msg) % 16 or 16))
    cipher = AES.new(secret, AES.MODE_ECB)
    return base64.urlsafe_b64encode(cipher.encrypt(msg))


def encode_level2_target_parameter(scanid, freqmode, project, secret):
    """Return encrypted string from scanid, freqmode and project to be used as
    parameter in a level2 post url
    """
    data = {'ScanID': scanid, 'FreqMode': freqmode, 'Project': project}
    return encrypt(json.dumps(data), secret)


if __name__ == '__main__':
    exit(main())
