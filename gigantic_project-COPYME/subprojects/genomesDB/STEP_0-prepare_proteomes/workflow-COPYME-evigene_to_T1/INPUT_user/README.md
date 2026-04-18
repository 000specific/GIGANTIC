# INPUT_user - EvidentialGene Okayset Files

**AI**: Claude Code | Opus 4.6 (1M context) | 2026 April 18
**Human**: Eric Edsinger

---

## What to Place Here

This directory is where you provide the path to your EvidentialGene okayset
okay.aa file. You do NOT need to copy the file into this directory -- just
provide the path in `START_HERE-user_config.yaml`.

However, if you prefer to keep a local copy, you may place the file here and
reference it with a relative path in the config.

---

## Expected Input File

### EvidentialGene okayset okay.aa

This is the main protein output from an EvidentialGene (evigene) transcriptome
assembly run. It is typically located in:

```
your_evigene_run/okayset/your_species.okay.aa
```

The file contains amino acid sequences in FASTA format with classification
information in the headers. The `evgclass=` tag indicates whether each
transcript is main, alt, or noclass:

```
>Mlig000002t1 type=protein; aalen=872,82%,complete; clen=3172; strand=+; offs=148-2766; evgclass=main,okay,match:Mlig000002t2,...
MDEFQSFVKELKDRPIGSAENQTYPWLFETLQAACERQHFPFGGEKKIGAKAQVMPLIKYALPNTGEG
...

>Mlig000002t2 type=protein; aalen=789,74%,complete; clen=3190; strand=+; offs=192-2561; evgclass=alt,okay,...
MDEFQSFVKELKDRPIGSAENQTYPWLFETLQAACERQHFPFGGEKKIGAKAQVMPLIKYALPNTGEG
...

>Mlig999999t1 type=protein; aalen=45,30%,partial; clen=450; strand=+; offs=1-138; evgclass=noclass,...
MXXXXXXXXXXX
...
```

### Key Fields in the Header

| Field | Example | Description |
|-------|---------|-------------|
| Sequence ID | `Mlig000002t1` | Transcript identifier |
| `aalen=` | `872,82%,complete` | Amino acid length, percent of CDS, completeness |
| `evgclass=` | `main,okay,...` | Classification: main, alt, or noclass |

---

## Configuration

After identifying your okay.aa file, edit `START_HERE-user_config.yaml` in
the workflow root directory:

```yaml
input:
  evigene_okay_aa: "/path/to/your/okayset/species.okay.aa"

species:
  name: "Genus_species"
```

Then run:
```bash
bash RUN-workflow.sh
```
