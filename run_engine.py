import os
import sys
import argparse
#
# to connect to charon we are using the standard NGI routines
#
from ngi_pipeline.database.classes import CharonSession, CharonError
#
# the subprocess32 module is recommended to use in POSIX systems (i.e. Linux) for python 2.7
#
if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

def cli_args():
    parser = argparse.ArgumentParser(description='Running a sample nextflow script with a given project ID')
    parser.add_argument('--id', dest='project_id', action='store', help='Project ID like P321', required=True)
    return parser.parse_args()

def main():
    args = cli_args()
    
    cs = CharonSession()
    cs.project_update(args.project_id,best_practice_analysis="hello_engine")
    # it is actually picking up stdout and stderr as well
    output = subprocess.check_output(["./nextflow", "run", "hello-ga.nf"])
    print "The output is:"
    print output
    print "done"


if __name__ == "__main__":
    main()
