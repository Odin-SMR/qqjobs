import pytest
import requests

from .utils import SECRET_KEY
from microq_admin.utils import load_config
from microq_admin.tools import delete_claims
from microq_admin.projectsgenerator.qsmrprojects import (
    create_project, delete_project, is_project
)
from microq_admin.jobsgenerator.qsmrjobs import (
    main as jobsmain,
)

CONFIG_FILE = '/tmp/test_qsmr_snapshot_config.conf'
JOBS_FILE = '/tmp/test_qsmr_snapshot_jobs.txt'
ODIN_PROJECT = 'myodinproject'
WORKER = 'claimtestsworker'


def make_config(odinurl, microqurl):
    cfg = (
        'JOB_API_ROOT={}/rest_api\n'.format(microqurl)
        + 'JOB_API_USERNAME=admin\n'
        'JOB_API_PASSWORD=sqrrl\n'
        'ODIN_API_ROOT={}\n'.format(odinurl)
        + f'ODIN_SECRET={SECRET_KEY}\n'
    )
    with open(CONFIG_FILE, 'w') as out:
        out.write(cfg)


def make_projects(jobsproject, nojobsproject, config):
    # No conflict with other tests
    assert not is_project(jobsproject, config)
    assert not is_project(nojobsproject, config)

    # Make projects
    assert not create_project(jobsproject, config)
    assert not create_project(nojobsproject, config)


def make_jobs(jobsproject, number_of_jobs=6):
    scanids = [str(v) for v in range(number_of_jobs)]
    with open(JOBS_FILE, 'w') as out:
        out.write('\n'.join(scanids) + '\n')
    assert not jobsmain([
        jobsproject, ODIN_PROJECT, '--freq-mode', '1', '--jobs-file',
        JOBS_FILE,
    ], CONFIG_FILE)


def claim_jobs(jobsproject, config, number_of_jobs=3):
    claimurl = "{}/v4/{}/jobs/{}/claim".format(
        config['JOB_API_ROOT'], jobsproject, "{}",
    )
    fetchurl = "{}/v4/{}/jobs/fetch".format(
        config['JOB_API_ROOT'], jobsproject,
    )
    auth = (config['JOB_API_USERNAME'], config['JOB_API_PASSWORD'])
    jobids = []
    for _ in range(number_of_jobs):
        response = requests.get(fetchurl, auth=auth)
        response.raise_for_status()
        jobid = response.json()['Job']['JobID']
        response = requests.put(
            claimurl.format(jobid), auth=auth, json={'Worker': WORKER},
        )
        response.raise_for_status()
        jobids.append(jobid)
    return jobids


def fail_job(jobsproject, failid, config):
    url = "{}/v4/{}/jobs/{}/status".format(
        config['JOB_API_ROOT'], jobsproject, failid,
    )
    auth = (config['JOB_API_USERNAME'], config['JOB_API_PASSWORD'])
    response = requests.put(url, auth=auth, json={'Status': 'FAILED'})
    response.raise_for_status()


@pytest.fixture(scope='function')
def delete_claim_projects(odin_and_microq):

    make_config(*odin_and_microq)
    config = load_config(CONFIG_FILE)

    jobsproject = "claimsjobsproject"
    nojobsproject = "claimsnojobsproject"
    make_projects(jobsproject, nojobsproject, config)

    make_jobs(jobsproject)

    jobids = claim_jobs(jobsproject, config)
    assert jobids
    fail_job(jobsproject, jobids[0], config)

    yield jobsproject, nojobsproject

    # Cleanup
    assert not delete_project(jobsproject, config)
    assert not delete_project(nojobsproject, config)


def get_jobs_counts(project):
    config = load_config(CONFIG_FILE)
    url = "{}/v4/{}/jobs/count".format(config['JOB_API_ROOT'], project)
    response = requests.get(url)
    response.raise_for_status()
    claimed = response.json()['Counts'][0]['JobsClaimed']
    failed = response.json()['Counts'][0]['JobsFailed']
    url = "{}/v4/{}/jobs?status=available".format(
        config['JOB_API_ROOT'], project
    )
    response = requests.get(url)
    response.raise_for_status()
    available = len(response.json()['Jobs'])
    return available, claimed, failed


@pytest.mark.system
def test_bad_project_name(delete_claim_projects):
    assert (
        delete_claims.main(['claimsbadproject'], config_file=CONFIG_FILE)
        == "No project called claimsbadproject"
    )


@pytest.mark.system
def test_empty_project(delete_claim_projects):
    _, nojobsproject = delete_claim_projects
    assert (
        delete_claims.main([nojobsproject], config_file=CONFIG_FILE)
        == "Project {} has no jobs".format(nojobsproject)
    )


@pytest.mark.system
def test_make_failed_available(delete_claim_projects):
    project, _ = delete_claim_projects
    # Available, Claimed + Failed, Failed
    # Total of six jobs
    assert get_jobs_counts(project) == (3, 3, 1)
    assert not delete_claims.main([project], config_file=CONFIG_FILE)
    # Avaialbe is only a status so it's still 3 (claiming sets a status)
    # Deleting claim does not change status
    # The previously claimed deleted job is no longer claimed but still deleted
    # Total of 6 jobs
    assert get_jobs_counts(project) == (3, 2, 1)


@pytest.mark.system
def test_make_non_finished_avaialable(delete_claim_projects):
    project, _ = delete_claim_projects
    # Available, Claimed + Failed, Failed
    # Total of six jobs
    assert get_jobs_counts(project) == (3, 3, 1)
    assert not delete_claims.main(
        [project, '--force'], config_file=CONFIG_FILE,
    )
    # Avaialbe is only a status so it's still 3 (claiming sets a status)
    # Deleting claim does not change status
    # The previously claimed jobs (deletedd or not) are no long claimed
    # The failed still has that status
    # Total of six jobs
    assert get_jobs_counts(project) == (3, 0, 1)
