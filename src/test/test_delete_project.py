import pytest
import requests
import json
from datetime import date, timedelta

from .utils import SECRET_KEY
from microq_admin.utils import load_config
from microq_admin.projectsgenerator.qsmrprojects import (
    main as create_project_main
)
from microq_admin.jobsgenerator.qsmrjobs import (
    main as jobsmain, encrypt
)
from microq_admin.tools.delete_project import (
    main as delete_project_data_main,
    delete_uservice_project,
    BadProjectError
)


CONFIG_FILE = '/tmp/test_qsmr_snapshot_config.conf'
JOBS_FILE = '/tmp/test_qsmr_snapshot_jobs.txt'
ODIN_PROJECT = 'myodinproject'
WORKER = 'testworkerimage'


def make_config(odinurl, microqurl):
    cfg = (
        'JOB_API_ROOT={}/rest_api\n'.format(microqurl)
        + 'JOB_API_USERNAME=admin\n'
        'JOB_API_PASSWORD=sqrrl\n'
        'ODIN_API_ROOT={}/rest_api\n'.format(odinurl)
        + f'ODIN_SECRET={SECRET_KEY}\n'
    )
    with open(CONFIG_FILE, 'w') as out:
        out.write(cfg)


def make_jobs(jobsproject, number_of_jobs=6):
    scanids = [str(v) for v in range(number_of_jobs)]
    with open(JOBS_FILE, 'w') as out:
        out.write('\n'.join(scanids) + '\n')
    assert not jobsmain([
        jobsproject, ODIN_PROJECT, '--freq-mode', '1', '--jobs-file',
        JOBS_FILE,
    ], CONFIG_FILE)


l2i_prototype = {
    "BLineOffset": [list(range(12)) for _ in range(4)],
    "ChannelsID": [list(range(639))],
    "FitSpectrum": [list(range(639))],
    "FreqMode": 0,
    "FreqOffset": 0.0,
    "InvMode": "",
    "LOFreq": [list(range(12))],
    "MinLmFactor": 0,
    "PointOffset": 0.0,
    "Residual": 0.0,
    "STW": [[0] for _ in range(12)],
    "ScanID": 0,
    "Tsat": 0.0,
    "SBpath": 0.0,
}

l2_prototype = {
    'AVK': [[0.0]],         # (2-D array of doubles)
    'Altitude': [0.0],      # (array of doubles)
    'Apriori': [0.0],       # (array of doubles)
    'ErrorNoise': [0.0],    # (array of doubles)
    'ErrorTotal': [0.0],    # (array of doubles)
    'FreqMode': 0,          # (int)
    'InvMode': '',          # (string)
    'Lat1D': 0.0,           # (double)
    'Latitude': [0.0],      # (array of doubles)
    'Lon1D': 0.0,           # (double)
    'Longitude': [0.0],     # (array of doubles)
    'MJD': 0.0,             # (double)
    'MeasResponse': [0.0],  # (array of doubles)
    'Pressure': [0.0],      # (array of doubles)
    'Product': '',          # (string)
    'Quality': None,        # (?)
    'ScanID': 0,            # (int)
    'Temperature': [0.0],   # (array of doubles)
    'VMR': [0.0]            # (array of doubles)
}


@pytest.mark.system
def test_bad_name_raises(odin_and_microq):
    make_config(*odin_and_microq)
    jobsproject = "nonexistingproject"
    assert (
        delete_project_data_main([jobsproject], CONFIG_FILE)
        == "No project called nonexistingproject"
    )


def test_invalid_config_raises():
    jobsproject = "nonexistingproject"
    with open(CONFIG_FILE, 'w') as out:
        out.write('configerror=1\n')
    assert (
        delete_project_data_main([jobsproject], CONFIG_FILE)
        == "Invalid config file."
    )


@pytest.mark.system
def test_delete_uservice_project_rasises(odin_and_microq):
    make_config(*odin_and_microq)
    config = load_config(CONFIG_FILE)
    jobsproject = "non/existing/project"
    with pytest.raises(BadProjectError):
        delete_uservice_project(jobsproject, config)


@pytest.mark.system
def test_delete_data_in_project(odin_and_microq):
    make_config(*odin_and_microq)
    config = load_config(CONFIG_FILE)
    jobsproject = "mytestproject"

    create_project_main([
        jobsproject,
        ODIN_PROJECT,
        WORKER,
        '--deadline',
        str(date.today() + timedelta(days=10))
    ], CONFIG_FILE)

    make_jobs(jobsproject)

    jobsurl = "{}/v4/{}/jobs".format(
        config['JOB_API_ROOT'], jobsproject,
    )
    auth = (config['JOB_API_USERNAME'], config['JOB_API_PASSWORD'])
    response = requests.get(jobsurl, auth=auth)
    response.raise_for_status()

    # post fake l2 data to odin-api
    auth = (config['ODIN_API_ROOT'], config['ODIN_SECRET'])
    for job in response.json()['Jobs']:
        freqmode = int(job["Id"].split(":")[0])
        scanid = int(job["Id"].split(":")[-1])
        data = {
            "L2": l2_prototype,
            "L2I": l2i_prototype,
            "L2C": 'dummystring',
        }
        data["L2"]['ScanID'] = scanid
        data["L2"]['FreqMode'] = freqmode
        data["L2I"]['ScanID'] = scanid
        data["L2I"]['FreqMode'] = freqmode
        url_string = encrypt(json.dumps({
            'ScanID': scanid,
            'FreqMode': freqmode,
            'Project': ODIN_PROJECT
        }), config['ODIN_SECRET'])
        post_response = requests.post(
            "{0}?d={1}".format(
                job["URLS"]["URL-Result"].split("/development")[0],
                url_string
            ),
            headers={'Content-Type': "application/json"},
            json=data,
            auth=auth
        )
        post_response.raise_for_status()

    # check that l2 data are present
    for job in response.json()['Jobs']:
        get_response = requests.get(
            "{0}/{1}".format(job['URLS']["URL-Result"], "L2i")
        )
        get_response.raise_for_status()

    delete_project_data_main([jobsproject], CONFIG_FILE)

    # check l2 data are removed
    for job in response.json()['Jobs']:
        get_response = requests.get(
            "{0}/{1}".format(job['URLS']["URL-Result"], "L2i")
        )
        assert get_response.status_code == 404

    # check no data in jobproject
    auth = (config['JOB_API_USERNAME'], config['JOB_API_PASSWORD'])
    response = requests.get(jobsurl, auth=auth)
    assert len(response.json()['Jobs']) == 0
