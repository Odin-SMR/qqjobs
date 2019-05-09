import pytest

from microq_admin import utils

CONFIG_FILE = '/tmp/test_micrqadmin_utils.conf'


@pytest.fixture
def config_file():
    with open(CONFIG_FILE, 'w') as fp:
        fp.write(
            'ODIN_SECRET=adsfasree\n'
            'ODIN_API_ROOT=http://example.com\n'
            'JOB_API_ROOT=http://example2.com\n'
            'JOB_API_USERNAME=testuser\n'
            'JOB_API_PASSWORD=testpw\n'
        )
    yield CONFIG_FILE


@pytest.fixture
def config():
    return {
        'ODIN_SECRET': 'adsfasree',
        'ODIN_API_ROOT': 'http://example.com',
        'JOB_API_ROOT': 'http://example2.com',
        'JOB_API_USERNAME': 'testuser',
        'JOB_API_PASSWORD': 'testpw',
    }


def test_load_config(config_file, config):
    assert utils.load_config(config_file) == config


def test_validate_config(config):
    assert utils.validate_config(config)


@pytest.mark.parametrize('key', (
    'ODIN_SECRET', 'ODIN_API_ROOT', 'JOB_API_ROOT', 'JOB_API_USERNAME',
    'JOB_API_PASSWORD',
))
def test_validate_config_missing_key(config, key):
    del config[key]
    assert not utils.validate_config(config)


@pytest.mark.parametrize('urlkey', ('ODIN_API_ROOT', 'JOB_API_ROOT'))
def test_validate_config_invalid_urls(config, urlkey):
    # Removes 'http://'
    config[urlkey] = config[urlkey][7:]
    assert not utils.validate_config(config)


def test_validate_config_adding_invalid_key(config):
    config['BAD'] = 'smirk'
    assert not utils.validate_config(config)


def test_validate_config_including_optionals(config):
    config['JOB_API_VERSION'] = 'v55'
    assert utils.validate_config(config)


def test_validate_project_name():
    assert utils.validate_project_name('project44')


@pytest.mark.parametrize('name', (
    None, '', 5, '5proj', 'test-55', 'test me #',
))
def test_invalidate_bad_project_names(name):
    assert not utils.validate_project_name(name)
