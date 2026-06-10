# AI: Claude Code | Opus 4.8 | 2026 June 03 | Purpose: For structure_001, sum OCL block-states (O, P, L) along the full path from Metazoa to each of the 5 clades (depth-matched), with per-block breakdown
# Human: Eric Edsinger
#
# NOTE: clades share backbone blocks, so deeper clades' path sums ACCUMULATE the shared upstream
# losses (not independent). O and L sum cleanly (each event once); P double-counts features
# conserved across consecutive blocks. A not computed by OCL; per-block X unavailable.

from pathlib import Path

PROJECT_ROOT = Path( __file__ ).resolve().parents[ 3 ]
OCL = PROJECT_ROOT / 'subprojects/ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/workflow-RUN_1-ocl_analysis/OUTPUT_pipeline'
structure = 'structure_001'

clades = [ ( 'Ctenophora', 'C086_Ctenophora' ), ( 'Porifera', 'C090_Porifera' ),
           ( 'Placozoa', 'C095_Placozoa' ), ( 'Cnidaria', 'C102_Cnidaria' ), ( 'Bilateria', 'C103_Bilateria' ) ]

# load parent map + block states
children___parents = {}
pc = OCL / structure / '1-output' / f'1_ai-{structure}_parent_child_table.tsv'
with open( pc ) as f:
    for line in f:
        p = line.rstrip( '\n' ).split( '\t' )
        if len( p ) < 3 or 'Parent' in p[ 1 ] or p[ 1 ] == p[ 2 ]:
            continue
        children___parents[ p[ 2 ] ] = p[ 1 ]

block_PL = {}
with open( OCL / structure / '3-output' / f'3_ai-{structure}_conservation_loss-per_block.tsv' ) as f:
    f.readline()
    for line in f:
        p = line.rstrip( '\n' ).split( '\t' )
        block_PL[ ( p[ 0 ], p[ 1 ] ) ] = ( int( p[ 3 ] ), int( p[ 4 ] ) )

block_O = {}
with open( OCL / structure / '2-output' / f'2_ai-{structure}_origins_summary-orthogroups_per_clade.tsv' ) as f:
    f.readline()
    for line in f:
        p = line.rstrip( '\n' ).split( '\t' )
        block_O[ p[ 0 ].rsplit( '-', 1 )[ 0 ] ] = int( p[ 1 ] )

def path_blocks( target, stop='C082_Metazoa' ):
    chain, node = [], target
    while node != stop and node in children___parents:
        parent = children___parents[ node ]
        chain.append( ( parent, node ) )
        node = parent
    chain.reverse()
    return chain

print( f"{structure}: depth-matched path sums (Metazoa -> clade)\n" )
print( f"{'Clade':12s} {'blocks':>6s} {'O_sum':>6s} {'P_sum':>7s} {'L_sum':>6s}" )
detail = []
for name, cid in clades:
    blocks = path_blocks( cid )
    O = P = L = 0
    lines = []
    for ( parent, child ) in blocks:
        pp, ll = block_PL.get( ( parent, child ), ( 0, 0 ) )
        oo = block_O.get( f'{parent}::{child}', 0 )
        O += oo; P += pp; L += ll
        lines.append( f"      {parent} -> {child}:  O={oo}  P={pp}  L={ll}" )
    print( f"{name:12s} {len( blocks ):6d} {O:6d} {P:7d} {L:6d}" )
    detail.append( ( name, lines ) )

print( "\nPer-block breakdown (shared backbone blocks recur across deeper clades):" )
for name, lines in detail:
    print( f"  {name}:" )
    for l in lines:
        print( l )
