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

parser = argparse.ArgumentParser(
    description="""MicroQ Admin""",
    prog=PROG,
    epilog=EPI,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    'SERVICE',
    help="""The service to run.

    For more help on a particular service do `SERVICE --help`
    """,
    choices=['qsmrjobs', 'qsmrprojects', 'delete-claims'],
)

if len(sys.argv) > 2 and not sys.argv[1].startswith('-'):
    myargs = [sys.argv[1]]
else:
    myargs = None

args = parser.parse_args(myargs)
service = args.SERVICE.lower().strip()
SERVICE_ARGS_START = 2
service_name = "{} {}".format(PROG, service)

if service is None:
    exit("Failed to supply service")

service_args = sys.argv[SERVICE_ARGS_START:]
if service == 'delete-claims':
    exit(delete_claims.main(service_args, prog=service_name))
elif service == "qsmrjobs":
    exit(qsmrjobs.main(service_args, prog=service_name))
elif service == "qsmrprojects":
    exit(qsmrprojects.main(service_args, prog=service_name))
else:
    exit("Invalid service '{}'".format(service))
