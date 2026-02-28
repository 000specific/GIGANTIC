#!/bin/bash
# GIGANTIC BLOCK 3 - Script 002: Replace Special Characters
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 03:50 | Purpose: Clean sequences for MAFFT alignment
# Human: Eric Edsinger

HOMOLOG_ID=$1

if [ -z "$HOMOLOG_ID" ]; then
    echo "Usage: $0 HOMOLOG_ID"
    echo "Example: $0 AGS-species67_T1-species37-innexin_pannexin"
    exit 1
fi

# Replace internal dashes (keep those in headers)
sed 's/^-//g' "output/1-${HOMOLOG_ID}.aa" | sed 's/-$//g' > "output/2-${HOMOLOG_ID}.aa"

# Note: U (pyrrolysine/selenocysteine) replacement disabled by default
# Uncomment if needed:
# sed 's/U/X/g' "output/2-${HOMOLOG_ID}.aa" > "output/2-${HOMOLOG_ID}-temp.aa"
# mv "output/2-${HOMOLOG_ID}-temp.aa" "output/2-${HOMOLOG_ID}.aa"

echo "Cleaned sequences: output/2-${HOMOLOG_ID}.aa"

