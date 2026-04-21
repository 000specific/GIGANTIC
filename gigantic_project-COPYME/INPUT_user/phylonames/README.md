# INPUT_user/phylonames/

User-provided custom taxonomic override data for the GIGANTIC phylonames subproject.

## Contents

- `user_phylonames.tsv` — Tab-separated mappings from `genus_species` to custom `phyloname`
  (format: `Kingdom_Phylum_Class_Order_Family_Genus_species`). Used by
  phylonames STEP_2-apply_user_phylonames to override NCBI-generated phylonames for
  species with NOTINNCBI placeholders, numbered clades, or user-preferred taxonomic
  assignments.

This is the canonical project-level home for user_phylonames.tsv. The STEP_2 workflow
copies from here into its workflow-local INPUT_user/ at run time.
