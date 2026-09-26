"""Check 2: compare our tumor/normal alt counts with the read counts (AD) the callers wrote in their VCFs.

Callers apply their own read filters and local realignment, so small differences are expected;
large disagreements (or a caller seeing reads where we see none) would point to a counting problem.
Run from ~/osteosarc_sv/igv:  python validation/check_callers.py
"""
import csv
import re
import subprocess

src = open("count_support.py").read()
CANDS = eval(re.search(r"CANDS = (\[.*?\n\])", src, re.S).group(1))
VCF = {"DRAGEN": "../snv_all/DRAGEN_{t}.vcf.gz", "Mutect2": "../snv_all/MUTECT2_{t}.cand.vcf.gz",
       "PURPLE": "../snv_all/PURPLE_{t}.vcf.gz"}
NORMAL = {"T0": "T0_blood", "T1": "T1_blood", "T2": "T1_blood"}  # T2 was called against the T1 blood

ours = {}
with open("support_counts_all.tsv") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        ours[(r["id"], r["sample"])] = r


def caller_ad(path, chrom, pos, ref, alt):
    """(normal alt, normal depth, tumor alt, tumor depth) from AD, or None if the site isn't in the VCF."""
    out = subprocess.run(["bcftools", "query", "-r", f"{chrom}:{pos}", "-f", "%POS\t%REF\t%ALT[\t%AD]\n", path],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        f = line.split("\t")
        if int(f[0]) != pos:
            continue
        alts = f[2].split(",")
        same = f[1] == ref and alt in alts if "N" not in ref else len(f[1]) - len(alts[0]) == len(ref) - len(alt)
        if not same:
            continue
        k = 1 + (alts.index(alt) if alt in alts else 0)
        (n, t) = [list(map(int, x.replace(".", "0").split(","))) for x in f[3:5]]
        return n[k], sum(n), t[k], sum(t)
    return None


rows = []
for cid, gene, chrom, pos, ref, alt in CANDS:
    for tp in ["T0", "T1", "T2"]:
        o_t, o_n = ours[(cid, f"{tp}_tumor")], ours[(cid, NORMAL[tp])]
        for caller, pat in VCF.items():
            ad = caller_ad(pat.format(t=tp), chrom, pos, ref, alt)
            if ad is None:
                continue
            rows.append([cid, gene, tp, caller, f"{o_t['alt_reads']}/{o_t['depth']}", f"{ad[2]}/{ad[3]}",
                         f"{o_n['alt_reads']}/{o_n['depth']}", f"{ad[0]}/{ad[1]}"])

w = csv.writer(open("validation/check_callers.tsv", "w"), delimiter="\t")
w.writerow(["id", "gene", "timepoint", "caller", "tumor_ours", "tumor_caller", "normal_ours", "normal_caller"])
w.writerows(rows)
for r in rows:
    print("\t".join(r))
