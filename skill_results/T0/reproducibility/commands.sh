#!/usr/bin/env bash
python skills/igv-validator/igv_validator.py --vcf candidates.vcf --tumor bams_wide/T0_tumor.bam --normal bams_wide/T0_blood.bam --variants T0_variants.tsv --reference reference/Homo_sapiens_assembly38.fasta --tumor-name T0_tumor --normal-name T0_blood --annotation reference/gencode.v44.basic.annotation.gtf.gz --output T0
