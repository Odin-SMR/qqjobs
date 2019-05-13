import json
import base64
import argparse
from sys import stderr
from collections import defaultdict

import requests
from Crypto.Cipher import AES

from .scanids import ScanIDs
from ..utils import load_config, validate_config, validate_project_name

NUMBER_OF_JOBS_TO_POST = 1000

DESCRIPTION = ("Add qsmr jobs to the microq job service.\n"
               "Choose between adding all scans in the freqmode, all scans "
               "between two timestamps or all scans in the vds dataset.\n"
               "If no jobs arguments are provided, the configuration and "
               "project name are validated.")


def make_argparser(prog):
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'PROJECT_NAME', help=(
            'Microq service project name, must only contain ascii letters '
            'and digits and start with an ascii letter'))
    parser.add_argument('ODIN_PROJECT', help=(
        'the project name used in the odin api'))
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


def main(args=None, config_file=None, prog=None):
    args = make_argparser(prog).parse_args(args)
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
    config = load_config(config_file)
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


class AddQsmrJobs:
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

    def _post_jobs(self, list_of_jobs):
        return self.session.post(
            self.job_api_root + '/v4/{}/jobs'.format(self.project),
            headers={'Content-Type': "application/json"},
            json=list_of_jobs, auth=(self.token, ''))

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
        list_of_jobs = self.filter_jobs(
            scanids, freqmode, skip)
        # split the post into several posts if list of jobs is long
        for n_post in range(len(list_of_jobs) // NUMBER_OF_JOBS_TO_POST + 1):
            try:
                response = self._post_jobs(
                    list_of_jobs[
                        n_post * NUMBER_OF_JOBS_TO_POST:
                        (n_post + 1) * NUMBER_OF_JOBS_TO_POST])
                status_code = response.status_code
                if status_code == 401:
                    print('Fetching new token')
                    self.get_token()
                    response = self._post_jobs(
                        list_of_jobs[
                            n_post * NUMBER_OF_JOBS_TO_POST:
                            (n_post + 1) * NUMBER_OF_JOBS_TO_POST])
                    status_code = response.status_code
                status_codes[status_code].append(n_post)
            except Exception as err:  # pylint: disable=broad-except
                stderr.write('Add job failed: %s\n' % err)
                print_status(n_post, status_codes)
                print(('Exiting, you can try add_jobs.py again with --skip=%s'
                       '') % (n_post * NUMBER_OF_JOBS_TO_POST))
                return False
            nr_of_jobs_added = min(
                len(list_of_jobs), (n_post + 1) * NUMBER_OF_JOBS_TO_POST)
            print_status(nr_of_jobs_added, status_codes)
        return True

    def filter_jobs(self, scanids, freqmode, skip):
        list_of_jobs = []
        for i, scanid in enumerate(scanids):
            if i < skip:
                continue
            list_of_jobs.append(self.make_job_data(scanid, freqmode))
        return list_of_jobs


def encrypt(msg, secret):
    msg += ' ' * (16 - (len(msg) % 16 or 16))
    cipher = AES.new(secret, AES.MODE_ECB)
    return base64.urlsafe_b64encode(cipher.encrypt(msg)).decode('utf8')


def encode_level2_target_parameter(scanid, freqmode, project, secret):
    """Return encrypted string from scanid, freqmode and project to be used as
    parameter in a level2 post url
    """
    data = {'ScanID': scanid, 'FreqMode': freqmode, 'Project': project}
    return encrypt(json.dumps(data), secret)
