from unittest.mock import patch
from collections import namedtuple
from datetime import date, datetime, timedelta
import requests
import tempfile
import pytest

from microq_admin.tools import add_production_jobs
from microq_admin.projectsgenerator.qsmrprojects import (
    create_project, delete_project, is_project
)
from microq_admin.utils import load_config
from microq_admin.jobsgenerator.qsmrjobs import (
    main as jobsmain,
)


RESPONSE = namedtuple('response', 'json')


URLBASE_ODINAPI = 'http://odin.rss.chalmers.se/rest_api'
URLBASE_USERVICE = 'http://odin.rss.chalmers.se:8080/rest_api'


def level2_projects():
    return {'Data': [{'Name': 'p1'}, {'Name': 'p2'}]}


def processing_projects():
    return {'Projects': [{'Name': 'p1'}, {'Name': 'p2'}]}


def latest_date():
    return {'Date': '1999-12-31'}


def level1_scans():
    return {'Data': [{'ScanID': 1}, {'ScanID': 2}, {'ScanID': 3}]}


def claimed_scans():
    return {
        'Jobs': [
            {'Id': '1:101'}, {'Id': '1:102'}, {'Id': '1:103'}
        ]
    }


@pytest.mark.parametrize('level2_projects,processing_projects,expect', (
    (
        [{'Name': 'p1'}],
        [
            {'Name': 'p1', 'Id': 1},
            {'Name': 'p3', 'Id': 3},
            {'Name': 'p2', 'Id': 2}
        ],
        [{'name': 'p1', 'id': 1}]
    ),
    (
        [{'Name': 'p2'}, {'Name': 'p3'}],
        [
            {'Name': 'p1', 'Id': 1},
            {'Name': 'p3', 'Id': 3},
            {'Name': 'p2', 'Id': 2}
        ],
        [{'name': 'p2', 'id': 2}, {'name': 'p3', 'id': 3}]
    ),
))
def test_get_matching_projects(
        level2_projects, processing_projects, expect):
    projects = add_production_jobs.get_matching_projects(
        level2_projects, processing_projects)
    assert projects == expect


@patch(
    'requests.get', return_value=RESPONSE(json=level2_projects)
)
def test_get_level2_projects(mocked_requests):
    projects = add_production_jobs.get_level2_projects(URLBASE_ODINAPI)
    mocked_requests.assert_called_once_with(
        f'{URLBASE_ODINAPI}/v5/level2/projects')
    assert projects == [{'Name': 'p1'}, {'Name': 'p2'}]


@patch(
    'requests.get',
    return_value=RESPONSE(json=processing_projects)
)
def test_get_processing_projects(mocked_requests):
    projects = add_production_jobs.get_processing_projects(
        URLBASE_USERVICE)
    mocked_requests.assert_called_once_with(
        f'{URLBASE_USERVICE}/v4/projects')
    assert projects == [{'Name': 'p1'}, {'Name': 'p2'}]


@patch(
    'requests.get',
    return_value=RESPONSE(json=latest_date)
)
def test_get_latest_date_to_process(mocked_requests):
    latest_date = add_production_jobs.get_latest_date_to_process(
        URLBASE_ODINAPI)
    mocked_requests.assert_called_once_with(
        f'{URLBASE_ODINAPI}/v5/config_data/latest_ecmf_file')
    assert latest_date == date(1999, 12, 31)


@patch(
    'requests.get',
    return_value=RESPONSE(json=level1_scans)
)
def test_get_level1_scans_single_date(mocked_requests):
    date_start = date(2000, 1, 1)
    date_end = date(2000, 1, 2)
    freqmode = 1
    scanids = add_production_jobs.get_level1_scans(
        URLBASE_ODINAPI, date_start, date_end, freqmode)
    mocked_requests.assert_called_with(
        f'{URLBASE_ODINAPI}/v5/level1/1/scans',
        params={'start_time': '2000-01-01', 'end_time': '2000-01-02'}
    )
    assert scanids == [1, 2, 3]


@patch(
    'requests.get',
    return_value=RESPONSE(json=level1_scans)
)
def test_get_level1_scans_mutliple_dates(mocked_requests):
    date_start = date(2000, 1, 1)
    date_end = date(2000, 1, 3)
    freqmode = 1
    scanids = add_production_jobs.get_level1_scans(
        URLBASE_ODINAPI, date_start, date_end, freqmode)
    mocked_requests.assert_called_with(
        f'{URLBASE_ODINAPI}/v5/level1/1/scans',
        params={'start_time': '2000-01-02', 'end_time': '2000-01-03'}
    )
    assert scanids == [1, 2, 3, 1, 2, 3]


@patch(
    'requests.get',
    return_value=RESPONSE(json=claimed_scans)
)
def test_get_claimed_jobs(mocked_requests):
    project = 'p1'
    date_start = (datetime.utcnow() - timedelta(days=1)).date()
    jobids = add_production_jobs.get_claimed_jobs(
        URLBASE_USERVICE, project, date_start)
    mocked_requests.assert_called_once_with(
        f'{URLBASE_USERVICE}/v4/p1/jobs',
        params={
            'status': 'CLAIMED',
            'start': date_start.strftime('%Y-%m-%dT00:00:00'),
            'end': (
                date_start + timedelta(days=1)
            ).strftime('%Y-%m-%dT00:00:00')
        }
    )
    assert jobids == ['1:101', '1:102', '1:103']


@pytest.mark.parametrize('jobid,expect', (
    ('1:100', 1), ('3:101', 3)
))
def test_get_freqmode_from_jobid(jobid, expect):
    freqmode = add_production_jobs.get_freqmode_from_jobid(jobid)
    assert freqmode == expect


@pytest.mark.parametrize('jobids,expect', (
    (['1:100', '1:101'], [100, 101]),
    (['1:200', '1:201'], [200, 201]),
))
def test_get_scanids_from_jobids(jobids, expect):
    scanids = add_production_jobs.get_scanids_from_jobids(jobids)
    assert scanids == expect


@patch(
    'microq_admin.tools.add_production_jobs.AddQsmrJobs.add_jobs',
    return_value=None
)
def test_add_jobs_get_called(mocked_add_jobs):
    processing_project = 'proj1'
    level2_project = 'proj2'
    freqmode = 1
    scanids = [1, 2, 3]
    config = {
        'ODIN_API_ROOT': 'ODIN_API_ROOT',
        'ODIN_SECRET': 'ODIN_SECRET',
        'JOB_API_ROOT': 'JOB_API_ROOT',
        'JOB_API_USERNAME': 'JOB_API_USERNAME',
        'JOB_API_PASSWORD': 'JOB_API_PASSWORD'
    }
    add_production_jobs.add_jobs(
        config, processing_project, level2_project, freqmode, scanids)
    mocked_add_jobs.assert_called_with(scanids, freqmode)


@patch(
    'microq_admin.tools.add_production_jobs.get_claimed_jobs',
    return_value=['1:101', '1:102', '1:103']
)
@patch(
    'microq_admin.tools.add_production_jobs.get_level1_scans',
    return_value=[101, 102, 103, 104, 105]
)
def test_get_unprocessed_scanids_finds_data(
        mocked_level1_scans, mocked_claimed_jobs):
    date_start = date(2019, 1, 1)
    date_end = date(2019, 1, 10)
    project_id = 'proj1'
    freqmode, scanids = (
        add_production_jobs.get_unprocessed_scanids(
            URLBASE_ODINAPI, URLBASE_USERVICE, project_id,
            date_start, date_end)
    )
    assert freqmode == 1 and scanids == [104, 105]


@patch(
    'microq_admin.tools.add_production_jobs.get_claimed_jobs',
    return_value=[]
)
def test_get_unprocessed_scanids_no_claimed_jobs(
        mocked_claimed_jobs):
    date_start = date(2019, 1, 1)
    date_end = date(2019, 1, 10)
    project_id = 'proj1'
    freqmode, scanids = (
        add_production_jobs.get_unprocessed_scanids(
            URLBASE_ODINAPI, URLBASE_USERVICE, project_id,
            date_start, date_end)
    )
    assert freqmode is None and scanids == []


@patch(
    'microq_admin.tools.add_production_jobs.get_claimed_jobs',
    return_value=['1:101', '1:102', '1:103']
)
@patch(
    'microq_admin.tools.add_production_jobs.get_level1_scans',
    return_value=[101, 102, 103]
)
def test_get_unprocessed_scanids_no_new_data(
        mocked_level1_scans, mocked_claimed_jobs):
    date_start = date(2019, 1, 1)
    date_end = date(2019, 1, 10)
    project_id = 'proj1'
    freqmode, scanids = (
        add_production_jobs.get_unprocessed_scanids(
            URLBASE_ODINAPI, URLBASE_USERVICE, project_id,
            date_start, date_end)
    )
    assert freqmode == 1 and scanids == []


@pytest.fixture
def config_file(odin_and_microq):
    odinurl, microqurl = odin_and_microq
    fp = tempfile.NamedTemporaryFile(mode='w', delete=True)
    cfg = (
        'JOB_API_ROOT={}/rest_api\n'.format(microqurl)
        + 'JOB_API_USERNAME=admin\n'
        'JOB_API_PASSWORD=sqrrl\n'
        'ODIN_API_ROOT={}/rest_api\n'.format(odinurl)
        + 'ODIN_SECRET=rc/lY+OQYq6mvI6tCfr+tQ==\n'
    )
    fp.write(cfg)
    fp.flush()
    yield fp
    fp.close()


def make_project(jobsproject, odinproject, config):
    # No conflict with other tests
    assert not is_project(jobsproject, config)
    # Make projects
    arguments = namedtuple(
        'args', ['PROCESSING_IMAGE_URL', 'deadline', 'ODIN_PROJECT'])
    args = arguments('dummy', '2020-01-01', odinproject)
    assert not create_project(jobsproject, config, args=args)


def make_jobs(jobs_project, odin_project, config_filename):
    jobsfile = tempfile.NamedTemporaryFile(mode='w', delete=True)
    jobsfile.write('101\n102\n103\n')
    jobsfile.flush()
    assert not jobsmain([
        jobs_project, odin_project, '--freq-mode', '1', '--jobs-file',
        jobsfile.name,
    ], config_filename)
    jobsfile.close()


@pytest.fixture(scope='function')
def processing_project(config_file):
    config = load_config(config_file.name)
    jobs_project = "jobsproject"
    odin_project = "odinproject"
    make_project(jobs_project, odin_project, config)
    make_jobs(jobs_project, odin_project, config_file.name)
    yield jobs_project
    # Cleanup
    assert not delete_project(jobs_project, config)


@patch(
    'microq_admin.tools.add_production_jobs.get_level2_projects',
    return_value=[{'Name': 'odinproject'}]
)
@patch(
    'microq_admin.tools.add_production_jobs.get_level1_scans',
    return_value=[101, 102, 103, 104, 105]
)
@patch(
    'microq_admin.tools.add_production_jobs.get_claimed_jobs',
    return_value=['1:101', '1:102', '1:103']
)
def test_main(
        mocked_claimed,
        mocked_level1_scans,
        mocked_level2_projects,
        config_file,
        processing_project):
    add_production_jobs.main(config_file=config_file.name)
    config = load_config(config_file.name)
    jobs_project = processing_project
    r = requests.get(
        '{}/v4/{}/jobs'.format(config['JOB_API_ROOT'], jobs_project),
        params={'status': 'AVAILABLE'})
    ids = [job['Id'] for job in r.json()['Jobs']]
    assert ids == ['1:101', '1:102', '1:103', '1:104', '1:105']
