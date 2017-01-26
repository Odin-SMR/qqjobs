# Base python repo

This repo can be used as a starting point for a new repo.

Included in the base repo:

- Archanist config.
- pytest base config.
- Base python requirements.
- Base test script: `run_all_tests.sh`.
- Base build script: `build.sh`
- Bootstrap script.

The test script and build script are used by the jenkins template jobs.

TODO: Link to documentation for setting up triggers in phabricator and jobs
in jenkins.

## Usage

- Create a new repo in phabricator.
- Clone this repository.
- Run the bootstrap script with the path to the new repo as argument:

        ./bootstrap_repo.sh https://phabricator.molflow.com/diffustion/<repo>/<name>.git
