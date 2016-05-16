from __future__ import print_function

import collections
import glob
import os
import re
import shlex
import shutil
import subprocess
import time
import datetime

from ngi_pipeline.conductor.classes import NGIProject
from ngi_pipeline.database.classes import CharonSession, CharonError
from ngi_pipeline.log.loggers import log_process_non_blocking, minimal_logger
from ngi_pipeline.utils.classes import with_ngi_config
from ngi_pipeline.utils.slurm import get_slurm_job_status

import subprocess
import pprint

LOG = minimal_logger(__name__)

@with_ngi_config
def analyze(project, sample,
            exec_mode="local", 
            restart_finished_jobs=False,
            restart_running_jobs=False,
            keep_existing_data=False,
            level="sample",
            genotype_file=None,
            config=None, config_file_path=None,
            generate_bqsr_bam=False):
    """Analyze data at the sample level.

    :param NGIProject project: the project to analyze
    :param NGISample sample: the sample to analyzed
    :param str exec_mode: "sbatch" or "local" (local not implemented)
    :param bool restart_finished_jobs: Restart jobs that are already done (have a .done file)
    :param bool restart_running_jobs: Kill and restart currently-running jobs
    :param str level: The level on which to perform the analysis ("sample" or "genotype")
    :param str genotype_file: The path to the genotype file (only relevant for genotype analysis)
    :param dict config: The parsed configuration file (optional)
    :param str config_file_path: The path to the configuration file (optional)

    :raises ValueError: If exec_mode is an unsupported value
    """
    #TODO add trace_tracking_path somehow
    dir_prefix = project.base_path + "/DATA/" + project.project_id + "/"
    LOG.info("Processing "+project.project_id + " at " + dir_prefix)
    # in the debugger you can have something like
    # import pdb
    # pdb.set_trace()
    # ...
    # print project.samples['P697_001'].libpreps['A'].seqruns['908254_ST-E00205_2662_BBZZHATCXX'].fastq_files
    # below is how to traverse the project -> samples -> libpreps -> seqruns tree to find all the FASTQs you want to feed into the workflow
    # this is only a logging info - get rid of it in your real code
    #
    # for some reason the R2 is the first and R1 is the second in the fastq list
    # 
    sample_names = []
    for s in project.samples.keys():
        for l in project.samples[s].libpreps.keys():
            for sr in project.samples[s].libpreps[l].seqruns.keys():
                for fq in project.samples[s].libpreps[l].seqruns[sr].fastq_files:
                    sample_names.append( s + "/" + l + "/" + sr + "/"+fq+" " )
    for sns in sample_names:
        LOG.info("Sample: " + dir_prefix + sns)
    # end of demo log code
    #
    # To launch  demo for each sample we are traversing the project object to collect all the fastq pairs
    #
    fastq_pairs = get_sample_fastq_pairs(sample,dir_prefix)
    cs = CharonSession()
    #cs.project_update(args.project_id,best_practice_analysis="hello_engine")
    # it is actually picking up stdout and stderr as well 
    #output = subprocess.check_output(["ls", "-l",fastq_pairs[0]])
    output = subprocess.check_output(["/home/szilva/dev/hello-ngi-engine/nextflow", "run", "/home/szilva/dev/hello-ngi-engine/hello-ga.nf","--reads1",fastq_pairs[0],"--reads2",fastq_pairs[1],"-with-trace","/home/szilva/dev/hello-ngi-engine/hello.trace","--refbase","/home/szilva/dev/hello-ngi-engine/a2014205/reference/"])
    import pdb
    pdb.set_trace()
    LOG.info("The output is:" + output)
    LOG.info("Done - bye")
    return 0

def get_sample_fastq_pairs(sample,prefix):
    ''' This is a sample code how to get the FASTQ pairs using only the NGISample object
        In fact we are assuming there is only a single libprep and a single run.
        For multiple libpreps/runs belonging to the same sample you have to do something 
        more sophisticated.
        Note, it is the R2 that comes first in the original class structure, we are 
        returning with the filenames in the correct order.
    '''
#    import pdb
#    pdb.set_trace()
    lp = sample.libpreps.keys()[0]              # assuming a single libprep
    sr = sample.libpreps[lp].seqruns.keys()[0]  # ditto a single run
    sample_prefix = prefix + str(sample) + "/" + str(lp) + "/" + sr + "/"   # concatenate with directory prefix
    fq_1 = sample_prefix + sample.libpreps[lp].seqruns[sr].fastq_files[1]   # the actual fastqs
    fq_2 = sample_prefix + sample.libpreps[lp].seqruns[sr].fastq_files[0]   # in reverse order
    return [fq_1, fq_2]

