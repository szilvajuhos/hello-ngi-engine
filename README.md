Hello GA Engine
---------------

This is a minimal NGI pipeline engine in NextFlow to provide a skeleton for a
larger engine. Prerequisites:

- nextflow installed: see http://www.nextflow.io/index.html#GetStarted 
- ngi\_pipeline installed (piper is not required for this engine. See
  installation steps below)
- access to charon-dev
- sample sheet and flowcell prepared

#### Installing NextFlow:

Generally it is something like described on the NextFlow web page above.  The
only thing to consider is that put nextflow to a place where it is in your path
so the pipeline can be launched.

#### Installing NGI pipeline:

You will need conda, for its quick installation see
http://conda.pydata.org/docs/install/quick.html . After that go with the
installation as:

    git clone git@github.com:NationalGenomicsInfrastructure/ngi_pipeline.git
    conda create -n NGI pip sqlalchemy 
    source activate NGI
    python setup.py develop

After going through all these steps, copy the "test\_ngi\_config.yaml" with a
new name (will be my\_setup.yaml in this sample), and edit it. There are
compulsory entries to be set, i.e.  the mail address should be your own
address, and the directories have to be set correctly. Make sure you are not
overwriting production data.

    Once ready, define your NGI_CONFIG variable (preferably in your shell
    profile, i.e. .bashrc):

    export NGI_CONFIG=/path/to/my/ngi_pipeline/my\_setup.py

#### Access to charon-dev:

You have to ask the charon admin to provide a CHARON\_API\_TOKEN for you. As
charon-dev is replicated weekly from the production charon, make sure you have
the account and token present in the production version of charon, or you have
to generate a new token after replication again. Once the token is ready, set
the environment variables in your .bashrc or shell profile like:

    export CHARON_API_TOKEN= YOUR_TOKEN
    export CHARON_BASE_URL=http://charon.scilifelab.se/

#### Sample sheet and flowcell prepared:

There is a script generating a flowcell structure in
scripts/NGI\_pipeline\_test.py. Using this you have to define a pair of FASTQs,
and it is building all the directory structure and stuff mimicking the
demultiplexed directory structure of NGI production. Its usage:

    python NGI_pipeline_test.py create  --project-name J.Doe_16_01 --symlinks --FC 1 --fastq1 test_S001_L001_R1_001.fastq.gz --fastq2 test_S001_L001_R2_001.fastq.gz

If you are not satisfied with a test project for some reason, delete it using
its ID (not by its name):

    python NGI_pipeline_test.py delete --project-id P836

To make sure the file format is in line with the usual Illumina format, we are
expecting read file format being something like
{}\_S{}\_L00{}\_R1\_001.fastq.gz . The working mode of NGI pipeline that it
picking up files from the pre-prepared flowcell. After demultiplexing we want
to have different folders for each project and subfolders for each sample.
Organizing the flowcell happens by the parse\_flowcell() function in
ngi\_pipeline/conductor/flowcell.py that is expecting a directory name. 

After generating the flowcell from the test fake data we are getting a
directory that can be organized. Note, the *a2014205* directory is there
because ngi\_pipeline expects this directory name to be somewhere in the
flowcell path. I do not know the rationale behind this right now.

    szilva@galatea ~/dev/hello-ga-engine/a2014205/data $ python ~/dev/ngi_pipeline/scripts/NGI_pipeline_test.py create  --project-name S.Juhos_16_02 --symlinks --FC 1 --fastq1 test_S001_L001_R1_001.fastq.gz --fastq2 test_S001_L001_R2_001.fastq.gz
    producing FC: 677817_ST-E00205_2645_BZAIURALXX
    updaiting charon-dev
    now run the following:
    PATH_TO_NGI=<path/to>/ngi_pipeline>
    PATH_TO_FC=/home/szilva/dev/hello-ga-engine/a2014205/data
    PATH_TO_DATA=<path/to/data>
    python $PATH_TO_NGI/scripts/ngi_pipeline_start.py organize flowcell $PATH_TO_FC/677817_ST-E00205_2645_BZAIURALXX
    python $PATH_TO_NGI/scripts/ngi_pipeline_start.py analyze $PATH_TO_DATA/DATA/P421
    szilva@galatea ~/dev/hello-ga-engine/a2014205/data $ ls -l
    total 4976
    drwxrwxr-x 3 szilva szilva    4096 apr 18 09:27 677817_ST-E00205_2645_BZAIURALXX
    -rw-rw-r-- 1 szilva szilva 2527596 mar 16 18:32 test_S001_L001_R1_001.fastq.gz
    -rw-rw-r-- 1 szilva szilva 2558400 mar 16 18:32 test_S001_L001_R2_001.fastq.gz

#### Things to consider before implementing a new engine:

The SampleSheet.csv is not used, it is only a placeholder though its existence
is checked and an exception/exit is generated if missing. The organizing
function is using the project folder structure made by demultiplexer. In
general this "organize" step could be left out but right now there is little
trust from the users to procees without this. 

The parse\_flowcell() function is only generating a directory data object, and
its return values is used by setup\_analysis\_directory\_structure() that is
calling charon to check registered samples. One point of the organizing step is
that after demultiplexing we have a Project -> Sample -> FASTQ file structure
and we want to have a Project -> Sample -> Libprep -> Run -> FASTQ hierarchy
instead - this is done with softlinks in the ARCHIVE directory (INCOMING an
irma). To find out the libprep/run relationship we have to go to charon. The
SampleSheet.csv in practice contains this information (Uppsala pipeline lives
without charon), but for Stockholm at the beginning charon is updated from LIMS
with this information.  When sequencing ends, TACA starts demultiplexing, and
moves data to nestor. When file transfer is ready, and data is on nestor, the
organize/analyze step should start automatically but now it is done manually. 

After launching the analysis, charon is called again to decide what pipeline to
use (see the get\_engine\_bp() function in
ngi\_pipeline/conductor/launchers.py). Right now we mostly use
*whole\_genome\_reseq* that is using piper as a workflow engine.  In the config
yaml file you can define these values in theory in the analysis:workflows
entries, so their role is not really clear for me.

As the engines are independent of the pipeline framework, the only thing that
is started by ngi\_pipeline is the analyse() function in your engine module.
This of course have to be written in python, and these functions have to be
implemented in there (see the launch\_analysis() function in
ngi\_pipeline/conductor/launchers.py) :

 * analyse()
 * local\_process\_tracking.update\_charon\_with\_local\_jobs\_status()

The latter process in needed to keep track the status of the processing
workflow. It is generally stored in a local SQL database since the connection
to charon is unstable. Synchronization between charon and this local sqlite3
table happens in this function. 

Additional quirk is that the pipeline starts launcing the QC step first *by
default* . To avoid this it is adviced to add the no\_qc command line parameter
(see also the launch\_analysis() part before).

Generally it is the conductor class that decides when to run what (just like in
an orchestra) and we are pulling the best practice method from charon. To
change the best practice part, use the code (using your project ID):

    from ngi_pipeline.database.classes import CharonSession, CharonError
    cs = CharonSession()
    cs.project_update("P876",best_practice_analysis="hello_engine")


organizing is via softlinks to the ARCHIVE (INCOMING on irma)

 * in the config file have a test entry in the analysis section
 * ngi\_pipeline/engines/test module that contains analyzis() and the update part
 * an entry in charon in sync with the engine name that is in the config
 * have a look at whole\_genome\_reseq in conductor.launchers.launch\_analysis.()

Now if we want to have test engine, its config in the NGI\_CONFIG yaml file
should be like:

    analysis:
        workflows:
            best_practice_analysis:
                whole_genome_reseq:
                    analysis_engine: ngi_pipeline.engines.piper_ngi
                qc:
                    analysis_engine: ngi_pipeline.engines.qc_ngi
                hello_engine:
                    analysis_engine: ngi_pipeline.engines.hello-ngi-engine

Now, after setting up the fake flowcell and organizing it, you can run something like:

    (NGI)szilva@galatea /szilvaproj/a2014205/nobackup/NGI/analysis_ready $ python ~/dev/ngi_pipeline/scripts/ngi_pipeline_start.py analyze project /szilvaproj/a2014205/nobackup/NGI/analysis_ready/DATA/P697 --no-qc
    2016-05-02 16:00:47,644 - ngi_pipeline.utils.filesystem - INFO - Setting up project "P697"
    2016-05-02 16:00:47,644 - ngi_pipeline.utils.filesystem - INFO - Setting up sample "P697_004"
    2016-05-02 16:00:47,644 - ngi_pipeline.utils.filesystem - INFO - Setting up libprep "A"
    2016-05-02 16:00:47,645 - ngi_pipeline.utils.filesystem - INFO - Setting up seqrun "908254_ST-E00205_2662_BBZZHATCXX"
    2016-05-02 16:00:47,645 - ngi_pipeline.utils.filesystem - INFO - Adding fastq file "P697_004_S4_L004_R1_001.fastq.gz" to seqrun "908254_ST-E00205_2662_BBZZHATCXX"
    2016-05-02 16:00:47,645 - ngi_pipeline.utils.filesystem - INFO - Adding fastq file "P697_004_S4_L004_R2_001.fastq.gz" to seqrun "908254_ST-E00205_2662_BBZZHATCXX"
    2016-05-02 16:00:47,645 - ngi_pipeline.utils.filesystem - INFO - Setting up sample "P697_008"
    [...]
    2016-05-02 16:00:47,749 - ngi_pipeline.engines.hello-ngi-engine.local_process_tracking - INFO - Updating Charon with local job status - not really, it is only a log message
    2016-05-02 16:00:47,824 - ngi_pipeline.conductor.launchers - INFO - Attempting to launch sample analysis for project "S.Juhos_16_01" / sample "P697_007" / engine"ngi_pipeline.engines.hello-ngi-engine"
    
