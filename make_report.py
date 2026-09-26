"""Build the IGV validation report from the counts, verdicts and captioned screenshots.

Inputs:  support_counts_all.tsv (count_support.py), verdicts.tsv, snapshots_T1_captioned/*.png
Outputs: report/report.html (single self-contained file, images embedded)
         report/report.md   (renders on GitHub; images linked from snapshots_T1_captioned/)

Automatic flags are computed from the read counts only, so anyone can check them.
The verdict column is the reviewer's call after looking at the reads in IGV.
"""
import base64
import csv
import datetime
import glob
import html
import os

SAMPLES = ["T0_tumor", "T0_blood", "T1_tumor", "T1_blood", "T2_tumor"]
TIME = {"T0": "T0 (Dec 2022)", "T1": "T1 (Jun 2024)", "T2": "T2 (Jan 2025)"}
LABEL = {"true": "True", "artifact": "Artifact", "weak": "Weak", "not_supported": "Not supported"}

counts = {}
with open("support_counts_all.tsv") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        counts[(r["id"], r["sample"])] = r
with open("verdicts.tsv") as fh:
    V = list(csv.DictReader(fh, delimiter="\t"))
shots = {os.path.basename(p).split("_")[0]: p for p in glob.glob("snapshots_T1_captioned/*.png")}


def is_sv(r):
    return r["alt_reads"].startswith("split=")


def support(r):
    """(supporting reads, depth, short text) for one sample."""
    if is_sv(r):
        kv = dict(x.split("=") for x in r["alt_reads"].split(";"))
        n = int(kv["union"])
        return n, int(r["depth"]), f"{n} ({kv['split']} split, {kv['discordant']} pairs) / {r['depth']}"
    n, d = int(r["alt_reads"]), int(r["depth"])
    return n, d, f"{n}/{d} ({r['vaf_pct']}%)"


def pair(v):
    tp = v["timepoint"]
    return f"{tp}_tumor", ("T1_blood" if tp == "T2" else f"{tp}_blood")


def flags(v):
    """Rule-based checks on the displayed tumor/blood pair."""
    tum, bld = pair(v)
    t, b = counts[(v["count_id"], tum)], counts[(v["count_id"], bld)]
    n, d, _ = support(t)
    nb, _, _ = support(b)
    out = []
    if nb > 0:
        out.append(f"{nb} supporting read{'s' if nb > 1 else ''} in blood")
    if n < 3:
        out.append("fewer than 3 supporting reads")
    elif d and 100 * n / d < 5:
        out.append("under 5% of reads")
    if not is_sv(t) and n >= 4:
        fwd, rev = int(t["alt_fwd"]), int(t["alt_rev"])
        if min(fwd, rev) == 0:
            out.append(f"all on one strand (chance alone: about 1 in {2 ** (n - 1):,})")
        if int(t["alt_within10bp_of_read_end"]) / n > 0.5:
            out.append("mostly near read ends")
    if v["timepoint"] != "T1":
        t1, _, txt = support(counts[(v["count_id"], "T1_tumor")])
        out.append(f"not seen at T1 (T1 tumor {txt})")
    return out


def timecourse(cid):
    return [support(counts[(cid, s)])[2] for s in SAMPLES]


rows = []
for v in V:
    tum, bld = pair(v)
    rows.append(dict(v=v, tum=support(counts[(v["count_id"], tum)])[2], bld=support(counts[(v["count_id"], bld)])[2],
                     tum_name=tum.replace("_", " "), bld_name=bld.replace("_", " "), flags=flags(v),
                     course=timecourse(v["count_id"])))

tally = {k: sum(r["v"]["category"] == k for r in rows if r["v"]["shot_id"] != "C4b") for k in LABEL}
n_variants = sum(tally.values())
today = datetime.date.today().isoformat()
os.makedirs("report", exist_ok=True)

# ---------- Markdown (GitHub) ----------
md = [f"# IGV validation report: osteosarcoma WGS", "",
      f"Generated {today} by `make_report.py`. Patient data from osteosarc.com (shared publicly by the patient).", "",
      f"**{n_variants} candidate variants checked:** {tally['true']} true, {tally['artifact']} artifact, "
      f"{tally['weak']} weak, {tally['not_supported']} not supported.", "",
      "Each variant is shown as one tumor track above its matched blood track, at T1 (Jun 2024) unless it was "
      "only called at another time point. Read counts come from the BAM files (pysam; MAPQ>=20, base quality>=20, "
      "duplicates removed), not from the screenshots. Flags are automatic checks on those counts; the verdict is the "
      "reviewer's call after looking at the reads in IGV.", "",
      "| ID | Gene | Variant | Shown at | Tumor support | Blood support | Flags | Verdict |",
      "|---|---|---|---|---|---|---|---|"]
for r in rows:
    v = r["v"]
    md.append(f"| {v['shot_id']} | {v['gene']} | {v['label'].replace('  ', ' ')} | {v['timepoint']} | {r['tum']} | "
              f"{r['bld']} | {'; '.join(r['flags']) or 'none'} | **{v['verdict']}** |")
md += ["", "## Variants", ""]
for r in rows:
    v = r["v"]
    md += [f"### {v['shot_id']} {v['gene']}: {v['verdict']}", "", v["reason"], "",
           f"![{v['gene']} IGV screenshot](../{shots[v['shot_id']]})", ""]
md += ["## Read support across all time points", "",
       "| ID | Gene | " + " | ".join(s.replace("_", " ") for s in SAMPLES) + " |",
       "|---|---|" + "---|" * len(SAMPLES)]
for r in rows:
    if r["v"]["shot_id"] == "C4b":
        continue
    md.append(f"| {r['v']['count_id']} | {r['v']['gene']} | " + " | ".join(r["course"]) + " |")
md += ["", "No blood sample was taken at T2, so T2 tumor calls are compared with T1 blood.", ""]
open("report/report.md", "w").write("\n".join(md))

# ---------- HTML (single file) ----------
e = html.escape


def img64(p):
    return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()


table = "".join(
    f"<tr><td><a href='#{e(r['v']['shot_id'])}'>{e(r['v']['shot_id'])}</a></td><td><b>{e(r['v']['gene'])}</b></td>"
    f"<td>{e(r['v']['label'])}</td><td>{e(r['v']['timepoint'])}</td><td class=num>{e(r['tum'])}</td>"
    f"<td class=num>{e(r['bld'])}</td><td>{'<br>'.join(e(f) for f in r['flags']) or '<span class=muted>none</span>'}</td>"
    f"<td><span class='badge {r['v']['category']}'>{e(r['v']['verdict'])}</span></td></tr>" for r in rows)
cards = "".join(
    f"<section class=card id='{e(r['v']['shot_id'])}'><header><h3>{e(r['v']['shot_id'])} {e(r['v']['gene'])}"
    f" <span class=loc>{e(r['v']['label'])}</span></h3><span class='badge {r['v']['category']}'>{e(r['v']['verdict'])}</span></header>"
    f"<p>{e(r['v']['reason'])}</p><dl><dt>{e(r['tum_name'])}</dt><dd>{e(r['tum'])}</dd><dt>{e(r['bld_name'])}</dt><dd>{e(r['bld'])}</dd>"
    f"<dt>Flags</dt><dd>{'; '.join(e(f) for f in r['flags']) or 'none'}</dd></dl>"
    f"<details><summary>IGV screenshot ({e(TIME[r['v']['timepoint']])})</summary>"
    f"<img loading=lazy src='{img64(shots[r['v']['shot_id']])}' alt='{e(r['v']['gene'])} IGV screenshot'></details></section>"
    for r in rows)
course = "".join(
    f"<tr><td>{e(r['v']['count_id'])}</td><td><b>{e(r['v']['gene'])}</b></td>" + "".join(f"<td class=num>{e(c)}</td>" for c in r["course"]) + "</tr>"
    for r in rows if r["v"]["shot_id"] != "C4b")
stats = "".join(f"<div class='stat {k}'><b>{tally[k]}</b><span>{LABEL[k]}</span></div>" for k in LABEL)

page = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>IGV Validation Report</title><style>
:root{{--bg:#fbfaf8;--fg:#1d1d1b;--muted:#6b6a66;--card:#fff;--line:#e4e1db;--true:#1f7a4d;--true-bg:#e3f3ea;
--artifact:#a23b2a;--artifact-bg:#f8e4df;--weak:#8a6200;--weak-bg:#f7edd2;--not_supported:#555;--not_supported-bg:#ebebea}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#181817;--fg:#ecebe7;--muted:#a09e98;--card:#222220;--line:#3a3935;
--true:#7fd3a5;--true-bg:#1e3a2b;--artifact:#f0a292;--artifact-bg:#45251f;--weak:#e8c46c;--weak-bg:#3d3219;--not_supported:#c4c4c0;--not_supported-bg:#34342f}}}}
:root[data-theme=dark]{{--bg:#181817;--fg:#ecebe7;--muted:#a09e98;--card:#222220;--line:#3a3935;--true:#7fd3a5;--true-bg:#1e3a2b;
--artifact:#f0a292;--artifact-bg:#45251f;--weak:#e8c46c;--weak-bg:#3d3219;--not_supported:#c4c4c0;--not_supported-bg:#34342f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,system-ui,"Segoe UI",sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:32px 16px 64px}}h1{{font-size:28px;margin:0 0 4px}}h2{{margin:40px 0 12px;font-size:20px}}
.muted,.sub{{color:var(--muted)}}.stats{{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:120px}}
.stat b{{display:block;font-size:26px}}.stat.true b{{color:var(--true)}}.stat.artifact b{{color:var(--artifact)}}.stat.weak b{{color:var(--weak)}}
.scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}}th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{font-weight:600;color:var(--muted)}}td.num{{font-variant-numeric:tabular-nums;white-space:nowrap}}a{{color:inherit}}
.badge{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}}
.badge.true{{color:var(--true);background:var(--true-bg)}}.badge.artifact{{color:var(--artifact);background:var(--artifact-bg)}}
.badge.weak{{color:var(--weak);background:var(--weak-bg)}}.badge.not_supported{{color:var(--not_supported);background:var(--not_supported-bg)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:14px 0}}
.card header{{display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap}}.card h3{{margin:0;font-size:17px}}
.loc{{font-weight:400;color:var(--muted);font-size:14px}}dl{{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:10px 0;font-size:14px}}
dt{{color:var(--muted)}}dd{{margin:0}}summary{{cursor:pointer;color:var(--muted);margin-top:6px}}img{{max-width:100%;margin-top:10px;border:1px solid var(--line);border-radius:6px}}
</style></head><body><main>
<h1>IGV validation report</h1><div class=sub>Osteosarcoma WGS (osteosarc.com, shared publicly by the patient) · generated {today}</div>
<div class=stats>{stats}</div>
<p>{n_variants} candidate variants. Each is shown as one tumor track above its matched blood track, at T1 (Jun 2024) unless it was only called at another time point.
Read counts come from the BAM files (pysam; MAPQ&ge;20, base quality&ge;20, duplicates removed), not from the screenshots.
<b>Flags</b> are automatic checks on those counts; the <b>verdict</b> is the reviewer's call after looking at the reads in IGV.</p>
<h2>Summary</h2><div class=scroll><table><tr><th>ID</th><th>Gene</th><th>Variant</th><th>Shown at</th><th>Tumor support</th><th>Blood support</th><th>Flags</th><th>Verdict</th></tr>{table}</table></div>
<h2>Variants</h2>{cards}
<h2>Read support across all time points</h2><div class=scroll><table><tr><th>ID</th><th>Gene</th>{''.join(f'<th>{e(s.replace("_", " "))}</th>' for s in SAMPLES)}</tr>{course}</table></div>
<p class=muted>No blood sample was taken at T2, so T2 tumor calls are compared with T1 blood. Supporting reads for the translocation are split reads plus discordant pairs.</p>
</main></body></html>"""
open("report/report.html", "w").write(page)
print(f"report/report.html ({os.path.getsize('report/report.html') // 1024} KB), report/report.md")
