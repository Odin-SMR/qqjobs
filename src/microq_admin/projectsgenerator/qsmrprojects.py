from sys import stderr
from datetime import datetime, timedelta, date
import argparse
import requests

from ..utils import load_config, validate_config, validate_project_name

DESCRIPTION = ("Add a processing project to the microq job service.\n")


def make_argparser(prog):
    """argument parser setup"""
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
    parser.add_argument('PROCESSING_IMAGE_URL', help=(
        'url to the worker processing image'))
    parser.add_argument(
        '--deadline',
        help=(
            'The desired deadline of the project (yyyy-mm-dd).'
            'Default value is 10 days from now. However, this parameter '
            'is used to set the priority of the project and the actual '
            'deadline can not be guaranteed.'
        ),
        default=str(date.today() + timedelta(days=10)),
    )
    return parser


def is_project(project, config):
    """Project should not already exists"""
    url_project = "{}/{}/{}".format(
        config['JOB_API_ROOT'],
        config.get('JOB_API_VERSION', 'v4'),
        project,
    )
    if requests.get(url_project).status_code == 200:
        return True
    return False


def validate_deadline(deadline):
    """validate deadline"""
    if datetime.strptime(deadline, "%Y-%m-%d") < datetime.utcnow():
        return False
    return True


def create_project(project, config, args=None):
    """Add a project to microq job service"""
    url_project = "{}/{}/{}".format(
        config['JOB_API_ROOT'],
        config.get('JOB_API_VERSION', 'v4'),
        project,
    )
    if args:
        json = {
            'processing_image_url': args.PROCESSING_IMAGE_URL,
            'deadline': args.deadline,
            'name': args.ODIN_PROJECT,
        }
    else:
        json = None

    request = requests.put(
        url_project,
        auth=(config['JOB_API_USERNAME'], config['JOB_API_PASSWORD']),
        json=json)
    if request.status_code != 201:
        stderr.write((
            'Project could not be created'))
        return 1
    return 0


def delete_project(project, config):
    """Delete a project of microq servise"""
    url_project = "{}/{}/{}".format(
        config['JOB_API_ROOT'],
        config.get('JOB_API_VERSION', 'v4'),
        project,
    )
    response = requests.delete(
        url_project,
        auth=(config['JOB_API_USERNAME'], config['JOB_API_PASSWORD']),
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        return 1
    return 0


def main(args=None, config_file=None, prog=None):
    """main function"""
    args = make_argparser(prog).parse_args(args)
    if not validate_project_name(args.PROJECT_NAME):
        stderr.write((
            'Project name must only contain ascii letters and digits and '
            'start with an ascii letter\n'))
        return 1
    if not validate_deadline(args.deadline):
        stderr.write((
            'Project deadline can not be earlier than today\n'))
        return 1
    config = load_config(config_file)
    if not validate_config(config):
        return 1
    if is_project(args.PROJECT_NAME, config):
        stderr.write((
            'Project {0} already exists.\n'
            'Change PROJECT_NAME!\n'.format(args.PROJECT_NAME)))
        return 1
    create_project(args.PROJECT_NAME, config, args)
    return 0
