from datetime import timedelta, date

import pytest

from microq_admin.projectsgenerator import qsmrprojects


PROJECT_NAME = 'dummyproject'
ODIN_PROJECT = 'dummyodinproject'
PROCESSING_IMAGE_URL = '"docker2.molflow.com/devops/qsmr__:yymmdd"'
CONFIG_FILE = '/tmp/test_qsmr_snapshot_config.conf'


def write_config(cfg):
    with open(CONFIG_FILE, 'w') as out:
        out.write(cfg)


@pytest.mark.system
class TestConfigValidation:
    """test config validation"""
    ARGS = [
        PROJECT_NAME,
        ODIN_PROJECT,
        PROCESSING_IMAGE_URL,
    ]

    def test_missing_value(self, odin_and_microq):
        """Test missing config values"""
        write_config(
            'JOB_API_ROOT=http://example.com\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=\n'
            'ODIN_API_ROOT=http://example.com\n'
            'ODIN_SECRET=myseeecret\n'
        )
        assert qsmrprojects.main(self.ARGS, CONFIG_FILE) == 1

    def test_ok_config(self, odin_and_microq):
        _, microqurl = odin_and_microq
        write_config(
            'JOB_API_ROOT={}/rest_api\n'.format(microqurl)
            + 'JOB_API_USERNAME=admin\n'
            'JOB_API_PASSWORD=sqrrl\n'
            'ODIN_API_ROOT=http://example.com\n'
            'ODIN_SECRET=myseeecret\n'
        )
        config = qsmrprojects.load_config(CONFIG_FILE)
        qsmrprojects.delete_project(PROJECT_NAME, config)
        assert qsmrprojects.main(self.ARGS, CONFIG_FILE) == 0

    def test_bad_api_root(self, odin_and_microq):
        """Test bad api root url"""
        write_config(
            'JOB_API_ROOT=http://example.com/\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=testpw\n'
            'ODIN_API_ROOT=http://example.com\n'
            'ODIN_SECRET=myseeecret\n'
        )
        assert qsmrprojects.main(self.ARGS, CONFIG_FILE) == 1


@pytest.mark.system
class TestAddProjects:
    """test that project can be cretated"""
    ARGS = [
        PROJECT_NAME,
        ODIN_PROJECT,
        PROCESSING_IMAGE_URL,
    ]

    @pytest.fixture(autouse=True)
    def withproject(self, odin_and_microq):
        _, microqurl = odin_and_microq
        write_config(
            'JOB_API_ROOT={}/rest_api\n'.format(microqurl)
            + 'JOB_API_USERNAME=admin\n'
            'JOB_API_PASSWORD=sqrrl\n'
            'ODIN_API_ROOT=http://example.com\n'
            'ODIN_SECRET=myseeecret\n'
        )

    def test_validate_deadline(self):
        """test that deadline must be in the future"""
        past_date = str(date.today() + timedelta(days=-10))
        assert qsmrprojects.validate_deadline(past_date) is False
        future_date = str(date.today() + timedelta(days=10))
        assert qsmrprojects.validate_deadline(future_date) is True

    def test_create_project(self):
        """test that a project can be created"""
        config = qsmrprojects.load_config(CONFIG_FILE)
        qsmrprojects.delete_project(PROJECT_NAME, config)
        assert qsmrprojects.is_project(PROJECT_NAME, config) is False
        qsmrprojects.main(self.ARGS, CONFIG_FILE)
        assert qsmrprojects.is_project(PROJECT_NAME, config) is True
        qsmrprojects.delete_project(PROJECT_NAME, config)
