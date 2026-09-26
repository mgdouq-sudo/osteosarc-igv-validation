# Validation of the read-count pipeline

Checked 2026-09-26 on the 11 osteosarcoma candidates (5 samples: T0/T1/T2 tumor, T0/T1 blood).
Scripts are in this folder; run each from `~/osteosarc_sv/igv`.

| # | Check | Script | Result |
|---|---|---|---|
| 1 | Independent recount with `samtools mpileup` (same filters) | `check_samtools.py` | **50/50 alt counts identical** (after the fix below) |
| 2 | Compare with the callers' read counts (DRAGEN, Mutect2, PURPLE `AD`) | `check_callers.py` | SNVs agree within 1-2 reads; indels: ours lower (see limitation) |
| 3 | Positive control: inherited heterozygous SNPs | `check_controls.py` | chr6:117301070 48% blood / 46% tumor; chr8:102560764 40% / 45% |
| 4 | Negative control: all other positions in the slices | `check_controls.py` | 6,050 positions, median 0.00% alt; only 3 reach 5% |
| 5 | Same result twice | rerun `count_support.py` | byte-identical output |

## Bug found and fixed

The indel counter counted both reads of an overlapping read pair, so one DNA molecule could count twice.
It now counts each molecule once, like the SNV and SV counters already did. Mostly affected T0 (shorter
fragments), e.g. H1-2 T0 tumor 17/137 -> 10/91. No verdict changed; blood stays at 0 for every variant.
Counts before the fix: `support_counts_before_fix.tsv`.

## Known limitations

- **Indel support is conservative.** Reads that end inside a deletion are soft-clipped by the aligner rather
  than aligned across it, and are not counted. Callers realign these. At MAP2 T1, 8 tumor reads (0 blood) are
  clipped exactly at the deletion edge: 24 counted vs 37 in PURPLE. Undercounts support; never invents it.
- **Indel depth ignores base quality** at the site, so it can be up to ~12% higher than samtools' depth
  (MAP2 only). Alt counts are unaffected.
- The SV counter handles two-breakpoint rearrangements (BND) only.
