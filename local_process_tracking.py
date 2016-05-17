from ngi_pipeline.utils.classes import with_ngi_config
from ngi_pipeline.log.loggers import minimal_logger

LOG = minimal_logger(__name__)

@with_ngi_config
def update_charon_with_local_jobs_status(quiet=False, config=None, config_file_path=None, trace=None):
    """Check the status of all locally-tracked jobs and update Charon accordingly.
    In this version we are using a trace file generated by NextFlow. As these files are generated on the sample 
    level, we have to have them in the command-line argument.
    Alternatively, we can check slurm status (see how piper does), in this sample we are parsing the
    actual state file.
    """
    # to know what are the actual arguments do something like
    # http://stackoverflow.com/questions/582056/getting-list-of-parameter-names-inside-python-function
    # args, _, _, values = inspect.getargvalues( inspect.currentframe() )
    parse_NF_trace_file(trace)
    return True

def parse_NF_trace_file(aTraceFile):
    if not aTraceFile:
        LOG.info("No trace file defined - here can go a code to track the process by slurm list and/or SQL status etc...")
    else:
        LOG.info("Processing trace file "+aTraceFile)
        # in the trace file process can be in states like COMPLETED|FAILED|ABORTED
        # also the name of the process is there like
        #task_id hash    native_id  name                status    exit    submit  duration        realtime        %cpu    rss     vmem   rchar   wchar
        #1    c8/fe9b9a  28951      mapping_bwa (1)     COMPLETED 0       2016-05-17 16:12:26.862 5.6s    2.5s    131.0%  32.1 MB 444.1 MB 5.8 MB  97 B
        #2    4b/17c1da  29171      do_variant_call (1) COMPLETED 0       2016-05-17 16:12:32.505 5.3s    5.1s    0.0%    38.4 MB 69.3 MB 272.7 KB  88.1 KB
        # we are looking at the status columns only now - if any of them is other then COMPLETED, will mark as stated ([FAILED|ABORTED] and jump out the loop)
        # 
        state = "RUNNING"
        trfh = open(aTraceFile,"r")
        # ignore the first line
        line = trfh.readline()
        for line in trfh:
            try:
                # this will fail if there is something else written as state 
                line.index("COMPLETED")
                LOG.info("Going OK so far ...")
            except ValueError:
                LOG.info("Something went amiss.")
                return "FAILED"



            


 
