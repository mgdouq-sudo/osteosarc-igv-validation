"""Checks 3-4: positive and negative controls, using count_support.py's own SNV counter.

Positive: inherited heterozygous SNPs (about half the reads in blood) must read about half in the tumor too.
Negative: every other position in the slices should show (almost) no alt reads.
Run from ~/osteosarc_sv/igv:  python validation/check_controls.py
"""
import collections
import csv

import pysam

src = open("count_support.py").read()
exec(src[: src.index("out = csv.writer")])  # load ok()/snv() without running the count

BLOOD, TUMOR = "T1_blood", "T1_tumor"
regions = [l.split()[:3] for l in open("regions_batch2.bed")] + [l.split()[:3] for l in open("regions_batch1.bed")]
cand_pos = {(c[2], c[3]) for c in CANDS} | {(SV[2], SV[3]), (SV[4], SV[5])}


def base_counts(bam, chrom, pos):
    c = collections.Counter()
    for col in bam.pileup(chrom, pos - 1, pos, truncate=True, min_base_quality=20, stepper="nofilter", ignore_orphans=False):
        for pr in col.pileups:
            r = pr.alignment
            if ok(r) and not pr.is_del and not pr.is_refskip and pr.query_position is not None:
                c[r.query_sequence[pr.query_position]] += 1
    return c


fa = None
hets, noise = [], []
for sample_pair in [(BLOOD, TUMOR)]:
    for chrom, start, end in regions:
        batch = 1 if (chrom, start) in {(l.split()[0], l.split()[1]) for l in open("regions_batch1.bed")} else 2
        b = pysam.AlignmentFile(f"bams/{BLOOD}.batch{batch}.bam")
        t = pysam.AlignmentFile(f"bams/{TUMOR}.batch{batch}.bam")
        for pos in range(int(start) + 50, int(end) - 50):  # stay away from slice edges
            if any(ch == chrom and abs(p - pos) <= 30 for ch, p in cand_pos):
                continue  # skip the candidate variants themselves
            cb = base_counts(b, chrom, pos)
            db = sum(cb.values())
            if db < 20:
                continue
            ref, _ = cb.most_common(1)[0]
            alt, na = (cb.most_common(2)[1] if len(cb) > 1 else ("N", 0))
            if 0.3 <= na / db <= 0.7:
                ct = base_counts(t, chrom, pos); dt = sum(ct.values())
                hets.append((chrom, pos, ref, alt, na, db, ct[alt], dt))
            else:
                noise.append(na / db)

print("Positive control: inherited heterozygous SNPs found in the slices (blood 30-70% alt)")
for chrom, pos, ref, alt, na, db, ta, dt in hets:
    print(f"  {chrom}:{pos} {ref}>{alt}   blood {na}/{db} ({100 * na / db:.0f}%)   tumor {ta}/{dt} ({100 * ta / dt:.0f}%)")
n = len(noise)
print(f"Negative control: {n} other positions with >=20 reads in {BLOOD}")
print(f"  median alt fraction {100 * sorted(noise)[n // 2]:.2f}%;  positions with >=3% alt: {sum(x >= 0.03 for x in noise)}"
      f";  with >=5%: {sum(x >= 0.05 for x in noise)}")
