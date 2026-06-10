# AI: Claude Code | Opus 4.8 | 2026 June 03 | Purpose: From the clade presence table, compute per-clade ancestral retained/lost and the node-local basal score (features uniquely retained by one clade = lost across the other four)
# Human: Eric Edsinger
#
# For the DEEPEST node (Metazoa -> one basal clade + the other four):
#   uniquely_retained(C) = ancestral features present in clade C and ABSENT in all other 4 clades.
#   Each such feature is one ancestral character the other four all lost = a candidate synapomorphy
#   that the other four form a group (i.e., C branched off first). Highest = node-local basal candidate.
# Also reports each clade's own ancestral LOSS count (sanity-check vs the ~1700 ctenophore / ~3500 sibling
# figures), with species counts for the size context (small clade + high unique-retention = strong).

from pathlib import Path

SANDBOX_DIR = Path( __file__ ).resolve().parent
input_table = SANDBOX_DIR / '1_ai-clade_presence_table.tsv'

clades = [ 'Ctenophora', 'Porifera', 'Placozoa', 'Cnidaria', 'Bilateria' ]
# column index in the table: 0=OG, 1=Outgroup, 2..6 = the 5 clades, 7=Total
clade_column = { 'Ctenophora': 2, 'Porifera': 3, 'Placozoa': 4, 'Cnidaria': 5, 'Bilateria': 6 }
species_counts = { 'Ctenophora': 5, 'Porifera': 7, 'Placozoa': 4, 'Cnidaria': 5, 'Bilateria': 35 }

ancestral_retained = { c: 0 for c in clades }   # outgroup>0 and clade>0
ancestral_lost = { c: 0 for c in clades }        # outgroup>0 and clade==0
uniquely_retained = { c: 0 for c in clades }     # outgroup>0, clade>0, all other 4 ==0

with open( input_table ) as input_file:
    input_file.readline()  # header
    for line in input_file:
        parts = line.rstrip( '\n' ).split( '\t' )
        outgroup = int( parts[ 1 ] )
        if outgroup == 0:
            continue  # only ancestral (outgroup-present) features
        clade_present = { c: int( parts[ clade_column[ c ] ] ) > 0 for c in clades }
        clades_present_total = sum( 1 for c in clades if clade_present[ c ] )
        for c in clades:
            if clade_present[ c ]:
                ancestral_retained[ c ] += 1
                if clades_present_total == 1:   # only this clade present -> the other 4 lost it
                    uniquely_retained[ c ] += 1
            else:
                ancestral_lost[ c ] += 1

print( "Per-clade ancestral-feature accounting (ancestral = present in >=1 outgroup species):\n" )
print( f"{'Clade':12s} {'species':>7s} {'retained':>9s} {'lost':>7s} {'UNIQUELY_retained':>18s}" )
print( f"{'':12s} {'':>7s} {'(has it)':>9s} {'(lost)':>7s} {'(only this clade)':>18s}" )
for c in clades:
    print( f"{c:12s} {species_counts[ c ]:7d} {ancestral_retained[ c ]:9d} {ancestral_lost[ c ]:7d} {uniquely_retained[ c ]:18d}" )

print( "\nNode-local BASAL score = UNIQUELY_retained (higher = stronger basal candidate at the deepest split):" )
for c in sorted( clades, key = lambda x: uniquely_retained[ x ], reverse = True ):
    per_species = uniquely_retained[ c ] / species_counts[ c ]
    print( f"  {c:12s} unique_retained={uniquely_retained[ c ]:5d}   (per species: {per_species:6.1f}; clade has {species_counts[ c ]} species)" )

print( "\nSanity check vs prior observation (clade's own ancestral LOSS count):" )
for c in sorted( clades, key = lambda x: ancestral_lost[ x ] ):
    print( f"  {c:12s} lost {ancestral_lost[ c ]:5d} ancestral features  (retains {ancestral_retained[ c ]})" )
