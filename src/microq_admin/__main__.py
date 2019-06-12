import argparse
import sys

from .tools import delete_claims
from .jobsgenerator import qsmrjobs
from .projectsgenerator import qsmrprojects
from .utils import CONFIG_FILE_DOCS

PROG = "microq_admin.sh"
EPI = """A configuration file is needed and will be mounted from `~/odin.cfg`.

{}
""".format(CONFIG_FILE_DOCS)

_parser = argparse.ArgumentParser(
    description="""MicroQ Admin""",
    prog=PROG,
    epilog=EPI,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
_parser.add_argument(
    'SERVICE',
    help="""The service to run.

    For more help on a particular service do `SERVICE --help`
    """,
    choices=['qsmrjobs', 'qsmrprojects', 'delete-claims', 'delete-project'],
)

if len(sys.argv) > 2 and not sys.argv[1].startswith('-'):
    _myargs = [sys.argv[1]]
else:
    _myargs = None

_args = _parser.parse_args(_myargs)
_service = _args.SERVICE.lower().strip()
_service_args_start = 2
_service_name = "{} {}".format(PROG, _service)

if _service is None:
    exit("Failed to supply service")

_service_args = sys.argv[_service_args_start:]
if _service == 'delete-claims':
    exit(delete_claims.main(_service_args, prog=_service_name))
elif _service == "qsmrjobs":
    exit(qsmrjobs.main(_service_args, prog=_service_name))
elif _service == "qsmrprojects":
    exit(qsmrprojects.main(_service_args, prog=_service_name))
elif _service == 'delete-project':
    exit(delete_project.main(_service_args, prog=_service_name))
else:
    exit("Invalid service '{}'".format(_service))
