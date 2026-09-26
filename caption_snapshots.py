"""Add a caption strip above each T1 IGV screenshot with the read counts from the BAM.

Counts come from support_counts_all.tsv (written by count_support.py), not from the image.
Raw screenshots stay in snapshots_T1/; captioned copies go to snapshots_T1_captioned/.
"""
import csv
import glob
import os

from PIL import Image, ImageDraw, ImageFont

TIME = {"T0": "T0 (Dec 2022)", "T1": "T1 (Jun 2024)", "T2": "T2 (Jan 2025)"}
# image id -> (count id, gene + variant label, verdict), shared with make_report.py
INFO = {}
with open("verdicts.tsv") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        INFO[r["shot_id"]] = (r["count_id"], f"{r['gene']}  {r['label']}", r["verdict"])

counts = {}
with open("support_counts_all.tsv") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        counts[(r["id"], r["sample"])] = r


def line(cid, sample):
    r = counts[(cid, sample)]
    name = sample.replace("_", " ")
    if r["alt_reads"].startswith("split="):
        kv = dict(x.split("=") for x in r["alt_reads"].split(";"))
        return (f"{name}: {kv['union']} supporting reads ({kv['split']} split, {kv['discordant']} discordant pairs)"
                f" of {r['depth']} at the breakpoint")
    alt, depth = int(r["alt_reads"]), int(r["depth"])
    s = f"{name}: {alt}/{depth} reads carry the variant ({r['vaf_pct']}%)"
    if alt:
        s += f", {r['alt_fwd']} forward / {r['alt_rev']} reverse strand"
    return s


font = "/System/Library/Fonts/Helvetica.ttc"
big, small = ImageFont.truetype(font, 26, index=1), ImageFont.truetype(font, 21)
os.makedirs("snapshots_T1_captioned", exist_ok=True)
for path in sorted(glob.glob("snapshots_T1/*.png")):
    fname = os.path.basename(path)
    img_id, _, tp = fname.split("_")[:3]
    cid, label, verdict = INFO[img_id]
    tumor = f"{tp}_tumor"
    blood = "T1_blood" if tp == "T2" else f"{tp}_blood"  # no blood sample was taken at T2
    rows = [(f"{img_id}  {label}   |   {TIME[tp]}", big),
            (line(cid, tumor), small),
            (line(cid, blood) + ("   (no blood sample at T2)" if tp == "T2" else ""), small),
            (f"IGV verdict: {verdict}", small),
            ("Counts come from the BAM (pysam; MAPQ>=20, base quality>=20, duplicates removed), not from the image.", small)]
    shot = Image.open(path).convert("RGB")
    pad, gap = 18, 10
    h = pad * 2 + sum(f.size for _, f in rows) + gap * (len(rows) - 1)
    out = Image.new("RGB", (shot.width, h + shot.height), "white")
    d = ImageDraw.Draw(out)
    y = pad
    for text, f in rows:
        d.text((pad, y), text, fill="black", font=f)
        y += f.size + gap
    d.line([(0, h - 1), (shot.width, h - 1)], fill=(180, 180, 180), width=2)
    out.paste(shot, (0, h))
    out.save(f"snapshots_T1_captioned/{fname}")
    print(fname)
