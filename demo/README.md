# GIGANTIC Demo

## Demo Species

This demo uses 3 species spanning 2 major clades plus an outgroup:

| Species | Common Name | Clade |
|---------|-------------|-------|
| *Homo sapiens* | Human | Vertebrata |
| *Aplysia californica* | California sea hare | Mollusca |
| *Octopus bimaculoides* | California two-spot octopus | Mollusca |

## What the Demo Covers

The demo walks through the complete GIGANTIC pipeline with a small dataset:

1. **databases** - Set up proteome databases for 3 species
2. **phylonames** - Generate phylonames for the demo species
3. **orthogroups** - Identify ortholog groups
4. **trees_species** - Generate all 3 possible tree topologies
5. **origins_conservation_loss** - Analyze evolutionary dynamics across topologies

## Running the Demo

```bash
cd demo
bash run_demo.sh
```

## Expected Runtime

The demo should complete in approximately 10-30 minutes depending on available compute resources.

## Validating Results

Compare your outputs against the reference files in `expected_outputs/` to verify correct installation and execution.
