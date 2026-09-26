#!/usr/bin/env bash
python skills/igv-validator/igv_validator.py --vcf candidates.vcf --tumor bams/T0_tumor.bam --normal bams/T0_blood.bam --variants T0_variants.tsv --reference reference/Homo_sapiens_assembly38.fasta --tumor-name T0_tumor --normal-name T0_blood --output T0
