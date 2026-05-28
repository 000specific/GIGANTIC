<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: Orient AI assistants landing in the GIGANTIC framework repository on
         what this directory is, how users use it, and where AI sessions
         should actually be rooted for project work.
Scope:   GIGANTIC/ root (the github-versioned framework repository). For
         project work, the canonical AI session root is the user's renamed
         copy of gigantic_project-COPYME/.
History:
  2026-05-25  Initial version (Opus 4.7). First fill of this file as part of
              the documentation cleanup pass. Intentionally minimal — will be
              expanded as the cleanup pass progresses.
============================================================================ -->

# GIGANTIC — AI Guide

You are reading the AI guide at the root of the **GIGANTIC framework
repository**. This file orients AI assistants on what this directory is, how
users use it, and — most importantly — **where the canonical AI session for
real project work should be rooted**.

---

## What this directory is

`GIGANTIC/` is the GitHub-versioned framework repository. When a user clones
the repo from GitHub, they get this directory tree. It contains:

- `gigantic_project-COPYME/` — the project template the user copies and
  renames; everything the user actually runs lives inside this template
- Standard repository files (`LICENSE`, `CITATION.cff`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `.github/`)
- Branding assets, a demo placeholder
- Two top-level documents at this level: this file (`AI_GUIDE.md`) and the
  user-facing `README.md`. The research-grade behavior/posture document
  (`CLAUDE.md` / `AI_BEHAVIOR.md`) lives inside `gigantic_project-COPYME/`
  because research-grade posture is project-scoped and ships with each
  renamed project copy

`GIGANTIC/` itself is not where a user does science. It is the framework. It
ships; the user copies it.

GIGANTIC use is built around a given project implemented through human-AI chat. It provides a framework of subprojects containing automated bioinformatic and phylogenetic workflows under the hood. It includes extensive documentation at every turn - READMEs for humans and AI_GUIDEs for AIs. For the non-expert user, it is intended as a wandering yet guided - often surprising & hopefully more fun than frustrating - research conversation to explore species, genomes, ideas, and data with an AI in chat. One where the human is guided and guides - and the AI acts. GIGANTIC floats you along in conversation - but with an exosuit grounded in sequence exploration - built to provide rigorous tools and methods in phylogenomics - and less excitingly but perhaps most critically - on-demand and behind the scenes documentation of chat as a record of research development and implementation, providing provenance in support of attribution, transparency, reproducibility, and publication. In this sense, a GIGANTIC project serves as a digital research notebook for comparative genomic and phylogenetic work - intended in the end to be archived and maintained no differently than a lab notebook at the bench.

Species for the demo are below - species set is species42. It is built for discovery of gene and genome evolution within a comparative framework of deuterostomes. It leverages deep functional knowledge in human, mouse and to a lesser extent zebrafish - and in the worm and fly models as outgroups. Hippo & splattering of cetaceans - plus octopus - fill things out. Entry requirements into species42 included a public high-quality annotated genome.

*Demo species set (species42, 42 species, deuterostome-focused):*

| Phylum | Species | Common name | Genome |
|--------|---------|-------------|--------|
| Chordata | *Homo sapiens* | human | [GCF_000001405.40](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000001405.40/) |
| Chordata | *Mus musculus* | house mouse | [GCF_000001635.27](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000001635.27) |
| Chordata | *Danio rerio* | zebrafish | [GCF_049306965.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_049306965.1/) |
| Chordata | *Balaenoptera musculus* | blue whale | [GCF_009873245.2](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_009873245.2) |
| Chordata | *Megaptera novaeangliae* | humpback whale | [GCA_041834305.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_041834305.1/) |
| Chordata | *Balaenoptera borealis* | sei whale | [GCF_965194805.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_965194805.1) |
| Chordata | *Orcinus orca* | killer whale | [GCF_937001465.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_937001465.1) |
| Chordata | *Tursiops truncatus* | common bottlenose dolphin | [GCF_011762595.2](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_011762595.2) |
| Chordata | *Phocoena phocoena* | harbor porpoise | [GCF_963924675.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_963924675.1) |
| Chordata | *Hippopotamus amphibius kiboko* | hippo | [GCF_030028045.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_030028045.1) |
| Chordata (Cephalochordata) | *Branchiostoma floridae* | Floridian lancelet | [GCF_000003815.2](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000003815.2/) |
| Chordata (Cephalochordata) | *Branchiostoma lanceolatum* | Mediterranean amphioxus | [GCF_035083965.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_035083965.1/) |
| Chordata (Urochordata) | *Ascidia mentula* | sea squirt | [GCF_947561715.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_947561715.1/) |
| Chordata (Urochordata) | *Botryllus schlosseri* | star tunicate | [GCF_051294905.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_051294905.1/) |
| Chordata (Urochordata) | *Corella eumyota* | orange-tipped sea squirt | [GCF_963082875.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_963082875.1/) |
| Chordata (Urochordata) | *Phallusia mammillata* | white sea squirt | [GCF_965637545.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_965637545.1/) |
| Chordata (Urochordata) | *Styela clava* | rough sea squirt | [GCF_964204865.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_964204865.1/) |
| Chordata (Urochordata) | *Aplidium turbinatum* | colonial sea squirt | [GCF_918807975.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_918807975.1/) |
| Chordata (Urochordata) | *Ciona intestinalis* | vase tunicate | [GCF_018327825.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_018327825.1/) |
| Chordata (Urochordata) | *Clavelina lepadiformis* | light-bulb sea squirt | [GCF_947623445.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_947623445.1/) |
| Chordata (Urochordata) | *Oikopleura dioica* | larvacean | [GCF_907165135.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_907165135.1/) |
| Chordata (Urochordata) | *Thalia democratica* | salp | [GCF_965202585.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_965202585.1/) |
| Echinodermata | *Antedon bifida* | rosy feather star | [GCF_963402885.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_963402885.1/) |
| Echinodermata | *Asterias rubens* | European sea star | [GCF_902459465.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_902459465.1/) |
| Echinodermata | *Lytechinus pictus* | Cyclins Nobel Prize painted sea urchin | [GCF_037042905.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_037042905.1/) |
| Echinodermata | *Amphiura filiformis* | brittlestar | [GCF_039555335.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_039555335.1/) |
| Echinodermata | *Antedon mediterranea* | Mediterranean feather star | [GCF_964355755.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_964355755.1/) |
| Echinodermata | *Apostichopus japonicus* | Japanese sea cucumber | [GCF_037975245.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_037975245.1/) |
| Echinodermata | *Asterias amurensis* | Northern Pacific sea star | [GCF_032118995.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_032118995.1/) |
| Echinodermata | *Diadema setosum* | long-spined sea urchin | [GCF_964275005.2](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_964275005.2/) |
| Echinodermata | *Eupentacta fraudatrix* | sea cucumber | [GCA_056552365.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_056552365.1/) |
| Echinodermata | *Holothuria leucospilota* | black sea cucumber | [GCA_029531755.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_029531755.1/) |
| Echinodermata | *Lytechinus variegatus* | green sea urchin | [GCF_018143015.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_018143015.1/) |
| Echinodermata | *Mesocentrotus franciscanus* | red sea urchin | [GCA_037976565.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_037976565.1/) |
| Echinodermata | *Patiria miniata* | bat sea star | [GCF_015706575.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_015706575.1/) |
| Echinodermata | *Strongylocentrotus purpuratus* | purple sea urchin | [GCF_000002235.5](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000002235.5/) |
| Hemichordata | *Glandiceps talaboti* | enteropneust acorn worm | [GCF_964340395.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_964340395.1/) |
| Hemichordata | *Ptychodera flava* | enteropneust acorn worm | [GCF_041260155.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_041260155.1/) |
| Hemichordata | *Schizocardium californicum* | enteropneust acorn worm | [figshare:25816303](https://figshare.com/articles/dataset/Schizocardium_californicum/25816303) |
| Nematoda | *Caenorhabditis elegans* | roundworm | [GCF_000002985.6](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000002985.6/) |
| Arthropoda | *Drosophila melanogaster* | fruit fly | [GCF_000001215.4](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000001215.4/) |
| Mollusca | *Octopus bimaculoides* | California two-spot octopus | [GCF_001194135.2](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_001194135.2/) |

---

## How a user starts

1. **Clone** the repository from GitHub:
   ```
   git clone https://github.com/000generic/GIGANTIC.git
   ```
2. **Copy and rename** `gigantic_project-COPYME/` to a project-specific name,
   placing the copy outside `GIGANTIC/` so the framework and the user's
   project stay cleanly separated:
   ```
   cp -r GIGANTIC/gigantic_project-COPYME /path/to/work/gigantic_project-cephalopod_evolution
   ```
3. **Start a fresh, naive AI session rooted at the renamed project
   directory.** This is the canonical session root for every subsequent piece
   of work in that project. The user does not run an AI session at
   `GIGANTIC/` for project work; they run it at
   `gigantic_project-cephalopod_evolution/` (or whatever they named the copy).

---

## Why the AI session should be rooted at the renamed project

- Every project-level convention, input, output, `research_notebook/`,
  workflow, and AI session record lives inside the renamed project directory.
- The renamed directory is self-contained: it travels independently of
  `GIGANTIC/` and can be archived as the complete record of one research
  project.
- A fresh AI session rooted there starts with the right scope. It does not
  need to filter framework-development context out of every response.

---

## When you (the AI) are rooted at `GIGANTIC/`

Your job in a session rooted here is **framework development** — improving
the template, the conventions, the top-level docs — not project work.

If a user opens a session at `GIGANTIC/` and asks you to run analyses, set
up inputs, or work with their data, redirect them:

1. Ask them to copy and rename `gigantic_project-COPYME/` to a
   project-specific directory.
2. Ask them to start a fresh AI session rooted at that renamed directory.
3. Point them at `gigantic_project-<their-name>/AI_GUIDE.md` (which exists in
   their copy) to continue.

---

## Capture for framework-development sessions

Framework-development sessions (rooted at `GIGANTIC/`) are also research-worthy
work — architectural decisions, naming conventions, design pivots — and
deserve the same lossless capture that project sessions get. The
`GIGANTIC/.claude/` directory is gitignored, so it stays developer-personal,
but the developer can add the PreCompact hook locally:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/gigantic_project-COPYME/ai/ai_scripts/002_ai-python-hook_precompact_capture_transcript.py"
          }
        ]
      }
    ]
  }
}
```

With this in place, framework-dev sessions capture into the same
`gigantic_project-COPYME/research_notebook/research_ai/sessions/` directory
(gitignored, so captures stay local). See
`gigantic_project-COPYME/ai/ai_FYIs/gigantic_conventions.md` §9 for the full
chat-as-research-notebook architecture.

---

*The canonical list of conventions surfaced during the ongoing documentation
cleanup lives at
[`gigantic_project-COPYME/ai/ai_FYIs/gigantic_conventions.md`](gigantic_project-COPYME/ai/ai_FYIs/gigantic_conventions.md).*
