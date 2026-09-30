#!/usr/bin/env bash
# Re-run the showcase with igv-validator (ClawBio fork, branch feat/igv-validator).
# Needs: bams_wide/ (python make_wide_slices.py), reference/Homo_sapiens_assembly38.fasta (Broad hg38),
# GENCODE v44 basic GTF, IGV desktop >= 2.16, and igv-reports (pip install igv-reports) for the interactive pages.
set -euo pipefail
V="python ${CLAWBIO:-../../ClawBio}/skills/igv-validator/igv_validator.py"
R=reference/Homo_sapiens_assembly38.fasta
G=${GENCODE:-gencode.v44.basic.annotation.gtf.gz}

# 1. one run per time point: read counts, flags and a tumor-over-blood screenshot per candidate
$V --vcf candidates.vcf --tumor bams_wide/T1_tumor.bam --normal bams_wide/T1_blood.bam --variants T1_variants.tsv \
   --reference $R --tumor-name T1_tumor --normal-name T1_blood --annotation $G --output T1
$V --vcf candidates.vcf --tumor bams_wide/T0_tumor.bam --normal bams_wide/T0_blood.bam --variants T0_variants.tsv \
   --reference $R --tumor-name T0_tumor --normal-name T0_blood --annotation $G --output T0
$V --vcf candidates.vcf --tumor bams_wide/T2_tumor.bam --normal bams_wide/T1_blood.bam --variants T2_variants.tsv \
   --reference $R --tumor-name T2_tumor --normal-name T1_blood --annotation $G --output T2   # no T2 blood

# 2. one page over all of them: the 11 candidates vs IGV, overview images and interactive views
$V --summarize . --curated-calls curated_calls.csv --overview --interactive --regions showcase_genes.bed \
   --annotation $G
