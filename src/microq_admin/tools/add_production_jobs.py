import argparse
from datetime import datetime, timedelta
import requests

from ..utils import load_config, validate_config
from ..jobsgenerator.qsmrjobs import AddQsmrJobs
from .delete_project import InvalidConfig


DESCRIPTION = '''
    Add jobs to the microq job service for
    production projects
'''


FIRST_DATE_TO_PROCESS = '2019-08-01'


def get_level2_projects(urlbase_odinapi):
    url = f'{urlbase_odinapi}/v5/level2/projects'
    return requests.get(url).json()['Data']


def get_latest_date_to_process(urlbase_odinapi):
    url = f'{urlbase_odinapi}/v5/config_data/latest_ecmf_file'
    date = requests.get(url).json()['Date']
    return datetime.strptime(date, '%Y-%m-%d').date()


def get_level1_scans(urlbase_odinapi, date_start, date_end, freqmode):
    scanids = []
    url = f'{urlbase_odinapi}/v5/level1/{freqmode}/scans'
    while date_start < date_end:
        params = {
            'start_time': date_start.strftime('%Y-%m-%d'),
            'end_time': (date_start + timedelta(days=1)).strftime('%Y-%m-%d'),
        }
        r = requests.get(url, params=params)
        for scan in r.json()['Data']:
            scanids.append(scan['ScanID'])
        date_start += timedelta(days=1)
    return scanids


def get_processing_projects(urlbase_uservice):
    url = f'{urlbase_uservice}/v4/projects'
    projects = requests.get(url).json()['Projects']
    return projects


def get_claimed_jobs(urlbase_uservice, project, date_start):
    url = f'{urlbase_uservice}/v4/{project}/jobs'
    date_end = datetime.utcnow().date()
    ids = []
    while date_start < date_end:
        params = {
            'status': 'CLAIMED',
            'start': date_start.strftime('%Y-%m-%dT00:00:00'),
            'end': (
                date_start + timedelta(days=1)
            ).strftime('%Y-%m-%dT00:00:00'),
        }
        r = requests.get(url, params=params)
        for job in r.json()['Jobs']:
            ids.append(job['Id'])
        date_start += timedelta(days=1)
    return ids


def get_matching_projects(level2_projects, processing_projects):
    matching_projects = []
    for level2_project in level2_projects:
        for processing_project in processing_projects:
            if level2_project['Name'] == processing_project['Name']:
                matching_projects.append({
                    'name': processing_project['Name'],
                    'id': processing_project['Id']
                })
    return matching_projects


def get_freqmode_from_jobid(jobid):
    return int(jobid.split(':')[0])


def get_scanids_from_jobids(jobids):
    return [int(id.split(':')[1]) for id in jobids]


def add_jobs(config, processing_project, level2_project, freqmode, scanids):
    adder = AddQsmrJobs(
        processing_project, level2_project, config['ODIN_API_ROOT'],
        config['ODIN_SECRET'], config['JOB_API_ROOT'],
        config['JOB_API_USERNAME'], config['JOB_API_PASSWORD']
    )
    adder.add_jobs(scanids, freqmode)


def get_unprocessed_scanids(
        urlbase_odinapi, urlbase_uservice, project_id, date_start, date_end):
    jobids_claimed = get_claimed_jobs(urlbase_uservice, project_id, date_start)
    if len(jobids_claimed) == 0:
        return None, []
    freqmode = get_freqmode_from_jobid(jobids_claimed[0])
    scanids_claimed = get_scanids_from_jobids(jobids_claimed)
    scanids_available = get_level1_scans(
        urlbase_odinapi, date_start, date_end, freqmode)
    unprocessed_scans = list(set(scanids_available) - set(scanids_claimed))
    return freqmode, unprocessed_scans


def main(argv=None, config_file=None, prog=None):
    argparse.ArgumentParser(
        description=DESCRIPTION,
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    config = load_config(config_file)
    if not validate_config(config):
        raise InvalidConfig('Invalid config file.')

    date_start = datetime.strptime(
        FIRST_DATE_TO_PROCESS, '%Y-%m-%d').date()
    date_end = get_latest_date_to_process(config['ODIN_API_ROOT'])

    level2_projects = get_level2_projects(config['ODIN_API_ROOT'])
    processing_projects = get_processing_projects(
        config['JOB_API_ROOT'])
    matching_projects = get_matching_projects(
        level2_projects, processing_projects)
    for project in matching_projects:
        freqmode, scanids = get_unprocessed_scanids(
            config['ODIN_API_ROOT'], config['JOB_API_ROOT'], project['id'],
            date_start, date_end
        )
        if len(scanids) == 0:
            continue
        add_jobs(
            config, project['id'], project['name'], freqmode, scanids)
