<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 27
Human:   Eric Edsinger
Purpose: Full audit writeup — which Pfam domains uniquely capture ion
         channels, and which superficially-similar Pfams must be excluded
         because they cross into non-channel families.
============================================================================ -->

# Pfam ion-channel domain audit — 2026-05-27

This document is the static, durable record of the Pfam audit that
underpins the `z_dark_sono` subproject. It captures the architecture
classification, the keeper list, the excluded promiscuous Pfams, and the
verification methodology. The corresponding live manifest is
`ion_channel_pfam_manifest-2026may27.tsv` in this same directory.

---

## Context and goal

The `z_dark_sono` subproject identifies species70 proteins that are
likely to be ion channels AND have no clear human ortholog. The
operational definition: a species70 protein is a dark_sono candidate if

1. It carries at least one Pfam domain on the curated ion-channel list
   (this document), AND
2. Its orthogroup (from `orthogroups/BLOCK_orthohmm`) does NOT contain a
   *Homo sapiens* member.

Channels lacking a clean channel-specific Pfam (CFTR, TMC1/2, CLIC1–6)
are intentionally out of scope; see the "Why BLAST-based capture was
considered and rejected" section below and the live
`out_of_scope_channels-2026may27.tsv` for the documented list.

The hard constraint on the Pfam list, set by the researcher, is:

> "We need to strictly avoid anything that would be promiscuous with a
> non-ion channel gene family. It would be ok if some members within an
> ion channel family have lost channel functionality."

That allows in-family channel↔transporter or channel↔scramblase
divergence (CLC, TMEM16) but disallows Pfams that hit unrelated protein
families (e.g., MIR, which is shared with mannosyltransferases).

---

## The two pore-domain Pfams (what "pore domain" actually means in Pfam)

There are two Pfam IDs in clan **CL0030** ("Ion channel") that together
capture the canonical tetrameric cation-channel pore-loop superfamily.
They differ in whether the voltage-sensor-like four-helix bundle is
attached:

| Pfam | Architecture | Captures |
|------|--------------|----------|
| **PF00520** (`Ion_trans`) | 6 TM = voltage-sensor-like S1–S4 + pore S5-loop-S6 | Nav, Cav, Kv (all), TRP (all subfamilies), CNG, HCN, NALCN, KCNQ, BK, SK, IK |
| **PF07885** (`Ion_chan`)  | 2 TM = pore only (no voltage sensor) | K2P (twice per subunit — tandem pore), bacterial K⁺ (KcsA-like), some 2-TM K-like |

PF01007 (`IRK`) is the Kir-family-specific 2-TM variant.

These three Pfams are the **core architectural hub**. Every member of the
Pfam clan CL0030 is in a cation channel by construction.

> **Verified**: human TRPV1 (Q8NER1), TRPA1 (O75762), and all 27 human
> TRPs carry PF00520 in the local annotation file
> `subprojects/annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/pfam-Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens.tsv`.
> Same file confirms human RYR1, RYR2, ITPR1, ITPR2, ITPR3 carry PF00520
> (their pore region). PF07885 is for K2P-style architectures only and
> does NOT hit TRPs.

---

## The 17 architecture groups (Table 1)

| Architecture | Stoichiometry | Pfam(s) | Channel families |
|--------------|---------------|---------|------------------|
| Voltage-gated 6TM cation (S1–S4 sensor + S5-pore-S6) | tetramer (or 4× internal repeat) | PF00520 | Nav, Cav, Kv, **TRP (all subfamilies)**, CNG, HCN, NALCN, KCNQ, BK, SK, IK |
| Minimal 2TM pore module | tetramer (K2P: dimer of 2× pore) | PF07885 | K2P (TWIK/TASK/TREK/TRAAK/TRESK/THIK/TALK), bacterial K⁺ (KcsA-like) |
| Kir 2TM variant | tetramer | PF01007 | Kir1–Kir7 (inward rectifiers) |
| Pentameric Cys-loop | pentamer | PF02931 (LBD) + PF02932 (TM) | nAChR, GABA-A, GlyR, 5-HT₃ |
| Tetrameric ionotropic glutamate | tetramer | PF00060 (TM) + PF10613 (LBD) | NMDA, AMPA, kainate |
| Trimeric ENaC/Degenerin | trimer | PF00858 | ENaC, ASIC, degenerin, FaNaC |
| Trimeric P2X | trimer | PF00864 | P2X1–P2X7 |
| Piezo propeller-blade | trimer | PF12166 | Piezo1, Piezo2 |
| OSCA/TMEM63 11-TM | dimer | PF02714 | OSCA1–3, TMEM63A/B/C |
| Bacterial small-conductance mechanosensitive | heptamer | PF01030 | MscS family |
| Bacterial large-conductance mechanosensitive | pentamer | PF01741 | MscL family |
| Intracellular Ca²⁺ release | tetramer | PF08709, PF01365, PF08454, PF02026, PF06459, PF21119 (+ PF00520 for pore) | RyR1–3, IP3R1–3 |
| Hexameric gap-junction "large pore" | hexamer | PF00029 | Vertebrate connexins (Cx26, Cx32, …) |
| Octameric gap-junction "large pore" | octamer | PF00876 | Invertebrate innexins + vertebrate pannexins |
| Double-barrel CLC | dimer (two pores) | PF00654 | CLC-1, CLC-2, CLC-Ka/b (channels); CLC-3 to CLC-7 (Cl⁻/H⁺ antiporters) |
| Anoctamin/TMEM16 | dimer | PF04547 | TMEM16A/B (channels); TMEM16C–K (channels/scramblases) |
| Bestrophin | pentamer | PF01062 | BEST1–BEST4 |

---

## The 24 keeper Pfams (Table 2)

The flat list, in architecture-group order. This is the canonical set
read by the workflow.

| # | Pfam | Short name | Architecture group | Specificity |
|---|------|------------|---------------------|-------------|
|  1 | PF00520 | Ion_trans | voltage_gated_6tm_cation | channel-specific; also pore region of RyR/IP3R |
|  2 | PF07885 | Ion_chan | minimal_2tm_pore | channel-specific |
|  3 | PF01007 | IRK | kir_2tm | Kir1–Kir7 |
|  4 | PF02931 | Neur_chan_LBD | pentameric_cys_loop | nAChR/GABA-A/GlyR/5-HT₃ ligand binding |
|  5 | PF02932 | Neur_chan_memb | pentameric_cys_loop | nAChR/GABA-A/GlyR/5-HT₃ TM/pore |
|  6 | PF00060 | Lig_chan | tetrameric_iglur | NMDA/AMPA/kainate TM/pore |
|  7 | PF10613 | Lig_chan-Glu_bd | tetrameric_iglur | NMDA/AMPA/kainate ligand binding |
|  8 | PF00858 | ASC | trimeric_enac_degenerin | ENaC/ASIC/degenerin/FaNaC |
|  9 | PF00864 | P2X_receptor | trimeric_p2x | P2X1–P2X7 |
| 10 | PF12166 | Piezo | piezo_blade | Piezo1, Piezo2 |
| 11 | PF02714 | RSN1_7TM | osca_tmem63 | OSCA1–3, TMEM63A/B/C |
| 12 | PF01030 | MS_channel | bacterial_mscs | MscS family |
| 13 | PF01741 | MscL | bacterial_mscl | MscL family |
| 14 | PF08709 | Ins145_P3_rec | intracellular_ca_release | RyR + IP3R (both; verified locally) |
| 15 | PF01365 | RIH | intracellular_ca_release | RyR + IP3R (both) |
| 16 | PF08454 | RIH_assoc | intracellular_ca_release | RyR + IP3R (both) |
| 17 | PF02026 | RyR | intracellular_ca_release | RyR only |
| 18 | PF06459 | RR_TM4-6 | intracellular_ca_release | RyR only (pore region) |
| 19 | PF21119 | RyR_junc_solenoid | intracellular_ca_release | RyR only |
| 20 | PF00029 | Connexin | gap_junction_hexamer | Vertebrate connexins |
| 21 | PF00876 | Innexin | gap_junction_octamer | Invertebrate innexins + vertebrate pannexins |
| 22 | PF00654 | Voltage_CLC | double_barrel_clc | CLC channels + CLC Cl⁻/H⁺ antiporters |
| 23 | PF04547 | Anoctamin | anoctamin_tmem16 | TMEM16 channels + TMEM16 scramblases |
| 24 | PF01062 | Bestrophin | bestrophin | BEST1–BEST4 |

---

## Excluded Pfams (and why)

These Pfams looked tempting (some appear on ion channels) but FAIL the
strict "no cross-family promiscuity" criterion. They are NOT in the
manifest.

| Pfam | Name | Why excluded |
|------|------|--------------|
| **PF02815** | `MIR` | Stands for **M**annosyltransferase / **I**P3R / **R**yR. Found in protein O-mannosyltransferases (Pmt1–Pmt4), stromal cell-derived factor 2 (SDF2L1), and other non-channel families. The β-trefoil fold is a *carbohydrate-binding* fold in mannosyltransferases. |
| **PF00622** | `SPRY` | Found in TRIM family (E3 ligases), butyrophilins, USP family (deubiquitinases), NLRP family inflammasomes, and many other non-channel proteins. Annotated on RyR but useless as a channel marker. |
| **PF13499** | `EF-hand_7` | EF-hand pairs are in calmodulin, troponin, S100 family, parvalbumin, and **hundreds** of non-channel Ca-binding proteins. Annotated on RyR2 but useless as a channel marker. |
| **PF01094** | `ANF_receptor` (PBP1-like) | Found in metabotropic glutamate receptors (mGluRs — GPCRs, not channels), GABA-B receptors (GPCRs), atrial natriuretic peptide / particulate guanylate cyclase receptors, and bacterial periplasmic binding proteins. The "Venus-fly-trap" fold predates ion channels. |
| **PF00023** | `Ank` | Ankyrin repeats are in transcription factors, cytoskeletal adaptors, signaling proteins, and over a thousand unrelated proteins. Massively promiscuous. |
| **PF00027** | `cNMP_binding` | Cyclic nucleotide binding domain — found in PKA, PKG, EPAC, and CAP/CRP bacterial transcription factors. Non-channel. |
| **PF00005** + **PF00664** | `ABC_tran` + `ABC_membrane` | Signatures of ALL ABC transporters (hundreds of them); CFTR is just one. Cannot isolate channel function via these. CFTR is documented as out of scope (see `out_of_scope_channels-2026may27.tsv`). |
| **PF02386** | `TrkH` | Bacterial K⁺ uptake transporters — classified as transporters, not channels. Borderline by definition; safest to exclude. |

---

## Channels with no clean Pfam (intentionally out of scope)

Three classes of ion channels lack a clean channel-specific Pfam ID
because their pore architecture is either shared with non-channel
relatives or not represented by a tight Pfam:

| Channel | Issue |
|---------|-------|
| **CFTR** | Only annotated by promiscuous ABC transporter Pfams (PF00664, PF00005) |
| **TMC1, TMC2** | InterPro family IPR012496 exists but no tight Pfam; additionally, TMC1/2 channel-vs-associator status is contested in the literature |
| **CLIC1–6** | Glutaredoxin-like fold shared with non-channel proteins |

The 9 human gene symbols are documented in `out_of_scope_channels-2026may27.tsv`
(file is NOT consumed by the workflow).

### Why BLAST-based capture was considered and rejected (2026-05-27)

An initial design included a per-species BLAST step that took each of
the 9 human channel sequences as query and ran blastp against every
species70 proteome (e-value 1e-5). This would yield candidate ion-channel
proteins in non-human species that could then be classified by
orthogroup membership — the same dark_sono logic, just with BLAST as the
discovery route instead of Pfam.

The approach was rejected because:

1. **Cross-family false positives at deep phylogenetic distance.**
   species70 spans from fungi/holozoans to chordates. BLAST homology
   between human CFTR and a fungal protein at e-value 1e-5 does not
   imply they are members of the same gene family — at that distance,
   fold homology pulls in unrelated proteins. CLIC is the worst case
   (glutaredoxin-like fold is shared with glutathione transferases,
   lipocalins, and many others), but CFTR (ABC fold) and TMC (broad
   transmembrane fold) suffer similar issues.

2. **The orthogroup filter doesn't save us.** Divergent cross-family
   proteins land in their OWN orthogroups (no human member) and would
   get called "dark_sono" — exactly the false-positive class the strict
   no-cross-family-promiscuity criterion is meant to avoid.

3. **TMC1/2 channel-vs-associator status is contested.** Recent
   structural work (Pan 2018, Jeong 2019, Akyuz 2023) supports
   TMC1 as pore-forming, but a reasonable subset of the field still
   treats TMC1/2 as channel-associated rather than channel-proper.
   They require accessory subunits (TMIE, LHFPL5, CIB2) to function.

4. **Same KIND of error as the excluded Pfams (MIR, SPRY, EF-hand).**
   We excluded those because they hit non-channel families *in human*.
   BLAST capture would produce the same error in *non-human species* —
   different route, same problem.

The cleaner design: Pfam-only. CFTR/TMC/CLIC become documented out of
scope. If the user later wants to ask about a specific gene's
non-human-orthologous paralogs, an orthogroup-membership inspection
(per-gene, hand-curated) gives clean results — but that's a separate
analysis, not part of this dark_sono pool.

---

## Verification methodology

The audit was cross-checked against local data, not just web search,
because Pfam web pages (InterPro SPA-loaded) return loading messages
rather than data through programmatic fetches. The ground-truth file
was:

```
subprojects/annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/
    pfam-Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens.tsv
```

For each candidate Pfam, the question "what does this annotate in human?"
was answered by:

```bash
awk -F'\t' '$1 ~ /g_GENE-/ {print $5"\t"$6}' "$HUMAN" | sort -u
```

For ITPR1/2/3 and RYR1/2 this returned:

```
PF00520	Ion transport protein
PF01365	RIH domain
PF02815	MIR domain
PF08454	RyR and IP3R Homology associated
PF08709	Inositol 1,4,5-trisphosphate/ryanodine receptor
+ (RYR-only:) PF02026, PF06459, PF21119
+ (promiscuous-on-RYR:) PF00622 (SPRY), PF13499 (EF-hand_7)
```

This is how PF08709's full scope (RyR + IP3R, not IP3R-only) was
confirmed, and how PF06459 and PF21119 (RyR-specific) were added to the
keeper list — they hadn't surfaced in earlier web searches.

---

## What this audit is NOT

- Not a comprehensive list of *every* Pfam ever associated with an ion
  channel. (Some borderline cases — TPK plant K⁺ channels via PF07885
  duplicate hits, some bacterial channels — are captured by the core
  three.)
- Not a guarantee that every hit in the workflow is a functional channel.
  Some members within an ion channel family have lost channel function
  (CLC transporters, TMEM16 scramblases). This is explicitly accepted —
  the researcher's criterion forbids cross-family promiscuity but allows
  within-family functional divergence.
- Not authoritative on rare or non-eukaryotic ion channel classes that
  are unlikely to be sonogenetic targets (e.g., highly bacterial-specific
  channels not represented in species70).

---

## Updates / corrections

When this audit is revised, append a `## YYYY-MM-DD revision` section
below with the change and rationale rather than editing the original
content. The manifest filename's date should also be bumped to reflect
the revision date.
