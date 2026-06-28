# GIGANTIC Server → Excel Conversion

Two ways to get GIGANTIC server tables as Excel (`.xlsx`) files, both using the
**same safety logic** so they can never disagree.

- **Server "EXCEL" button** (`/excel/...`) — click it in the browser next to any
  `.tsv` / `.csv` file. The server converts on the fly and sends you the `.xlsx`.
- **Standalone script** (`ai/download_and_convert_to_excel.py`) — download a whole
  directory of tables at once and convert them locally, deleting the downloaded
  TSVs and keeping only the Excel files. Ideal to run via Claude Code in Cursor.

Both are **pure standard-library Python** — no `pip install` needed anywhere.

---

## Why convert to Excel?

`.xlsx` is a zipped format, so the files are several times smaller than the raw
TSV (one real annogroup table: 28.8 MB TSV → 6.0 MB xlsx). The ratio depends on
the table; tables with lots of repeated values shrink the most.

## The most important part: this is also a data-integrity safeguard

Excel has hard limits that **silently destroy data** when you open a big TSV
directly in Excel:

- **32,767 characters per cell** — Excel keeps the first 32,767 and drops the rest.
- **1,048,576 rows** and **16,384 columns** per sheet — extra rows/columns vanish.

Several GIGANTIC tables cross these limits. For example, the composite-clades
"member sequence identifiers" columns contain comma-delimited lists that reach
**hundreds of thousands — even ~1.6 million — characters in a single cell**.
Opening those in Excel keeps a tiny fraction and silently throws the rest away.

**Both tools here refuse to produce a lossy Excel file.** If a table cannot be
stored in `.xlsx` without losing or corrupting data, the conversion is
**refused** and you are told exactly which file / column / cell / length caused
it. The original TSV is the complete record — use it for those tables.

### Two deliberate design choices

1. **Every cell is written as text.** This prevents Excel's other silent
   corruption: turning gene names like `SEPT2` / `MARCH1` into dates and turning
   e-values / identifiers into rounded numbers or scientific notation.
   *Trade-off:* genuinely numeric columns are stored as text, so they won't
   auto-sort numerically in Excel. (This can be revisited if needed.)
2. **Refuse + report, never truncate.** No partial/truncated workbook is ever
   produced. (Chosen by Eric, 2026-06-28.)

---

## Using the server "EXCEL" button

Browse to any directory on the server (e.g. `http://localhost:9456/annogroups/...`).
Each `.tsv` / `.csv` row shows an **EXCEL** link next to **DOWNLOAD**. Click EXCEL
to get the `.xlsx`. If the table can't be converted losslessly, you'll get a
clear "EXCEL — REFUSED" page listing the problem cells and a link to the TSV.

> **Activation note:** the EXCEL button only appears after the running server is
> restarted to pick up the new code (see `Login-node-server-GUIDE.md`). The
> standalone script below works immediately and needs no restart.

## Using the standalone script

```bash
# One directory of tables (the common case):
python3 ai/download_and_convert_to_excel.py \
    http://localhost:9456/annogroups/BLOCK_build_annogroups/workflow-RUN_6-build_annogroups/2-output/pfam/

# Choose an output folder and include subdirectories:
python3 ai/download_and_convert_to_excel.py URL --output-dir ~/Desktop/pfam_excel --recursive

# A single table also works (directory page, file page, or /download/ link).
```

Options: `--output-dir DIR` (default: current directory), `--recursive` (walk
subdirectories, mirroring the folder structure), `--keep-tsv` (don't delete the
downloaded TSVs), `--quiet` (summary only).

Behaviour: downloads each `.tsv` / `.csv`, converts it, and on success deletes
the downloaded TSV — leaving only the `.xlsx`. On a refusal it **keeps the TSV**
(so no data is lost), reports why, and exits non-zero.

### Example: asking Claude Code (Cursor) to do it

> Please download and convert to Excel the files located at:
> http://localhost:9456/annogroups/BLOCK_build_annogroups/workflow-RUN_6-build_annogroups/2-output/pfam/

Claude runs the standalone script, saves the `.xlsx` files, deletes the
downloads, and reports any tables that were too large for Excel.

---

## Files

| File | Role |
|------|------|
| `ai/tsv_to_xlsx.py` | Shared converter + validation (stdlib only). Also a CLI: `python3 ai/tsv_to_xlsx.py INPUT.tsv -o OUT.xlsx` |
| `ai/download_and_convert_to_excel.py` | Standalone downloader/converter (imports `tsv_to_xlsx`) |
| `ai/gigantic_server.py` | Server; serves the `/excel/...` endpoint and EXCEL links |
