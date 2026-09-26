"""Check 1: recount every SNV/indel candidate with samtools mpileup and compare to count_support.py.

samtools shares no code with our pysam counter, so agreement means the counting logic is right.
Same filters on both sides: MAPQ>=20, base quality>=20, no duplicate/secondary/supplementary/QC-fail reads.
BAQ is off (-B) and anomalous pairs are kept (-A) because count_support.py does neither.
Indels count reads with an indel of the same length starting within +-5 bp, as count_support.py does.
Run from ~/osteosarc_sv/igv:  python validation/check_samtools.py
"""
import csv
import re
import subprocess
import sys

sys.path.insert(0, ".")
SAMPLES = ["T0_tumor", "T0_blood", "T1_tumor", "T1_blood", "T2_tumor"]
src = open("count_support.py").read()
CANDS = eval(re.search(r"CANDS = (\[.*?\n\])", src, re.S).group(1))
BATCH1 = eval(re.search(r"BATCH1 = (\{.*?\})", src).group(1))

ours = {}
with open("support_counts_all.tsv") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        ours[(r["id"], r["sample"])] = r


def mpileup(bam, chrom, start, end):
    cmd = ["samtools", "mpileup", "-B", "-A", "-q", "20", "-Q", "20", "-d", "100000",
           "--ff", "UNMAP,SECONDARY,QCFAIL,DUP,SUPPLEMENTARY", "-r", f"{chrom}:{start}-{end}", bam]
    return [l.split("\t") for l in subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()]


def strip_marks(bases):
    return re.sub(r"\^.", "", bases).replace("$", "")


def snv(bam, chrom, pos, alt):
    for f in mpileup(bam, chrom, pos, pos):
        if int(f[1]) != pos:
            continue
        # drop indel sequences (+2AC / -3GTT) so only the base at this position remains
        s, i, out = strip_marks(f[4]), 0, []
        while i < len(s):
            if s[i] in "+-":
                m = re.match(r"[+-](\d+)", s[i:]); i += len(m.group(0)) + int(m.group(1)); continue
            out.append(s[i]); i += 1
        calls = [c for c in out if c != "*"]
        return len(calls), sum(c.upper() == alt for c in calls)
    return 0, 0


def indel(bam, chrom, pos, ref, alt):
    size = len(alt) - len(ref)
    sign, n = ("-" if size < 0 else "+"), abs(size)
    depth, hits = 0, 0
    for f in mpileup(bam, chrom, pos - 5, pos + 5):
        p = int(f[1])
        s = strip_marks(f[4])
        if p == pos:  # depth = reads with a base (or deletion) at this position
            i, depth = 0, 0
            while i < len(s):
                if s[i] in "+-":
                    m = re.match(r"[+-](\d+)", s[i:]); i += len(m.group(0)) + int(m.group(1)); continue
                depth += 1; i += 1
        hits += len(re.findall(rf"\{sign}{n}(?![0-9])", s))
    return depth, hits


rows, bad = [], 0
for sample in SAMPLES:
    for cid, gene, chrom, pos, ref, alt in CANDS:
        bam = f"bams/{sample}.batch{1 if cid in BATCH1 else 2}.bam"
        d, a = snv(bam, chrom, pos, alt) if len(ref) == len(alt) == 1 else indel(bam, chrom, pos, ref, alt)
        o = ours[(cid, sample)]
        od, oa = int(o["depth"]), int(o["alt_reads"])
        same_alt = a == oa
        bad += not same_alt
        rows.append([cid, gene, sample, oa, a, od, d, "yes" if same_alt else "NO"])

w = csv.writer(open("validation/check_samtools.tsv", "w"), delimiter="\t")
w.writerow(["id", "gene", "sample", "alt_ours", "alt_samtools", "depth_ours", "depth_samtools", "alt_match"])
w.writerows(rows)
print(f"{len(rows) - bad}/{len(rows)} alt-read counts match samtools exactly")
for r in rows:
    if r[-1] == "NO" or abs(r[5] - r[6]) > max(2, 0.05 * r[5]):
        print("  differs:", *r)
