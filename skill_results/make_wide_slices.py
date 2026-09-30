"""Download ±5 kb BAM slices around each candidate from the public osteosarc.com BAMs.

Needs the BAM indexes (.bai) in ../bams/ (download them once from the same S3 paths + ".bai"),
and writes bams_wide/<sample>.bam (+ .bai), about 5-15 MB each. Usage: python make_wide_slices.py
"""
import os

import pysam

BASE = "https://sid-sijbrandij-osteosarc-dataset.s3.us-west-2.amazonaws.com/"
PAD = 5000
INDEX = {"T0_tumor": "NP_WGS_Tumor_DNA.recal.bam.bai", "T0_blood": "NP_WGS_Normal_DNA.recal.bam.bai",
         "T1_tumor": "tumor24.recal.bam.bai", "T1_blood": "blood.recal.bam.bai",
         "T2_tumor": "SG.WGS.UCLA.2025.01.tumor.recal.bam.bai"}

paths = dict(line.rstrip("\n").split("\t") for line in open("../samples.tsv"))
windows = []
for line in open("candidates.vcf"):
    if not line.startswith("#"):
        chrom, pos = line.split("\t")[:2]
        windows.append((chrom, max(0, int(pos) - PAD), int(pos) + PAD))

os.makedirs("bams_wide", exist_ok=True)
for name, bai in INDEX.items():
    src = pysam.AlignmentFile(BASE + paths[name], index_filename="../bams/" + bai)
    tmp, seen = f"bams_wide/{name}.unsorted.bam", set()
    with pysam.AlignmentFile(tmp, "wb", header=src.header) as out:
        for chrom, a, b in windows:
            for read in src.fetch(chrom, a, b):
                key = (read.query_name, read.flag, read.reference_id, read.reference_start)
                if key not in seen:          # windows can overlap: write each read once
                    seen.add(key)
                    out.write(read)
    pysam.sort("-o", f"bams_wide/{name}.bam", tmp)
    os.remove(tmp)
    pysam.index(f"bams_wide/{name}.bam")
    print(name, len(seen), "reads")
