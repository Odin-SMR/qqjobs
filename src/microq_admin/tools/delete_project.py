import argparse
import requests
import json
from ..projectsgenerator.qsmrprojects import (
    delete_project, is_project
)
from ..jobsgenerator.qsmrjobs import (
    encrypt
)
from ..tools.delete_claims import(
    get_project_jobs, get_project_uri_and_auth
)
from ..utils import load_config, validate_config


DESCRIPTION = """Delete Project

Deletes a uservice project and associated processed L2 data
for this project.
"""


class BadProjectError(ValueError):
    pass


class InvalidConfig(Exception):
    pass


def delete_uservice_project(project, config):
    if delete_project(project, config):
        raise BadProjectError(
            "Project {} could not be deleted".format(project))
    return 0


def get_config(config_file):
    config = load_config(config_file)
    if not validate_config(config):
        raise(InvalidConfig('Invalid config file.'))
    return config


def get_odin_project_name(project, project_uri, config):
    '''returns the associated odinproject of a given
       uservice project
    '''
    try:
        response = requests.get(project_uri)
    except requests.ConnectionError:
        raise BadProjectError(
            'Could not connect to MicroQ service, '
            'validate that the url is correct '
            'and that you have internet connection.'
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as err:
        if response.status_code == 404:
            raise BadProjectError("No project called {}".format(project))
        raise BadProjectError(str(err))

    return response.json()['Name']


def delete_level2_data(jobs, odinproject, config):
    delete_successful = True
    auth = (config['ODIN_API_ROOT'], config['ODIN_SECRET'])
    for job in jobs:
        url_string = encrypt(json.dumps({
            'ScanID': int(job["Id"].split(":")[-1]),
            'FreqMode': int(job["Id"].split(":")[0]),
            'Project': odinproject
        }), config['ODIN_SECRET'])
        try:
            response = requests.delete(
                "{0}?d={1}".format(
                    job["URLS"]["URL-Result"].split("/development")[0],
                    url_string
                ),
                auth=auth
            )
        except requests.ConnectionError:
            raise BadProjectError(
                'Could not connect to odin-api service, '
                'validate that you have internet connection.'
            )
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            # accept and continue but raise later
            delete_successful = False

    if not delete_successful:
        raise BadProjectError(
            'Could not delete all Level2 data'
        )
    return 0


def delete_project_data(project, config_file):

    try:
        config = get_config(config_file)
    except InvalidConfig as err:
        return str(err)

    project_uri, _ = get_project_uri_and_auth(project, config)

    try:
        odinproject = get_odin_project_name(project, project_uri, config)
    except BadProjectError as err:
        return str(err)

    try:
        jobs = get_project_jobs(project, project_uri, config)
    except BadProjectError as err:
        return str(err)

    try:
        delete_level2_data(jobs, odinproject, config)
    except BadProjectError as err:
        return str(err)

    try:
        delete_uservice_project(project, config)
    except BadProjectError as err:
        return str(err)

    return 0


def main(argv=None, config_file=None, prog=None):
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'USERVICE_PROJECT',
        help="""The uservice project for which to delete jobs"""
    )
    args = parser.parse_args(argv)
    return delete_project_data(args.USERVICE_PROJECT, config_file)
