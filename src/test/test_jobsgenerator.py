# pylint: disable=W0212
import base64
import unittest
from io import BytesIO

import pytest
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from microq_admin.jobsgenerator import qsmrjobs
from microq_admin.jobsgenerator.scanids import ScanIDs


PROJECT_NAME = 'testproject'
ODIN_PROJECT = 'odinproject'
CONFIG_FILE = '/tmp/test_qsmr_snapshot_config.conf'
JOBS_FILE = '/tmp/test_qsmr_snapshot_jobs.txt'
SECRET = 'rc/lY+OQYq6mvI6tCfr+tQ=='


class BaseTest(unittest.TestCase):
    @staticmethod
    def _write_config(cfg):
        with open(CONFIG_FILE, 'w') as out:
            out.write(cfg)


class ResponseMock:
    def __init__(self, status_code):
        self.status_code = status_code


class TestConfigValidation(BaseTest):

    ARGS = [PROJECT_NAME, ODIN_PROJECT]

    def test_missing_value(self):
        """Test missing config values"""
        self._write_config(f'ODIN_SECRET={SECRET}\n')
        self.assertEqual(qsmrjobs.main(self.ARGS, CONFIG_FILE), 1)

        self._write_config((
            f'ODIN_SECRET={SECRET}\n'
            'ODIN_API_ROOT=http://example.com\n'
            'JOB_API_ROOT=http://example.com\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=\n'))
        self.assertEqual(qsmrjobs.main(self.ARGS, CONFIG_FILE), 1)

    def test_ok_config(self):
        """Test that ok config validates"""
        self._write_config((
            f'ODIN_SECRET={SECRET}\n'
            'ODIN_API_ROOT=http://example.com\n'
            'JOB_API_ROOT=http://example.com\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=testpw\n'))
        self.assertEqual(qsmrjobs.main(self.ARGS, CONFIG_FILE), 0)

    def test_bad_api_root(self):
        """Test bad api root url"""
        self._write_config((
            f'ODIN_SECRET={SECRET}\n'
            'ODIN_API_ROOT=example.com\n'
            'JOB_API_ROOT=http://example.com\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=testpw\n'))
        self.assertEqual(qsmrjobs.main(self.ARGS, CONFIG_FILE), 1)

        self._write_config((
            f'ODIN_SECRET={SECRET}\n'
            'ODIN_API_ROOT=http://example.com\n'
            'JOB_API_ROOT=http://example.com/\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=testpw\n'))
        self.assertEqual(qsmrjobs.main(self.ARGS, CONFIG_FILE), 1)


class TestProjectNameValidation(BaseTest):

    def test_project_names(self):
        """Test bad and good project names"""
        self._write_config((
            f'ODIN_SECRET={SECRET}\n'
            'ODIN_API_ROOT=http://example.com\n'
            'JOB_API_ROOT=http://example.com\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=testpw\n'))
        self.assertEqual(
            qsmrjobs.main(['test_project', ODIN_PROJECT], CONFIG_FILE), 1,
        )
        self.assertEqual(
            qsmrjobs.main(['1project', ODIN_PROJECT], CONFIG_FILE), 1,
        )
        self.assertEqual(
            qsmrjobs.main(['123', ODIN_PROJECT], CONFIG_FILE), 1,
        )
        self.assertEqual(
            qsmrjobs.main(['', ODIN_PROJECT], CONFIG_FILE), 1,
        )
        self.assertEqual(
            qsmrjobs.main([PROJECT_NAME, '1project'], CONFIG_FILE), 1,
        )

        self.assertEqual(
            qsmrjobs.main(['project', ODIN_PROJECT], CONFIG_FILE), 0,
        )
        self.assertEqual(
            qsmrjobs.main(['p123', ODIN_PROJECT], CONFIG_FILE), 0,
        )


class BaseTestAddJobs(BaseTest):

    @pytest.fixture(autouse=True)
    def jobs(self, odin_and_microq):
        odinurl, microqurl = odin_and_microq
        self._apiroot = '{}/rest_api'.format(odinurl)
        self._write_config((
            f'ODIN_SECRET={SECRET}\n'
            'ODIN_API_ROOT={}/rest_api\n'.format(odinurl)
            + 'JOB_API_ROOT=http://example.com\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=testpw\n'))

        self._mock_post_method = self._get_mock_post_method()
        orig_post_method = qsmrjobs.AddQsmrJobs._post_jobs
        orig_get_token = qsmrjobs.AddQsmrJobs.get_token
        qsmrjobs.AddQsmrJobs._post_jobs = self._mock_post_method
        qsmrjobs.AddQsmrJobs.get_token = lambda _: None
        yield
        qsmrjobs.AddQsmrJobs._post_jobs = orig_post_method
        qsmrjobs.AddQsmrJobs.get_token = orig_get_token

    @staticmethod
    def _get_mock_post_method():
        def mock_post_method(self, job):  # pylint: disable=unused-argument
            mock_post_method.jobs.append(job)
            return ResponseMock(201)
        mock_post_method.jobs = []
        return mock_post_method

    @staticmethod
    def _write_scanids(scanids):
        with open(JOBS_FILE, 'w') as out:
            out.write('\n'.join(scanids) + '\n')


class TestAddJobsFromFile(BaseTestAddJobs):

    def test_add_jobs(self):
        """Test to add jobs from a scan id file"""
        self._write_scanids(list(map(str, range(1500))))
        exit_code = qsmrjobs.main([
            PROJECT_NAME, ODIN_PROJECT, '--freq-mode', '1', '--jobs-file',
            JOBS_FILE,
        ], CONFIG_FILE)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(self._mock_post_method.jobs), 2)
        self.assertEqual(len(self._mock_post_method.jobs[0]), 1000)
        self.assertEqual(self._mock_post_method.jobs[1][-1]['id'], '1:1499')

    def test_filter_jobs(self):
        """Test skipping of scan ids"""
        adder = qsmrjobs.AddQsmrJobs(
            PROJECT_NAME,
            ODIN_PROJECT,
            self._apiroot,
            f"{SECRET}",
            "http://example.com",
            "testuser",
            "testpw")
        scanids = list(map(str, range(15)))
        freqmode = 1
        skip = 6
        list_of_jobs = adder.filter_jobs(scanids, freqmode, skip)
        self.assertEqual(len(list_of_jobs), 15 - skip)

    def test_skip(self):
        """Test skipping of scan ids in the file"""
        self._write_scanids(list(map(str, range(15))))
        skip = 6
        exit_code = qsmrjobs.main([
            PROJECT_NAME, ODIN_PROJECT, '--freq-mode', '1', '--jobs-file',
            JOBS_FILE, '--skip', str(skip),
        ], CONFIG_FILE)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(self._mock_post_method.jobs), 1)
        self.assertEqual(len(self._mock_post_method.jobs[0]), 15 - skip)


@pytest.mark.system
class TestAddVds(BaseTestAddJobs):

    def test_add_jobs(self):
        """Test to add all scan ids in the vds"""
        exit_code = qsmrjobs.main([
            PROJECT_NAME, ODIN_PROJECT, '--freq-mode', '13', '--vds',
        ], CONFIG_FILE)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(self._mock_post_method.jobs), 15)
        self.assertEqual(len(self._mock_post_method.jobs[0]), 1000)


@pytest.mark.system
class TestAddAll(BaseTestAddJobs):

    def test_add_jobs(self):
        """Test to add all scan ids"""
        exit_code = qsmrjobs.main([
            PROJECT_NAME, ODIN_PROJECT, '--freq-mode', '1', '--all',
            '--end-day', '2015-01-11',
        ], CONFIG_FILE)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(self._mock_post_method.jobs), 5)
        self.assertEqual(len(self._mock_post_method.jobs[0]), 1000)


class TestRenewToken(BaseTestAddJobs):

    @staticmethod
    def _get_mock_post_method():
        def mock_post_method(self, job):  # pylint: disable=unused-argument
            if not mock_post_method.called:
                mock_post_method.called = True
                return ResponseMock(401)
            mock_post_method.jobs.append(job)
            return ResponseMock(201)

        mock_post_method.jobs = []
        mock_post_method.called = False
        return mock_post_method

    def test_renew_token(self):
        """Test retry because of renewal of auth token"""
        self._write_scanids(list(map(str, range(15))))
        exit_code = qsmrjobs.main([
            PROJECT_NAME, ODIN_PROJECT, '--freq-mode', '1', '--jobs-file',
            JOBS_FILE,
        ], CONFIG_FILE)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(self._mock_post_method.jobs), 1)


class TestJobAPIFailure(BaseTestAddJobs):

    @staticmethod
    def _get_mock_post_method():
        def mock_post_method(self, job):  # pylint: disable=unused-argument
            if mock_post_method.jobs:
                raise Exception('Failed!')
            mock_post_method.jobs.append(job)
            return ResponseMock(201)
        mock_post_method.jobs = []
        mock_post_method.called = False
        return mock_post_method

    def test_failure(self):
        """Test exception of post of job"""
        self._write_scanids(list(map(str, range(1500))))
        exit_code = qsmrjobs.main([
            PROJECT_NAME, ODIN_PROJECT, '--freq-mode', '1', '--jobs-file',
            JOBS_FILE,
        ], CONFIG_FILE)
        self.assertEqual(exit_code, 1)
        self.assertEqual(len(self._mock_post_method.jobs), 1)
        self.assertEqual(len(self._mock_post_method.jobs[0]), 1000)


@pytest.mark.system
class TestGenerateIds(BaseTestAddJobs):

    def test_generate_all(self):
        """Test to generate all available scan ids for a freqmode"""
        scanids = ScanIDs(self._apiroot)

        ids = list(scanids.generate_all(1))
        self.assertGreater(len(ids), 0)
        ids2 = list(scanids.generate_all(1, end_day="2015-01-11"))
        self.assertGreater(len(ids), len(ids2))

    def test_generate_vds(self):
        scanids = ScanIDs(self._apiroot)

        ids = list(scanids.generate_vds(13))
        self.assertGreater(len(ids), 0)


def test_encrypt_returns_string():
    secret = base64.b64encode(get_random_bytes(16)).decode("utf8")
    assert isinstance(qsmrjobs.encrypt('hello', secret), str)


def decode(msg, secret):
    bytes = BytesIO()
    bytes.write(base64.urlsafe_b64decode(msg))
    bytes.flush()
    bytes.seek(0)
    nonce, tag, ciphertext = [bytes.read(x) for x in (16, 16, -1)]
    cipher = AES.new(base64.b64decode(secret.encode()), AES.MODE_EAX, nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf8')


def test_encrypt_perserves_message():
    secret = base64.b64encode(get_random_bytes(16)).decode("utf8")
    payload = 'hello'
    msg = qsmrjobs.encrypt(payload, secret)
    assert decode(msg, secret) == payload
