#!/usr/bin/env nextflow
 
/*
 * Defines pipeline parameters in order to specify the refence genomes
 * and read pairs by using the command line options
 * TODO: clean up so any sort of directory can be added as a source for input data
 */

params.sample = "test" // override with --sample <SAMPLE>
params.reads1 = "${PWD}/a2014205/data/${params.sample}_S001_L001_R1_001.fastq.gz"
params.reads2 = "${PWD}/a2014205/data/${params.sample}_S001_L001_R2_001.fastq.gz"

// the default output directory: as before you can change by --out /my/target/dir 
params.out = "$PWD"

/*
 * references/indexes used 
 * By default we are using directory structure present on milou. 
 * If your references, indexes resides at a different location, change it as 
 * --refbase /my/directory/with/references
 */

params.refbase = "${PWD}/a2014205/reference"

// the reference genome
params.genome = "${params.refbase}/fakeRef.fasta"
params.genomeidx = "${params.genome}.fai"

/*
 * validate input
 */
genome_file = file(params.genome)
// the index file is not in there in the flow explicitly as an input file, 
// but the pileup part is expecting it to be next to the reference fasta
genome_index = file(params.genomeidx)

reads1 = file(params.reads1)
reads2 = file(params.reads2)

if( !genome_file.exists() ) exit 1, "Missing reference: ${genome_file}"
if( !genome_index.exists() ) exit 1, "Missing index: ${genome_index}"
if( !reads1.exists() ) exit 2, "Missing read ${params.reads1}"
if( !reads2.exists() ) exit 2, "Missing read ${params.reads2}"

// the mapping part; it is a pipeline itself, but this flow is explicit enough not to make it into 
// different compartments
process mapping_bwa {

	module 'bwa'
	module 'samtools'

	cpus 4

	input:
	file genome_file
	file reads1
	file reads2

	output:
	file '*.bam' into mapped_bam 

	"""
	bwa mem -t ${task.cpus} -R "@RG\\tID:${params.sample}\\tSM:${params.sample}\\tLB:${params.sample}\\tPL:illumina" \
	-B 3 -t ${task.cpus} \
	-M ${params.genome} ${reads1} ${reads2} \
	| samtools view -bS -t ${genome_index} - \
	| samtools sort - > ${params.sample}.bam
	"""	

}

process do_variant_call {

	cpus 1
	
	input:
	file mapped_bam

	output:
	file "${params.sample}.vcf" into mpileup_vcf

	"""
    samtools mpileup -f ${params.genome} -vu ${params.sample}.bam  2> ${params.sample}.vc.log 1> ${params.sample}.vcf 
	"""
}


