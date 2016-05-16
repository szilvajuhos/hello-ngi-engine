from ngi_pipeline.utils.classes import with_ngi_config
from ngi_pipeline.log.loggers import minimal_logger

LOG = minimal_logger(__name__)

@with_ngi_config
def update_charon_with_local_jobs_status(quiet=False, config=None, config_file_path=None):
    """Check the status of all locally-tracked jobs and update Charon accordingly.
    """
    LOG.info("Updating Charon with local job status - not really, it is only a log message")
    # add trace tracking path somehow
    return True

