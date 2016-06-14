Hello GA Engine
---------------

This is a minimal NGI pipeline engine in NextFlow to provide a skeleton for a
larger engine. Prerequisites:

- work either on your laptop, or on milou-b - the latter is the only UPPMAX
  node that can connect to charon-dev
- nextflow installed: see http://www.nextflow.io/index.html#GetStarted
  (installed as module on milou-b)
- ngi\_pipeline installed (piper is not required for this engine. See
  installation steps below)
- access to charon-dev (get an API token)
- sample sheet and flowcell prepared

#### __Installing NextFlow:__

Generally it is something like described on the NextFlow web page above.  The
only thing to consider is that put nextflow to a place where it is in your path
so the pipeline can be launched. 
On UPPMAX machines there should be a Nextflow module already, so get it by simply

    $ module load Nextflow

#### __Installing NGI pipeline:__

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
address, and the directories have to be set correctly. Do not overwrite
production data. Also see later some entries in hello\_engine.yaml you have to
add to your yaml file.

Once ready, define your NGI\_CONFIG variable (preferably in your shell
profile, i.e. .bashrc):

    export NGI_CONFIG=/path/to/my/ngi_pipeline/my_setup.yaml

#### __Access to charon-dev:__

You have to ask the charon admin to provide a CHARON\_API\_TOKEN for you. As
charon-dev is replicated weekly from the production charon, make sure you have
the account and token present in the production version of charon, or you have
to generate a new token after replication again. Once the token is ready, set
the environment variables in your .bashrc or shell profile like:

    export CHARON_API_TOKEN=YOUR_TOKEN
    export CHARON_BASE_URL=http://charon.scilifelab.se/

#### __Clone hello-ngi-engine__

From Github get a clone:

    git clone git@github.com:szilvajuhos/hello-ngi-engine.git
    cd hello-ngi-engine/a2014205/

The directory name a2014205 is needed for some reason to be in the path, so we
are doing data emulation there. There is a small set of reads in its data
subdirectory and a corresponding dummy reference.

#### __Sample sheet and flowcell prepared:__

There is a script generating a flowcell structure in
scripts/NGI\_pipeline\_test.py. Using this you have to define a pair of FASTQs,
and it is building all the directory structure and stuff mimicking the
demultiplexed directory structure of NGI production. Before starting, source the
NGI conda environment. Its usage:

    (NGI)$ python /path/to/NGI_pipeline_test.py create  --project-name J.Doe_16_01 --symlinks --FC 1 --fastq1 /full/path/to/hello-ngi-engine/a2014205/data/test_S001_L001_R1_001.fastq.gz --fastq2 /full/path/to/hello-ngi-engine/a2014205/data/test_S001_L001_R2_001.fastq.gz

If you are not satisfied with a test project for some reason, delete it using
its ID (not by its name):

    (NGI)$ python /path/to/NGI_pipeline_test.py delete --project-id P836

Formatting is important! Make sure you are naming your project as J.Doe\_16\_01
(and not J.Doe\_2\_3 or J.Doe\12.3 etc). Furthermore, the file format is in line
with the usual Illumina format, we are expecting the read file being
something like {sample}\_S{index}\_L00{lane}\_R[12]\_001.fastq.gz . The working
mode of NGI pipeline is that it is picking up files from the pre-prepared flowcell.
After demultiplexing we want to have different folders for each project and
subfolders for each sample.  Organizing the flowcell happens by the
parse\_flowcell() function in ngi\_pipeline/conductor/flowcell.py that is
expecting a directory name. 

After generating the flowcell from the test fake data we are getting a
directory that can be organized. Note, the *a2014205* directory is there
because ngi\_pipeline expects this directory name to be somewhere in the
flowcell path. I do not know the rationale behind this right now.

    (NGI)szilva@milou-b ~/dev/hello-ga-engine/a2014205/data $ python ~/dev/ngi_pipeline/scripts/NGI_pipeline_test.py create  --project-name S.Juhos_16_02 --symlinks --FC 1 --fastq1 /full/path/to/test_S001_L001_R1_001.fastq.gz --fastq2 /full/path/to/test_S001_L001_R2_001.fastq.gz
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

You have to use full path, as the script is expecting in this form.

#### __Editing Charon-dev to pick up the hello engine__

Go to the http://charon-dev.scilifelab.se URL, and edit the entry referring to your project. 
 * click on the project ID (it is P421 in this example above)
 * click on Edit on the right side
 * edit the Best-practice analysis part from "whole\_genome\_reseq" to "hello\_engine"
 * click Save

*Alternative method to change best practice analysis:*

Generally it is the conductor class that decides when to run what (just like in
an orchestra) and we are pulling the best practice method from charon. To
change the best practice part, use the code (using your project ID):

    from ngi_pipeline.database.classes import CharonSession, CharonError
    cs = CharonSession()
    cs.project_update("P876",best_practice_analysis="hello_engine")



#### __Running NGI pipeline__

Engines used by NGI pipeline are usually residing in the
ngi\_pipeline/ngi\_pipeline/engines directory. In the yaml config file we are
referring to them in the "analysis" session, so if we have:

    hello_engine:
        analysis_engine: ngi_pipeline.engines.hello-ngi-engine

It is expected that the hello engine files are in
ngi\_pipeline/ngi\_pipeline/engines/hello-ngi-engine . Make a symlink (or copy
the files there):

    ln -s /path/to/hello-ngi-engine /path/to/ngi_pipeline/ngi_pipeline/engines/hello-ngi-engine

We have to provide a path to the reference and other environment variables (see
code in launchers\.py and the analyze() function when calling the nextflow
subprocess). It can be done by any YAML directive, we are doing it by adding:

    hello_engine:
        load_modules:
            - bioinfo-tools
            - Nextflow
        workflow: /path/to/your/hello-ngi-engine/hello-ga.nf
        refbase: /path/to/your/hello-ngi-engine/a2014205/reference/        
        trace_tracking_prefix: /home/szilva/sr/a2014205/trace_tracking_

To the NGI\_CONFIG file. The refbase contains a simple fake BWA index and reference for testing.

Now we are at the stage when we can run the pipeline. First we have to organize
(there will be a new random flowcell ID generated, do not use this):

    python $PATH_TO_NGI/scripts/ngi_pipeline_start.py organize flowcell $PATH_TO_FLOWCELL/224721_ST-E00202_8606_ARENQBHBXX

If you get a healthy "Done with organization" message, you have files and
symlinks in your \$top\_dir directory. Also the log file defined in the
"logging:" section of the setup yaml file contains entries referring to the
successful organization. Next step is to run the process without the QC step
(it is something we have to later refactor in NGI pipeline):

    python ${PATH_TO_NGI}/scripts/ngi_pipeline_start.py analyze flowcell ${PATH_TO_FLOWCELL}/224721_ST-E00202_8606_ARENQBHBXX --no-qc

or 

    python ${PATH_TO_NGI}/scripts/ngi_pipeline_start.py analyze project ${topdir}/DATA/P421/ --no-qc

The pipeline starts launcing the QC step first *by default* . To avoid this it
is adviced to add the --no-qc command line parameter (see also the
launch\_analysis() part before).

#### __Things to consider before implementing a new engine:__

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
moves data to nestor (TODO well, no, have to ask Isak/Francesco/Per what is the
case now). When file transfer is ready, and data is on
(includecorrectplacehere), the organize/analyze step should start automatically
but now it is done manually (dunno whether it is the case still). 

After launching the analysis, charon is called again to decide what pipeline to
use (see the get\_engine\_bp() function in
ngi\_pipeline/conductor/launchers.py). Right now we mostly use
*whole\_genome\_reseq* that is using piper as a workflow engine.  In the config
yaml file you can define these values in theory in the analysis:workflows
entries, so their role is not really clear for me. 

As for the hello engine we are using "hello\_engine" instead of the whole
genome reseq part. Now it have to be edited manually, go to your project on
charon-dev, and edit manualy the "Best-practice analysis" item to
"hello\_engine". Also, see the changes you have to give to your yaml config in
hello\_engine.yaml (see an example below) .
As the engines are independent of the pipeline framework, the only thing that
is started by ngi\_pipeline is the analyse() function in your engine module.
This of course have to be written in python, and these functions have to be
implemented in there (see the launch\_analysis() function in
ngi\_pipeline/conductor/launchers.py) :

 * analyse()
 * local\_process\_tracking.update\_charon\_with\_local\_jobs\_status()

The latter process in needed to keep track the status of the processing
workflow. Using piper it is stored in a local SQL database since the connection
to charon is unstable. Synchronization between charon and this local sqlite3
table happens in this function. Do not be fooled: the implementation of piper
allows only checking for launch and finish, nothing is known about the ongoing
status. Nextflow can have a trace file, with actual running statuses about
processes. It is what is stored in the database:trace\_tracking\_prefix, and you
have to parametrize nextflow as 

    nextflow run myscript.nf --sample this_and_that -with-trace /there/it/goes/tracefile.txt

As we have different flows for each sample, the prefix of this tracefile is
defined in the yaml file, and you will get trace file to process as
trace\_tracking\_J.Doe\_16\_06\_P123\_001

### __Random unorganized notes__

The SampleSheet.csv is not used, it is only a placeholder though its existence
is checked and an exception/exit is generated if missing. The organizing
function is using the project folder structure made by demultiplexer. In
general this "organize" step could be left out but right now there is little
trust from the users to procees without this. 

organizing is via softlinks to the ARCHIVE (INCOMING on irma)

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

