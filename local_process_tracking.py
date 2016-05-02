import collections
import glob
import inspect
import os
import psutil
import re
import time

from ngi_pipeline.database.classes import CharonSession, CharonError
from ngi_pipeline.log.loggers import minimal_logger
from ngi_pipeline.utils.communication import mail_analysis
from ngi_pipeline.engines.piper_ngi.database import SampleAnalysis, get_db_session
from ngi_pipeline.engines.piper_ngi.utils import create_exit_code_file_path, \
                                                 create_project_obj_from_analysis_log, \
                                                 get_finished_seqruns_for_sample
from ngi_pipeline.engines.piper_ngi.parsers import parse_genotype_concordance, \
                                                   parse_mean_coverage_from_qualimap, \
                                                   parse_deduplication_percentage
from ngi_pipeline.utils.slurm import get_slurm_job_status, \
                                     kill_slurm_job_by_id
from ngi_pipeline.utils.parsers import STHLM_UUSNP_SEQRUN_RE, \
                                       STHLM_UUSNP_SAMPLE_RE
from sqlalchemy.exc import IntegrityError, OperationalError
from ngi_pipeline.utils.charon import recurse_status_for_sample
from ngi_pipeline.utils.classes import with_ngi_config


LOG = minimal_logger(__name__)

@with_ngi_config
def update_charon_with_local_jobs_status(quiet=False, config=None, config_file_path=None):
    """Check the status of all locally-tracked jobs.
    Generally we arre considering our engines independent of the NGI pipeline.
    Nevertheless, the intention of this module is to save the status of the
    actual engine in charon, and/or in a local SQLite3 table. Your actual
    implementation can differ from this just like here: for the sake of
    simplicity we are NOT logging things in charon/sqlite3/whatever, only in
    the log file.  
    For an implementation of charon/sqlite3 interaction see the piper engine.
    """
    LOG.info("Updating local status.")

@with_ngi_config
def XXXupdate_charon_with_local_jobs_status(quiet=False, config=None, config_file_path=None):
    """Check the status of all locally-tracked jobs and update Charon accordingly.
    """
    if quiet and not config.get("quiet"):
        config['quiet'] = True
    LOG.info("Updating Charon with the status of all locally-tracked jobs...")
    with get_db_session() as session:
        charon_session = CharonSession()
        for sample_entry in session.query(SampleAnalysis).all():
            # Local names
            workflow = sample_entry.workflow
            project_name = sample_entry.project_name
            project_id = sample_entry.project_id
            project_base_path = sample_entry.project_base_path
            sample_id = sample_entry.sample_id
            engine = sample_entry.engine
            # Only one of these id fields (slurm, pid) will have a value
            slurm_job_id = sample_entry.slurm_job_id
            process_id = sample_entry.process_id
            piper_exit_code = get_exit_code(workflow_name=workflow,
                                            project_base_path=project_base_path,
                                            project_name=project_name,
                                            project_id=project_id,
                                            sample_id=sample_id)
            label = "project/sample {}/{}".format(project_name, sample_id)

            if workflow not in ("merge_process_variantcall", "genotype_concordance",):
                LOG.error('Unknown workflow "{}" for {}; cannot update '
                          'Charon. Skipping sample.'.format(workflow, label))
                continue

            try:
                project_obj = create_project_obj_from_analysis_log(project_name,
                                                                   project_id,
                                                                   project_base_path,
                                                                   sample_id,
                                                                   workflow)
            except IOError as e: # analysis log file is missing!
                error_text = ('Could not find analysis log file! Cannot update '
                              'Charon for {} run {}/{}: {}'.format(workflow,
                                                                   project_id,
                                                                   sample_id,
                                                                   e))
                LOG.error(error_text)
                if not config.get('quiet'):
                    mail_analysis(project_name=project_name,
                                  sample_name=sample_id,
                                  engine_name=engine,
                                  level="ERROR",
                                  info_text=error_text,
                                  workflow=workflow)
                continue
            try:
                if piper_exit_code == 0:
                    # 0 -> Job finished successfully
                    if workflow == "merge_process_variantcall":
                        sample_status_field = "analysis_status"
                        seqrun_status_field = "alignment_status"
                        set_status = "ANALYZED" # sample level
                    elif workflow == "genotype_concordance":
                        sample_status_field = seqrun_status_field = "genotype_status"
                        set_status = "DONE" # sample level
                    recurse_status = "DONE" # For the seqrun level
                    info_text = ('Workflow "{}" for {} finished succesfully. '
                                 'Recording status {} in Charon'.format(workflow,
                                                                        label,
                                                                        set_status))
                    LOG.info(info_text)
                    if not config.get('quiet'):
                        mail_analysis(project_name=project_name,
                                      sample_name=sample_id,
                                      engine_name=engine,
                                      level="INFO",
                                      info_text=info_text,
                                      workflow=workflow)
                    charon_session.sample_update(projectid=project_id,
                                                 sampleid=sample_id,
                                                 **{sample_status_field: set_status})
                    recurse_status_for_sample(project_obj,
                                              status_field=seqrun_status_field,
                                              status_value=recurse_status,
                                              config=config)
                    # Job is only deleted if the Charon status update succeeds
                    session.delete(sample_entry)
                    if workflow == "merge_process_variantcall":
                        # Parse seqrun output results / update Charon
                        # This is a semi-optional step -- failure here will send an
                        # email but not more than once. The record is still removed
                        # from the local jobs database, so this will have to be done
                        # manually if you want it done at all.
                        piper_qc_dir = os.path.join(project_base_path, "ANALYSIS",
                                                    project_id, "piper_ngi",
                                                    "02_preliminary_alignment_qc")
                        update_coverage_for_sample_seqruns(project_id, sample_id,
                                                           piper_qc_dir)
                        update_duplication_rates_for_sample(project_id, sample_id,
                                                           project_base_path)
                    elif workflow == "genotype_concordance":
                        piper_gt_dir = os.path.join(project_base_path, "ANALYSIS",
                                                    project_id, "piper_ngi",
                                                    "03_genotype_concordance")
                        try:
                            update_gtc_for_sample(project_id, sample_id, piper_gt_dir)
                        except (CharonError, IOError, ValueError) as e:
                            LOG.error(e)
                elif type(piper_exit_code) is int and piper_exit_code > 0:
                    # 1 -> Job failed
                    set_status = "FAILED"
                    error_text = ('Workflow "{}" for {} failed. Recording status '
                                  '{} in Charon.'.format(workflow, label, set_status))
                    LOG.error(error_text)
                    if not config.get('quiet'):
                        mail_analysis(project_name=project_name,
                                      sample_name=sample_id,
                                      engine_name=engine,
                                      level="ERROR",
                                      info_text=error_text,
                                      workflow=workflow)
                    if workflow == "merge_process_variantcall":
                        sample_status_field = "analysis_status"
                        seqrun_status_field = "alignment_status"
                    elif workflow == "genotype_concordance":
                        sample_status_field = seqrun_status_field = "genotype_status"
                    charon_session.sample_update(projectid=project_id,
                                                 sampleid=sample_id,
                                                 **{sample_status_field: set_status})
                    recurse_status_for_sample(project_obj, status_field=seqrun_status_field,
                                              status_value=set_status, config=config)
                    # Job is only deleted if the Charon update succeeds
                    session.delete(sample_entry)
                else:
                    # None -> Job still running OR exit code was never written (failure)
                    JOB_FAILED = None
                    if slurm_job_id:
                        try:
                            slurm_exit_code = get_slurm_job_status(slurm_job_id)
                        except ValueError as e:
                            slurm_exit_code = 1
                        if slurm_exit_code is not None: # "None" indicates job is still running
                            JOB_FAILED = True
                    else:
                        if not psutil.pid_exists(process_id):
                            # Job did not write an exit code and is also not running
                            JOB_FAILED = True
                    if JOB_FAILED:
                        set_status = "FAILED"
                        error_text = ('No exit code found but job not running '
                                      'for {} / {}: setting status to {} in '
                                      'Charon'.format(label, workflow, set_status))
                        if slurm_job_id:
                            exit_code_file_path = \
                                create_exit_code_file_path(workflow_subtask=workflow,
                                                           project_base_path=project_base_path,
                                                           project_name=project_name,
                                                           project_id=project_id,
                                                           sample_id=sample_id)
                            error_text += (' (slurm job id "{}", exit code file path '
                                           '"{}")'.format(slurm_job_id, exit_code_file_path))
                        LOG.error(error_text)
                        if not config.get('quiet'):
                            mail_analysis(project_name=project_name,
                                          sample_name=sample_id,
                                          engine_name=engine, level="ERROR",
                                          info_text=error_text,
                                          workflow=workflow)
                        if workflow == "merge_process_variantcall":
                            sample_status_field = "analysis_status"
                            seqrun_status_field = "alignment_status"
                        elif workflow == "genotype_concordance":
                            sample_status_field = seqrun_status_field = "genotype_status"
                        charon_session.sample_update(projectid=project_id,
                                                     sampleid=sample_id,
                                                     **{sample_status_field: set_status})
                        recurse_status_for_sample(project_obj,
                                                  status_field=seqrun_status_field,
                                                  status_value=set_status,
                                                  config=config)
                        # Job is only deleted if the Charon update succeeds
                        LOG.debug("Deleting local entry {}".format(sample_entry))
                        session.delete(sample_entry)
                    else: # Job still running
                        set_status = "UNDER_ANALYSIS"
                        if workflow == "merge_process_variantcall":
                            sample_status_field = "analysis_status"
                            seqrun_status_field = "alignment_status"
                            recurse_status = "RUNNING"
                        elif workflow == "genotype_concordance":
                            sample_status_field = seqrun_status_field = "genotype_status"
                            recurse_status = "UNDER_ANALYSIS"
                        try:
                            charon_status = \
                                    charon_session.sample_get(projectid=project_id,
                                                              sampleid=sample_id).get(sample_status_field)
                            if charon_status and not charon_status == set_status:
                                LOG.warn('Tracking inconsistency for {}: Charon status '
                                         'for field "{}" is "{}" but local process tracking '
                                         'database indicates it is running. Setting value '
                                         'in Charon to {}.'.format(label, sample_status_field,
                                                                   charon_status, set_status))
                                charon_session.sample_update(projectid=project_id,
                                                             sampleid=sample_id,
                                                             **{sample_status_field: set_status})
                                recurse_status_for_sample(project_obj,
                                                          status_field=seqrun_status_field,
                                                          status_value=recurse_status,
                                                          config=config)
                        except CharonError as e:
                            error_text = ('Unable to update/verify Charon '
                                          'for {}: {}'.format(label, e))
                            LOG.error(error_text)
                            if not config.get('quiet'):
                                mail_analysis(project_name=project_name, sample_name=sample_id,
                                              engine_name=engine, level="ERROR",
                                              workflow=workflow, info_text=error_text)
            except CharonError as e:
                error_text = ('Unable to update Charon for {}: '
                              '{}'.format(label, e))
                LOG.error(error_text)
                if not config.get('quiet'):
                    mail_analysis(project_name=project_name, sample_name=sample_id,
                                  engine_name=engine, level="ERROR",
                                  workflow=workflow, info_text=error_text)
            except OSError as e:
                error_text = ('Permissions error when trying to update Charon '
                              '"{}" status for "{}": {}'.format(workflow, label, e))
                LOG.error(error_text)
                if not config.get('quiet'):
                    mail_analysis(project_name=project_name, sample_name=sample_id,
                                  engine_name=engine, level="ERROR",
                                  workflow=workflow, info_text=error_text)
        session.commit()
