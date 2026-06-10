# AI: Claude Code | Opus 4.8 | 2026 June 03 | Purpose: Remove the clade-size confound from the node-local basal score by equalizing all 5 clades to N species, via EXACT expected value under N-species subsampling (hypergeometric), using the clade presence counts
# Human: Eric Edsinger
#
# Confound: raw uniquely-retained score favors species-rich clades (Bilateria) because
# "present in clade" and "absent in the other 4" both get easier/harder with clade size.
# Fix: give every clade the same effective sampling depth N. For a clade with k of its
# M species present in a feature, under a random N-subsample (no replacement):
#   P(present) = 1 - C(M-k, N)/C(M, N)      (>=1 of the N chosen has it)
#   P(absent)  = C(M-k, N)/C(M, N)
# Expected uniquely-retained(C) = sum over ancestral features of
#       P(C present) * product over the other clades of P(that clade absent).
# This is the exact mean over all equal-size subsamples (no Monte-Carlo noise).
# Outgroup is left at full depth (the "present in outgroup" anchor is a common filter for
# every clade, so it adds no between-clade bias; full depth = maximum ancestral coverage).

from math import comb
from pathlib import Path

SANDBOX_DIR = Path( __file__ ).resolve().parent
input_table = SANDBOX_DIR / '1_ai-clade_presence_table.tsv'

clades = [ 'Ctenophora', 'Porifera', 'Placozoa', 'Cnidaria', 'Bilateria' ]
clade_column = { 'Ctenophora': 2, 'Porifera': 3, 'Placozoa': 4, 'Cnidaria': 5, 'Bilateria': 6 }
clade_size = { 'Ctenophora': 5, 'Porifera': 7, 'Placozoa': 4, 'Cnidaria': 5, 'Bilateria': 35 }

def p_present( k, M, N ):
    if k <= 0:
        return 0.0
    if M - k < N:
        return 1.0
    return 1.0 - comb( M - k, N ) / comb( M, N )

# load ancestral features as per-clade present counts
features = []   # list of dict clade -> k present (only ancestral / outgroup-present features)
with open( input_table ) as input_file:
    input_file.readline()
    for line in input_file:
        parts = line.rstrip( '\n' ).split( '\t' )
        if int( parts[ 1 ] ) == 0:
            continue
        features.append( { c: int( parts[ clade_column[ c ] ] ) for c in clades } )

print( f"Ancestral features loaded: {len( features )}\n" )

for N in [ 4, 3, 2 ]:
    expected_unique = { c: 0.0 for c in clades }
    expected_retained = { c: 0.0 for c in clades }
    for feature in features:
        pp = { c: p_present( feature[ c ], clade_size[ c ], N ) for c in clades }
        pa = { c: 1.0 - pp[ c ] for c in clades }
        for c in clades:
            expected_retained[ c ] += pp[ c ]
            # present in c AND absent in every other clade
            product_absent_others = 1.0
            for d in clades:
                if d != c:
                    product_absent_others *= pa[ d ]
            expected_unique[ c ] += pp[ c ] * product_absent_others

    print( f"================ Equalized to N = {N} species per clade ================" )
    print( f"{'Clade':12s} {'exp_unique_retained':>20s} {'exp_retained':>13s}" )
    for c in sorted( clades, key = lambda x: expected_unique[ x ], reverse = True ):
        print( f"{c:12s} {expected_unique[ c ]:20.1f} {expected_retained[ c ]:13.1f}" )
    print()
