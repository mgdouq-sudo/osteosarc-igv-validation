#!/usr/bin/env bash
python skills/igv-validator/igv_validator.py --vcf candidates.vcf --tumor bams_wide/T2_tumor.bam --normal bams_wide/T1_blood.bam --variants T2_variants.tsv --reference reference/Homo_sapiens_assembly38.fasta --tumor-name T2_tumor --normal-name T1_blood --annotation reference/gencode.v44.basic.annotation.gtf.gz --output T2
