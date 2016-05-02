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
    return 0


