import os
import sys
#
# the subprocess32 module is recommended to use in POSIX systems (i.e. Linux) for python 2.7
#
if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

# it is actually picking up stdout and stderr as well
output = subprocess.check_output(["./nextflow", "run", "hello-ga.nf"])


print "The output is:"
print output
print "done"
