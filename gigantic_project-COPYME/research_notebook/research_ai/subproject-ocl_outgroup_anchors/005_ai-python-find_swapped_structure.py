# AI: Claude Code | Opus 4.8 | 2026 June 03 | Purpose: Build the real 5-clade induced topology for all 105 OCL structures from their parent-child tables, and find the structure identical to structure_001 but with Ctenophora and Porifera positions swapped
# Human: Eric Edsinger
#
# Uses the authoritative per-structure parent_child_table (consistent with OCL + the clade-ID
# newick). The 2-output topology_permutations file is mislabeled relative to the final structures
# and is NOT used.

from pathlib import Path

PROJECT_ROOT = Path( __file__ ).resolve().parents[ 3 ]
OCL = PROJECT_ROOT / 'subprojects/ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/workflow-RUN_1-ocl_analysis/OUTPUT_pipeline'
target_clade_names = { 'Ctenophora', 'Porifera', 'Placozoa', 'Cnidaria', 'Bilateria' }

def name_part( clade_id_name ):
    return clade_id_name.split( '_', 1 )[ 1 ] if '_' in clade_id_name else clade_id_name

def induced_topology( parents___children, node ):
    """Canonical Newick of the 5-clade induced topology below Metazoa.
    Stop (leaf) when a node is one of the 5 target clades."""
    nm = name_part( node )
    if nm in target_clade_names:
        return nm
    children = parents___children.get( node, [] )
    sub = sorted( induced_topology( parents___children, c ) for c in children )
    if len( sub ) == 1:
        return sub[ 0 ]
    return '(' + ','.join( sub ) + ')'

def structure_topology( structure ):
    pc = OCL / structure / '1-output' / f'1_ai-{structure}_parent_child_table.tsv'
    if not pc.exists():
        return None
    parents___children = {}
    with open( pc ) as f:
        for line in f:
            line = line.rstrip( '\n' )
            parts = line.split( '\t' )
            if len( parts ) < 3 or parts[ 1 ] == 'Parent_Clade_ID_Name' or 'Parent' in parts[ 1 ]:
                continue
            parent, child = parts[ 1 ], parts[ 2 ]
            if parent == child:
                continue
            parents___children.setdefault( parent, [] ).append( child )
    # find the Metazoa node
    metazoa = None
    for node in list( parents___children.keys() ) + [ c for cs in parents___children.values() for c in cs ]:
        if name_part( node ) == 'Metazoa':
            metazoa = node; break
    if metazoa is None:
        return None
    return induced_topology( parents___children, metazoa )

# canonical topology per structure
topo___structures = {}
structure___topo = {}
for n in range( 1, 106 ):
    s = f"structure_{n:03d}"
    t = structure_topology( s )
    if t is None:
        continue
    structure___topo[ s ] = t
    topo___structures.setdefault( t, [] ).append( s )

# structure_001 and the swapped target
t001 = structure___topo[ 'structure_001' ]
print( f"structure_001 real 5-clade topology:\n  {t001}\n" )

def swap_labels( topo ):
    # swap Ctenophora <-> Porifera, then re-canonicalize by re-parsing is overkill;
    # since canonical form sorts alphabetically, swapping names then re-sorting is needed.
    # Easiest: rebuild from a placeholder swap then canonical-sort via a tiny parser.
    return topo.replace( 'Ctenophora', '@CT@' ).replace( 'Porifera', 'Ctenophora' ).replace( '@CT@', 'Porifera' )

def canonicalize( newick ):
    # parse a clade-only newick of the 5 names and re-emit canonical (alphabetical-sorted) form
    pos = 0
    def parse():
        nonlocal pos
        if newick[ pos ] == '(':
            pos += 1
            kids = []
            while True:
                kids.append( parse() )
                if newick[ pos ] == ',':
                    pos += 1
                elif newick[ pos ] == ')':
                    pos += 1
                    break
            return '(' + ','.join( sorted( kids ) ) + ')'
        else:
            start = pos
            while pos < len( newick ) and newick[ pos ] not in '(),':
                pos += 1
            return newick[ start:pos ]
    return parse()

swapped = canonicalize( swap_labels( t001 ) )
print( f"target (Ctenophora<->Porifera swapped, canonical):\n  {swapped}\n" )

matches = topo___structures.get( swapped, [] )
print( f"Structures matching the swapped topology: {matches if matches else 'NONE FOUND'}" )
for s in matches:
    print( f"  {s}: {structure___topo[ s ]}" )

# sanity: show how many distinct topologies and that 001 is unique
print( f"\n(total structures parsed: {len( structure___topo )}; distinct 5-clade topologies: {len( topo___structures )})" )
print( f"structures sharing 001's topology: {topo___structures.get( t001 )}" )
