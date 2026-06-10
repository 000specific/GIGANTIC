# AI: Claude Code | Opus 4.8 | 2026 June 03 | Purpose: For each high-confidence clade swapped to the basal position (direct child of C082_Metazoa), report OCL block-states on the Metazoa->basal-clade block and the Metazoa->rest block, plus whole-tree state totals per structure
# Human: Eric Edsinger
#
# OCL block-states reported: O (origins, 2-output), P (conserved, 3-output per_block),
#   L (lost, 3-output per_block). Whole-tree totals (P, L, X) from the 3-output summary.
# NOTE: A (inherited absence, pre-origin) is NOT computed by OCL (explicitly "implicit/ignored"),
#   and per-block X is not in OCL's per_block file (only the whole-tree X total is available).

from pathlib import Path

PROJECT_ROOT = Path( __file__ ).resolve().parents[ 3 ]
OCL = PROJECT_ROOT / 'subprojects/ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/workflow-RUN_1-ocl_analysis/OUTPUT_pipeline'
named_clades = { 'C086_Ctenophora', 'C090_Porifera', 'C095_Placozoa', 'C102_Cnidaria', 'C103_Bilateria' }

def parse_summary_totals( path ):
    P = L = X = None
    with open( path ) as input_file:
        for line in input_file:
            if 'Conservation events' in line: P = int( line.rsplit( ':', 1 )[ 1 ] )
            elif 'Loss events' in line:        L = int( line.rsplit( ':', 1 )[ 1 ] )
            elif 'Continued absence events' in line: X = int( line.rsplit( ':', 1 )[ 1 ] )
    return P, L, X

results = {}  # basal clade -> list of dicts
for n in range( 1, 106 ):
    s = f"structure_{n:03d}"
    per_block = OCL / s / '3-output' / f'3_ai-{s}_conservation_loss-per_block.tsv'
    origins   = OCL / s / '2-output' / f'2_ai-{s}_origins_summary-orthogroups_per_clade.tsv'
    summary   = OCL / s / '3-output' / f'3_ai-{s}_conservation_loss-summary.tsv'
    if not ( per_block.exists() and origins.exists() and summary.exists() ):
        continue

    metazoa_children = []
    with open( per_block ) as f:
        f.readline()
        for line in f:
            p = line.rstrip( '\n' ).split( '\t' )
            if p[ 0 ] == 'C082_Metazoa':
                metazoa_children.append( ( p[ 1 ], int( p[ 2 ] ), int( p[ 3 ] ), int( p[ 4 ] ) ) )  # child, Inherited, P, L

    blocks___O = {}
    with open( origins ) as f:
        f.readline()
        for line in f:
            p = line.rstrip( '\n' ).split( '\t' )
            blocks___O[ p[ 0 ].rsplit( '-', 1 )[ 0 ] ] = int( p[ 1 ] )

    if len( metazoa_children ) != 2:
        continue
    ( ca, ia, pa, la ), ( cb, ib, pb, lb ) = metazoa_children
    if ( ca in named_clades ) == ( cb in named_clades ):
        continue
    if ca in named_clades:
        basal, p_basal, l_basal, rest, p_rest, l_rest = ca, pa, la, cb, pb, lb
    else:
        basal, p_basal, l_basal, rest, p_rest, l_rest = cb, pb, lb, ca, pa, la
    o_basal = blocks___O.get( f'C082_Metazoa::{basal}' )
    o_rest  = blocks___O.get( f'C082_Metazoa::{rest}' )
    tot_P, tot_L, tot_X = parse_summary_totals( summary )

    results.setdefault( basal, [] ).append( {
        's': s, 'o_basal': o_basal, 'p_basal': p_basal, 'l_basal': l_basal,
        'o_rest': o_rest, 'p_rest': p_rest, 'l_rest': l_rest,
        'tot_P': tot_P, 'tot_L': tot_L, 'tot_X': tot_X } )

order = [ 'C086_Ctenophora', 'C090_Porifera', 'C095_Placozoa', 'C102_Cnidaria', 'C103_Bilateria' ]
print( "BLOCK-STATES AT THE BASAL SPLIT (Metazoa -> basal clade), per swap.  A = not computed by OCL.\n" )
print( f"{'BASAL clade':16s} {'#str':>4s} | {'O_in':>6s} {'P_in':>6s} {'L_in':>6s} | {'O_rest':>6s} {'P_rest':>7s} {'L_rest':>6s} | whole-tree mean(P / L / X)" )
for clade in order:
    if clade not in results:
        print( f"{clade:16s}   0   (never basal/pectinate)" ); continue
    rows = results[ clade ]
    r = rows[ 0 ]
    mP = sum( x['tot_P'] for x in rows ) / len( rows )
    mL = sum( x['tot_L'] for x in rows ) / len( rows )
    mX = sum( x['tot_X'] for x in rows ) / len( rows )
    name = clade.split('_',1)[1]
    print( f"{name:16s} {len(rows):4d} | {r['o_basal']:6d} {r['p_basal']:6d} {r['l_basal']:6d} | {r['o_rest']:6d} {r['p_rest']:7d} {r['l_rest']:6d} | {mP:10.0f} {mL:8.0f} {mX:9.0f}" )

print( "\nLegend: O_in/P_in/L_in = origins/conserved/lost on the Metazoa->basal-clade block (constant per basal clade, species-content determined)." )
print( "        O_rest/P_rest/L_rest = same on the Metazoa->(other four) block.  whole-tree = totals summed over all 139 blocks (mean over the structures with this basal clade)." )
