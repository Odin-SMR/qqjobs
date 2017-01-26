# Processing jobs generator

The jobs generator is used to add a list of qsmr processing jobs to the
microq service.

The application needs these environment variables to be able to communicate
with the microq service api and to generate correct job result target urls to
the cps api:

    export JOB_API_ROOT=https://example.com/job_api
    export JOB_API_USERNAME=<username>
    export JOB_API_PASSWORD=<password>
    expost ODIN_API_ROOT=https://example.com/odin_api
    export ODIN_API_SECRET=<secret encryption key>

The environment could for example be provided by adding the variables to a
config file and then source that file before calling the jobs generator:

    source config_file.conf

## Installation

Install the application by calling the install script:

    ./install.sh

This will install the jobs generator and its dependencies in a virtual
environment.

## Usage

The jobs generator takes these arguments:

- Project name: The project name.
- Odin project name: The project name used in the odin api.
- Jobs file: Path to a file that lists the job ids that should be added to the
  microq service.

Example usage:

    # Load environment variables
    source config_file.conf
    # Activate the virtual env
    source env/bin/activate
    # Add jobs to the queue
    jobsgenerator project_name odin_project /path/to/scanids.txt

The `scanids.txt` should contain one scan id per row:

    2342353234
    3253253534
    ...

## Resume after failure

Sometimes the job api can timeout, which will break the script.
It will then print this message:

    Exiting, you can try to call jobsgenerator again with --skip=X

It is then possible to continue from the scan id that failed with:

    jobsgenerator project_name odin_project /path/to/scanids.txt --skip=X

## Processing status and results

The processing status for your project can be seen in the microq service web
interface:
`http://example.com/<projectname>`

The processing result data can be seen in the odin api:
`http://example.com/odin_api/v5/level2/development/<odin_project_name>/`
