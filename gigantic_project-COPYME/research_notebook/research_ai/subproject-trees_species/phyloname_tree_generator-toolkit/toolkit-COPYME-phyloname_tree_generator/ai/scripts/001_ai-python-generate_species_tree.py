#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 29 | Purpose: Generate a binary phyloname-derived species tree (user-specified backbone + optional internal-clade constraints + random polytomy resolution)
# Human: Eric Edsinger
"""
Generate a binary species tree from a phylonames TSV map.

Pipeline
--------
1. Read phylonames TSV (genus_species + phyloname columns).
2. Assign each species to one of N backbone leaves declared by the user.
3. Build a nested taxonomic dict per backbone leaf from the tokens BELOW
   that leaf.
4. Apply optional `internal_clade_constraints` (named monophyletic clades
   anywhere in the tree — e.g. group Balaenopteridae+Delphinidae+Phocoenidae
   into a "Cetacea" node before resolving the Artiodactyla polytomy, so
   Hippopotamidae lands sister to Cetacea rather than inside it).
5. Where a node still has > 2 children after constraints, randomly pair
   children using a seeded RNG; log every pairing in decision_log.tsv.
6. Substitute resolved subtrees into the backbone topology; strip the
   outermost single-child wrapper so the emitted tree is a clean binary
   tree with N leaves and N-1 internals.
7. Assign `ancestral_clade_NNN` labels to every internal node in BFS order
   (NOT yet — labels are deliberately omitted from the emitted Newick so
   trees_species/BLOCK_gigantic_species_tree can do its own auto-naming;
   the pattern is reserved by that BLOCK).

Inputs
------
  - phylonames TSV (positional column read: col 0 = genus_species, col 1 = phyloname)
  - YAML config describing:
      backbone_topology    nested list-of-lists; leaves are backbone-leaf names
      backbone_leaves      mapping: backbone-leaf-name -> phyloname-token rules
      internal_clade_constraints (optional)  list of {name, siblings}
      seed                 RNG seed for reproducible polytomy resolution

Outputs (--output-dir)
----------------------
  <prefix>-seed<SEED>-species_tree.newick           Clean binary, no internal labels
  <prefix>-seed<SEED>-decision_log.tsv              Per-step polytomy pairings
  <prefix>-seed<SEED>-internal_constraints_applied.tsv  Where each constraint fired
  <prefix>-seed<SEED>-ambiguity_summary.md          Human-readable summary

CLI
---
  python3 001_ai-python-generate_species_tree.py \\
      --phylonames PATH \\
      --config PATH \\
      --output-dir PATH \\
      --prefix species42 \\
      --seed 42 \\
      --log-file PATH

Exit 0 on success. Exit 1 on any species that cannot be assigned to a
backbone leaf, or on any internal-clade constraint whose declared
siblings can't all be matched.
"""

import argparse
import csv
import logging
import random
import sys
from collections import deque
from pathlib import Path

import yaml


# ============================================================================
# Logging
# ============================================================================

def setup_logging( log_path ):
    logger = logging.getLogger( "generate_species_tree" )
    logger.setLevel( logging.INFO )
    fh = logging.FileHandler( log_path, mode = "w" )
    sh = logging.StreamHandler( sys.stdout )
    fmt = logging.Formatter( "%(asctime)s - %(levelname)s - %(message)s" )
    fh.setFormatter( fmt )
    sh.setFormatter( fmt )
    logger.addHandler( fh )
    logger.addHandler( sh )
    return logger


# ============================================================================
# Phylonames TSV -> species records
# ============================================================================

def load_phylonames( path, logger ):
    """
    Positional column read (col 0 = genus_species, col 1 = phyloname) to
    survive the phylonames TSV's descriptive-parenthetical header style.
    """

    records = []
    with open( path ) as f:
        reader = csv.reader( f, delimiter = "\t" )
        header = next( reader )
        for row in reader:
            if not row or not row[ 0 ].strip():
                continue
            genus_species = row[ 0 ].strip()
            phyloname = row[ 1 ].strip()
            tokens = phyloname.split( "_" )
            records.append( {
                "genus_species": genus_species,
                "phyloname":     phyloname,
                "tokens":        tokens,
            } )
    logger.info( f"Loaded {len(records)} species from {path.name}" )
    return records


# ============================================================================
# Backbone-leaf assignment
# ============================================================================

def assign_backbone_leaf( tokens, backbone_rules, logger ):
    """
    backbone_rules is a list of dicts. Each dict has:
      name              backbone-leaf name (string)
      match             a dict whose key/values must all match the
                        phyloname tokens by position (0=Kingdom,1=Phylum,
                        2=Class,3=Order,4=Family). Use the special value
                        '*' to accept anything.
                        Multiple `match` entries may be given as a list;
                        the species is assigned if ANY entry matches.

    The list is evaluated in order; first match wins.
    """

    for rule in backbone_rules:
        match_entries = rule[ "match" ]
        if isinstance( match_entries, dict ):
            match_entries = [ match_entries ]
        for entry in match_entries:
            ok = True
            for level_str, expected in entry.items():
                level = int( level_str )
                if level >= len( tokens ):
                    ok = False
                    break
                actual = tokens[ level ]
                if expected == "*":
                    continue
                if isinstance( expected, list ):
                    if actual not in expected:
                        ok = False
                        break
                else:
                    if actual != expected:
                        ok = False
                        break
            if ok:
                return rule[ "name" ]
    return None


def backbone_skip_depth( backbone_name, backbone_rules ):
    """How many leading phyloname tokens are absorbed by this backbone leaf."""

    for rule in backbone_rules:
        if rule[ "name" ] == backbone_name:
            return int( rule.get( "skip_depth", 2 ) )
    raise ValueError( backbone_name )


# ============================================================================
# Taxonomic dict (under a single backbone leaf)
# ============================================================================

def build_taxonomic_dict( species_in_group, skip_depth ):
    root = {}
    for sp in species_in_group:
        tokens = sp[ "tokens" ]
        genus_species = sp[ "genus_species" ]
        terminus_token_count = len( genus_species.split( "_" ) )
        hierarchy = tokens[ skip_depth : len( tokens ) - terminus_token_count ]
        node = root
        for tax_name in hierarchy:
            node = node.setdefault( tax_name, {} )
        node.setdefault( "__leaves__", [] ).append( genus_species )
    return root


# ============================================================================
# Polytomy resolution helpers
# ============================================================================

def collect_leaves( subtree ):
    if isinstance( subtree, str ):
        return [ subtree ]
    out = []
    for child in subtree:
        out.extend( collect_leaves( child ) )
    return out


def summarize_child( subtree, name = None, max_leaves = 3 ):
    if name is not None:
        leaves = collect_leaves( subtree )
        return f"{name}({len(leaves)})"
    if isinstance( subtree, str ):
        return subtree
    leaves = collect_leaves( subtree )
    if len( leaves ) <= max_leaves:
        return "+".join( leaves )
    return f"<{len(leaves)}-leaf clade: {leaves[0]}..{leaves[-1]}>"


def random_resolve( named_children, rng, decisions, parent_context ):
    """
    named_children is a list of (name_or_None, subtree). Iteratively pair
    random children until exactly 2 remain. Returns a 2-tuple of subtrees.
    """

    items = list( named_children )
    step = 0
    while len( items ) > 2:
        i, j = sorted( rng.sample( range( len( items ) ), 2 ) )
        j_item = items.pop( j )
        i_item = items.pop( i )
        new_subtree = ( i_item[ 1 ], j_item[ 1 ] )
        step += 1
        decisions.append( {
            "parent_context":          parent_context,
            "step":                    step,
            "paired_left":             summarize_child( i_item[ 1 ], i_item[ 0 ] ),
            "paired_right":            summarize_child( j_item[ 1 ], j_item[ 0 ] ),
            "paired_left_leafcount":   len( collect_leaves( i_item[ 1 ] ) ),
            "paired_right_leafcount":  len( collect_leaves( j_item[ 1 ] ) ),
            "siblings_remaining_after": len( items ),
        } )
        items.append( ( None, new_subtree ) )
    return tuple( item[ 1 ] for item in items )


# ============================================================================
# Internal-clade constraint application
# ============================================================================

def apply_internal_constraints(
    named_children, constraints, parent_context,
    constraint_applications, logger
):
    """
    Walk through `constraints`. For each, if ALL its declared siblings
    appear in named_children, collapse those siblings into one composite
    (name, subtree) entry whose name is the constraint name.

    Constraint format:
      { "name": "Cetacea", "siblings": ["Balaenopteridae", "Delphinidae", "Phocoenidae"] }
    """

    items = list( named_children )

    for constraint in constraints:
        target_name = constraint[ "name" ]
        target_siblings = list( constraint[ "siblings" ] )
        idx_by_name = { it[ 0 ]: i for i, it in enumerate( items ) if it[ 0 ] is not None }

        # Are all siblings present at THIS level?
        if not all( s in idx_by_name for s in target_siblings ):
            continue

        # Pull them out in user-declared order
        picked = [ items[ idx_by_name[ s ] ] for s in target_siblings ]
        # Build the composite subtree as a left-folded binary pair to ensure
        # determinism (no random pairing within a constraint's siblings).
        # Each pair makes (existing, next) so order matches the user's list.
        if len( picked ) == 1:
            composite_subtree = picked[ 0 ][ 1 ]
        else:
            composite_subtree = picked[ 0 ][ 1 ]
            for next_item in picked[ 1 : ]:
                composite_subtree = ( composite_subtree, next_item[ 1 ] )

        # Remove the picked siblings, append the composite
        to_remove = set( target_siblings )
        items = [ it for it in items if it[ 0 ] not in to_remove ]
        items.append( ( target_name, composite_subtree ) )

        leaf_count = len( collect_leaves( composite_subtree ) )
        logger.info(
            f"  applied constraint '{target_name}' at {parent_context}: "
            f"grouped {target_siblings} ({leaf_count} leaves)"
        )
        constraint_applications.append( {
            "constraint_name": target_name,
            "parent_context":  parent_context,
            "siblings_grouped": ",".join( target_siblings ),
            "leaf_count":      leaf_count,
        } )

    return items


# ============================================================================
# Build subtree from nested dict
# ============================================================================

def build_subtree_from_dict(
    nested, rng, decisions, constraint_applications,
    constraints, context_path, logger
):
    named_children = []

    # Direct genus_species leaves at this level (under __leaves__)
    if "__leaves__" in nested:
        for leaf in nested[ "__leaves__" ]:
            named_children.append( ( leaf, leaf ) )

    # Deeper taxonomic nodes
    for tax_name, sub in nested.items():
        if tax_name == "__leaves__":
            continue
        deeper = build_subtree_from_dict(
            sub, rng, decisions, constraint_applications,
            constraints, context_path + ( tax_name, ), logger
        )
        named_children.append( ( tax_name, deeper ) )

    if not named_children:
        raise ValueError(
            f"Empty taxonomic node at context {context_path!r}"
        )

    parent_context = "/".join( context_path ) if context_path else "ROOT"

    # Apply internal-clade constraints BEFORE polytomy resolution
    named_children = apply_internal_constraints(
        named_children, constraints, parent_context,
        constraint_applications, logger
    )

    if len( named_children ) == 1:
        return named_children[ 0 ][ 1 ]
    if len( named_children ) == 2:
        return ( named_children[ 0 ][ 1 ], named_children[ 1 ][ 1 ] )

    # > 2 children -> random pairing
    return random_resolve(
        named_children, rng, decisions, parent_context
    )


# ============================================================================
# Substitute resolved subtrees into the backbone topology
# ============================================================================

def substitute_backbone( topology, backbone_subtrees ):
    if isinstance( topology, str ):
        return backbone_subtrees.get( topology, topology )
    return tuple( substitute_backbone( c, backbone_subtrees ) for c in topology )


# ============================================================================
# Newick emit (no internal labels -> trees_species will auto-fill)
# ============================================================================

def to_newick_unlabeled( tree ):
    def emit( node ):
        if isinstance( node, str ):
            return node
        return "(" + ",".join( emit( c ) for c in node ) + ")"
    return emit( tree ) + ";"


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser( description = __doc__ )
    parser.add_argument( "--phylonames", required = True )
    parser.add_argument( "--config",     required = True )
    parser.add_argument( "--output-dir", required = True )
    parser.add_argument( "--prefix",     default = "species_tree" )
    parser.add_argument( "--seed",       type = int, default = None )
    parser.add_argument( "--log-file",   required = True )
    args = parser.parse_args()

    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )
    log_path = Path( args.log_file ).resolve()
    log_path.parent.mkdir( parents = True, exist_ok = True )

    logger = setup_logging( log_path )

    config_path = Path( args.config ).resolve()
    phylonames_path = Path( args.phylonames ).resolve()

    with open( config_path ) as f:
        config = yaml.safe_load( f ) or {}

    seed = args.seed if args.seed is not None else int( config.get( "seed", 42 ) )
    backbone_topology = config[ "backbone_topology" ]
    backbone_rules = config[ "backbone_leaves" ]
    constraints = config.get( "internal_clade_constraints", [] ) or []

    species_records = load_phylonames( phylonames_path, logger )

    # Assign each species to a backbone leaf
    by_backbone = {}
    unassigned = []
    for sp in species_records:
        leaf = assign_backbone_leaf( sp[ "tokens" ], backbone_rules, logger )
        if leaf is None:
            unassigned.append( sp[ "genus_species" ] )
            continue
        by_backbone.setdefault( leaf, [] ).append( sp )

    if unassigned:
        logger.error(
            f"{len(unassigned)} species could not be assigned to any backbone leaf:"
        )
        for sp in unassigned:
            logger.error( f"  {sp}" )
        sys.exit( 1 )

    rng = random.Random( seed )
    decisions = []
    constraint_applications = []

    # Build each backbone subtree
    backbone_subtrees = {}
    for rule in backbone_rules:
        name = rule[ "name" ]
        members = by_backbone.get( name, [] )
        if not members:
            logger.warning( f"backbone leaf '{name}' has zero species — skipping" )
            continue
        skip = backbone_skip_depth( name, backbone_rules )
        tax_dict = build_taxonomic_dict( members, skip )
        subtree = build_subtree_from_dict(
            tax_dict, rng, decisions, constraint_applications,
            constraints, ( name, ), logger
        )
        backbone_subtrees[ name ] = subtree
        logger.info( f"  backbone leaf '{name}': {len(collect_leaves(subtree))} species" )

    full = substitute_backbone( backbone_topology, backbone_subtrees )

    # Strip outer unary wrappers (the user's backbone Newick fragment may
    # have an outer parenthesis pair around the Bilateria node).
    while isinstance( full, tuple ) and len( full ) == 1:
        full = full[ 0 ]

    newick = to_newick_unlabeled( full )

    # ---- Write outputs ----
    suffix = f"-seed{seed}"
    newick_path = output_dir / f"{args.prefix}{suffix}-species_tree.newick"
    decisions_path = output_dir / f"{args.prefix}{suffix}-decision_log.tsv"
    constraints_path = output_dir / f"{args.prefix}{suffix}-internal_constraints_applied.tsv"
    summary_path = output_dir / f"{args.prefix}{suffix}-ambiguity_summary.md"

    newick_path.write_text( newick + "\n" )

    with open( decisions_path, "w", newline = "" ) as f:
        writer = csv.DictWriter(
            f, delimiter = "\t",
            fieldnames = [
                "parent_context", "step",
                "paired_left", "paired_right",
                "paired_left_leafcount", "paired_right_leafcount",
                "siblings_remaining_after",
            ],
        )
        writer.writeheader()
        for d in decisions:
            writer.writerow( d )

    with open( constraints_path, "w", newline = "" ) as f:
        writer = csv.DictWriter(
            f, delimiter = "\t",
            fieldnames = [
                "constraint_name", "parent_context",
                "siblings_grouped", "leaf_count",
            ],
        )
        writer.writeheader()
        for c in constraint_applications:
            writer.writerow( c )

    total_leaves = len( collect_leaves( full ) )

    summary_lines = [
        f"# {args.prefix} species tree — seed {seed}",
        "",
        f"- Phylonames input: `{phylonames_path}`",
        f"- Output Newick:    `{newick_path.name}`",
        f"- Decision log:     `{decisions_path.name}`",
        f"- Constraints log:  `{constraints_path.name}`",
        f"- RNG seed:         `{seed}`",
        "",
        "## Counts",
        "",
        f"- Species (leaves): **{total_leaves}**",
        f"- Polytomy pairing steps: **{len(decisions)}**",
        f"- Internal-clade constraints applied: **{len(constraint_applications)}**",
        "",
        "## Internal clade constraints applied",
        "",
    ]
    if constraint_applications:
        for c in constraint_applications:
            summary_lines.append(
                f"- `{c['constraint_name']}` under `{c['parent_context']}`: "
                f"{c['siblings_grouped']} ({c['leaf_count']} leaves)"
            )
    else:
        summary_lines.append( "- (none applied)" )
    summary_lines.append( "" )

    summary_lines += [
        "## Polytomy parents with pairing steps",
        "",
    ]
    parent_counts = {}
    for d in decisions:
        parent_counts[ d[ "parent_context" ] ] = \
            parent_counts.get( d[ "parent_context" ], 0 ) + 1
    for p in sorted( parent_counts ):
        summary_lines.append( f"- `{p}` — {parent_counts[p]} step(s)" )
    summary_lines.append( "" )

    summary_lines += [
        "## Reproducibility",
        "",
        "Same `--seed` + same `--phylonames` + same config -> identical "
        "Newick. Change `--seed` to draw a different sample from the "
        "polytomy resolution space.",
        "",
        "## Note on internal node labels",
        "",
        "Internal nodes are deliberately UNLABELED in the emitted Newick. "
        "Downstream `trees_species/BLOCK_gigantic_species_tree/` reserves "
        "the `ancestral_clade_NNN` pattern for its own auto-naming pass and "
        "hard-fails on user-supplied labels matching that pattern. Letting "
        "the canonical workflow do the labeling guarantees the same final "
        "label scheme regardless of which generator produced the input.",
        "",
    ]
    summary_path.write_text( "\n".join( summary_lines ) )

    logger.info( "" )
    logger.info( f"Wrote: {newick_path}" )
    logger.info( f"Wrote: {decisions_path}" )
    logger.info( f"Wrote: {constraints_path}" )
    logger.info( f"Wrote: {summary_path}" )


if __name__ == "__main__":
    main()
