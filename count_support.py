"""Count read support for each IGV candidate in each sample BAM slice.

SNVs: reads carrying ALT base at POS (MAPQ>=20, BQ>=20, no dups/secondary).
Indels: reads with an indel of the same length starting within +-5 bp of POS.
SV (CDKN2B-PARD3B BND): split reads (SA tag to mate chrom near mate bp) and
discordant pairs (mate mapped to mate chrom within 1 kb of mate bp).
Also reports strand balance and how many alt reads have the variant within
10 bp of a read end (a common artifact signature).
"""
import csv
import sys

import pysam

SAMPLES = ["T0_tumor", "T0_blood", "T1_tumor", "T1_blood", "T2_tumor"]
CANDS = [
    # id, gene, chrom, pos(1-based), ref, alt
    ("C1", "H1-2", "chr6", 26055824, "N" * 16, "N"),  # 15 bp in-frame deletion
    ("C5", "ATRX", "chrX", 77599465, "C", "T"),
    ("C2", "DOT1L", "chr19", 2214506, "G", "A"),
    ("C3", "ROBO2", "chr3", 77607853, "C", "A"),
    ("C8", "MAP2", "chr2", 209694772, "GGCTACTGTGTGTTCAATAAGTACACAGT", "G"),
    ("C7", "ZNRF3", "chr22", 29049913, "G", "A"),
    ("C6", "ROS1", "chr6", 117301021, "G", "T"),
    ("C9", "FGFR3", "chr4", 1805817, "GC", "G"),
    ("C10", "USH2A", "chr1", 215650752, "C", "A"),
    ("C11", "ODF1", "chr8", 102560579, "G", "T"),
]
# H1-2 and ATRX were sliced into the batch1 BAMs, everything else into batch2
BATCH1 = {"C1", "C5"}
SV = ("C4", "CDKN2B-PARD3B", "chr9", 22007648, "chr2", 205310103)


def ok(r):
    return not (r.is_unmapped or r.is_duplicate or r.is_secondary
                or r.is_supplementary or r.is_qcfail) and r.mapping_quality >= 20


def snv(bam, chrom, pos, alt):
    depth, hits = 0, []
    for col in bam.pileup(chrom, pos - 1, pos, truncate=True, min_base_quality=20,
                          stepper="nofilter", ignore_orphans=False):
        for pr in col.pileups:
            r = pr.alignment
            if not ok(r) or pr.is_del or pr.is_refskip or pr.query_position is None:
                continue
            depth += 1
            qp = pr.query_position
            if r.query_sequence[qp] == alt:
                hits.append((r.is_reverse, min(qp, r.query_length - 1 - qp), r.mapping_quality))
    return depth, hits


def indel(bam, chrom, pos, ref, alt):
    size = len(alt) - len(ref)  # negative = deletion
    # Count molecules, not reads: when the two reads of a pair overlap they cover the same DNA,
    # and counting both would double it (the SNV pileup already handles this).
    depth, hits = set(), {}
    for r in bam.fetch(chrom, pos - 1, pos + 1):
        if not ok(r) or r.reference_start > pos - 1 or r.reference_end < pos + 1:
            continue
        depth.add(r.query_name)
        rp, qp = r.reference_start, 0
        for op, n in r.cigartuples:
            if op in (0, 7, 8):
                rp += n; qp += n
            elif op == 1:  # insertion
                if size > 0 and n == size and abs(rp - pos) <= 5:
                    hits.setdefault(r.query_name, (r.is_reverse, min(qp, r.query_length - qp), r.mapping_quality)); break
                qp += n
            elif op == 2:  # deletion
                if size < 0 and n == -size and abs(rp - pos) <= 5:
                    hits.setdefault(r.query_name, (r.is_reverse, min(qp, r.query_length - qp), r.mapping_quality)); break
                rp += n
            elif op == 4:
                qp += n
    return len(depth), list(hits.values())


def sv(bam, c1, p1, c2, p2):
    split, disc, depth = set(), set(), 0
    for r in bam.fetch(c1, p1 - 500, p1 + 500):
        if not ok(r):
            continue
        if r.reference_start <= p1 <= r.reference_end:
            depth += 1
        if r.has_tag("SA"):
            for sa in r.get_tag("SA").strip(";").split(";"):
                ch, sp = sa.split(",")[:2]
                if ch == c2 and abs(int(sp) - p2) < 500:
                    split.add(r.query_name)
        if r.is_paired and not r.mate_is_unmapped and r.next_reference_name == c2 \
                and abs(r.next_reference_start - p2) < 1000:
            disc.add(r.query_name)
    return depth, split, disc


out = csv.writer(sys.stdout, delimiter="\t")
out.writerow(["id", "gene", "sample", "depth", "alt_reads", "vaf_pct", "alt_fwd", "alt_rev",
              "alt_within10bp_of_read_end", "alt_mean_mapq"])
for sample in SAMPLES:
    bam = pysam.AlignmentFile(f"bams/{sample}.batch2.bam")
    bam1 = pysam.AlignmentFile(f"bams/{sample}.batch1.bam")
    for cid, gene, chrom, pos, ref, alt in CANDS:
        b = bam1 if cid in BATCH1 else bam
        if len(ref) == 1 and len(alt) == 1:
            d, h = snv(b, chrom, pos, alt)
        else:
            d, h = indel(b, chrom, pos, ref, alt)
        n = len(h)
        out.writerow([cid, gene, sample, d, n, f"{100 * n / d:.1f}" if d else "NA",
                      sum(not x[0] for x in h), sum(x[0] for x in h), sum(x[1] < 10 for x in h),
                      f"{sum(x[2] for x in h) / n:.0f}" if n else "NA"])
    cid, gene, c1, p1, c2, p2 = SV
    d, s, dd = sv(bam, c1, p1, c2, p2)
    out.writerow([cid, gene, sample, d, f"split={len(s)};discordant={len(dd)};union={len(s | dd)}",
                  f"{100 * len(s | dd) / d:.1f}" if d else "NA", "", "", "", ""])
