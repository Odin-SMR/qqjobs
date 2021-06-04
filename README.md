# Processing jobs generator

Run `./microq_admin.sh --help` for instrucitons.

The settings and credentials file should be located in `~/odin.cfg`.

## Development setup

The `data/` directory comes from a different repository added as a submodule.

To clone the qqjobs repository with the submodule, you can use:

    git clone --recursive https://github.com/Odin-SMR/qqjobs.git

If you already cloned the repository without the submodule, or if you
want to update the submodule:

    git submodule update --init --recursive

## Usage

See the respective service for usage, e.g. `./microq_admin.sh qsmrjobs --help`.

## Resume after failure

Sometimes the job api can timeout, which will break the script.
It will then print this message:

    Exiting, you can try to call jobsgenerator again with --skip=X

It is then possible to continue from the scan id that failed with:

    ./microq_admin qsmrjobs project_name odin_project /path/to/scanids.txt --skip=X

## Processing status and results

The processing status for your project can be seen in the microq service web
interface:
`http://example.com/<projectname>`

The processing result data can be seen in the odin api:
`http://example.com/odin_api/v5/level2/development/<odin_project_name>/`
