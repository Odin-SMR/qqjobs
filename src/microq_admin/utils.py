from sys import stderr

CONFIG_PATH = '/odin.cfg'

CONFIG_FILE_DOCS = """The configuration file should contain these settings:
ODIN_API_ROOT=https://example.com/odin_api
ODIN_SECRET=<secret encryption key>
JOB_API_ROOT=https://example.com/job_api
JOB_API_USERNAME=<username>
JOB_API_PASSWORD=<password>

It may contain:
JOB_API_VERSION=v4
"""


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

    optional = ['JOB_API_VERSION']

    if not set(config.keys()).issubset(required + optional):
        error("Config contains too invalid settings: {}".format(
            set(config.keys()).difference(required + optional)
        ))
    return error.ok


def load_config(config_file=None):
    if config_file is None:
        config_file = CONFIG_PATH
    with open(config_file) as inp:
        conf = dict(row.strip().split('=') for row in inp if row.strip())
    for k, v in conf.items():
        conf[k] = v.strip('"')
    return conf
