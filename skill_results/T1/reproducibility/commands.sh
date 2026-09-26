#!/usr/bin/env bash
python skills/igv-validator/igv_validator.py --vcf candidates.vcf --tumor bams/T1_tumor.bam --normal bams/T1_blood.bam --variants T1_variants.tsv --reference reference/Homo_sapiens_assembly38.fasta --tumor-name T1_tumor --normal-name T1_blood --output T1
