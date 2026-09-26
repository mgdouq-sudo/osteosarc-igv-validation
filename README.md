# IGV validation of osteosarcoma somatic mutations

Do the reads support the mutations the variant callers report? This repo checks 11 candidate
somatic mutations from a publicly shared osteosarcoma genome against the sequencing reads.
For each one it counts tumor and blood reads straight from the BAM files and shows the reads
in IGV, one tumor-over-blood screenshot per mutation.

The checks were run with **[igv-validator](https://github.com/mgdouq-sudo/ClawBio/tree/feat/igv-validator/skills/igv-validator)**,
a [ClawBio](https://github.com/ClawBio/ClawBio) skill built from the prototype pipeline in this repo.

## Data

Whole-genome sequencing shared publicly by the patient at [osteosarc.com](https://osteosarc.com)
(tumor at three time points, matched blood). Thanks to the patient for making the data open.

| Sample | Date | Lab |
|---|---|---|
| T0 tumor + blood | Dec 2022 | Personalis |
| T1 tumor + blood | Jun 2024 | UCLA |
| T2 tumor (compared with T1 blood; no T2 blood sample) | Jan 2025 | UCLA |

No reads are stored here. `samples.tsv` lists the source BAMs; only small slices around each
mutation were downloaded. Reference: Broad `Homo_sapiens_assembly38.fasta`, the build the BAMs were aligned to.

## Results

Each mutation is shown at T1 unless it was only called at another time point.

| ID | Gene | Mutation | Shown at | Tumor support | Blood | Flags | Skill status | Manual review |
|---|---|---|---|---|---|---|---|---|
| C1 | H1-2 | 15 bp in-frame deletion | T1 | 9/108 (8.3%) | 0/57 | none | supported | true |
| C2 | DOT1L | G>A p.Trp611Ter | T1 | 12/62 (19.4%) | 0/48 | none | supported | true |
| C3 | ROBO2 | C>A p.Asn1080Lys | T1 | 13/124 (10.5%) | 0/50 | none | supported | true |
| C4 | CDKN2B–PARD3B | t(2;9) translocation | T1 | 18 molecules (12 split, 6 pairs) | 0 | none | supported | true |
| C8 | MAP2 | 28 bp deletion p.Leu867fs | T1 | 29/85 (34.1%) | 0/70 | none | supported | true |
| C10 | USH2A | C>A p.Cys4728Phe | T0 | 15/40 (37.5%) | 0/37 | none | supported | true at T0 only |
| C7 | ZNRF3 | G>A p.Gly578Ser | T1 | 3/57 (5.3%) | 0/57 | none | supported | weak / unclear |
| C6 | ROS1 | G>T p.Ser2223Tyr | T1 | 6/94 (6.4%) | 0/64 | germline_site | flagged | likely artifact |
| C11 | ODF1 | G>T p.Val150Leu | T0 | 5/52 (9.6%) | 0/41 | strand_bias | flagged | artifact |
| C9 | FGFR3 | 1 bp deletion p.Pro573fs | T2 | 4/119 (3.4%) | 0/59 | low_vaf | flagged | weak / likely noise |
| C5 | ATRX | C>T p.Gly1968Arg | T1 | 2/66 (3.0%) | 0/30 | low_support; low_vaf | insufficient | not supported |

**Six mutations are well supported, three look like artifacts or noise, one is weak and one has too few reads.**
Read counts come from the BAMs (mapping quality ≥ 20, base quality ≥ 20, duplicates removed, each DNA
molecule counted once), never from the screenshots.

The skill's automatic status agrees with the manual review for 10 of 11. The exception is ZNRF3: it
just clears the thresholds at T1 (3 reads, 5.3%), but manual review also saw that it is absent at T2
despite deeper coverage. The skill checks one tumor/normal pair at a time, which is why its status is a
summary of the flags and not a verdict.

### Examples

**DOT1L, a clear somatic mutation:** 12 tumor reads carry the A, on both strands; none in blood.

![DOT1L](skill_results/T1/figures/igv/C2_DOT1L.png)

**ODF1, an artifact:** the 5 supporting reads are all on one strand and carry T's at three clustered
positions, a misalignment or damage pattern. It is absent from blood and from later tumors.

![ODF1](skill_results/T0/figures/igv/C11_ODF1.png)

The other screenshots are in `skill_results/T1`, `T0` and `T2` (each with a full `report.md`).

## Validation of the counting

Before the counts were trusted they were checked five ways (`validation/VALIDATION.md`):

| Check | Result |
|---|---|
| Independent recount with `samtools mpileup` | 50/50 alt counts identical |
| Callers' own read counts (DRAGEN, Mutect2, PURPLE) | SNVs within 1–2 reads |
| Positive control: inherited heterozygous SNPs | ~50% in blood and tumor |
| Negative control: 6,050 positions without a variant | median 0.00% alt |
| Same result twice | identical |

This caught one real bug: overlapping read pairs were counted twice for indels (now fixed).

## Repository layout

| Path | What it is |
|---|---|
| `skill_results/` | The igv-validator runs: `candidates.vcf` (the 11 mutations), per-time-point variant lists, and a report, screenshots, counts table and reproducibility bundle for T1, T0 and T2 |
| `validation/` | The five validation checks and their results |
| `igv_validation_results.tsv` | Manual review verdicts from the first pass |
| `count_support.py`, `batch_T1.igv`, `caption_snapshots.py`, `make_report.py`, `run_validation.sh`, `verdicts.tsv` | The original prototype pipeline, kept for reference |
| `report/`, `snapshots_T1*/`, `support_counts_all.tsv` | Prototype outputs |

## Reproduce

Install the skill from the ClawBio fork, download the BAM slices listed in `samples.tsv` and the
Broad hg38 FASTA, then run the command in `skill_results/<time point>/reproducibility/commands.sh`.

*This is a research and educational analysis, not a clinical test. It does not provide diagnoses.*
