#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Convert a TSV/CSV table to .xlsx with strict refuse-and-report validation (no silent data loss)
# Human: Eric Edsinger

"""
tsv_to_xlsx — pure-stdlib TSV/CSV -> Excel (.xlsx) converter.

Design goals (research-integrity first):

  * STDLIB ONLY. No pandas, no openpyxl. An .xlsx file is just a ZIP of XML
    parts, so this module writes those parts directly. This keeps the GIGANTIC
    server dependency-free and lets the companion download script run on any
    machine with Python 3 and nothing else installed.

  * EVERY CELL IS WRITTEN AS TEXT (no type guessing). This is deliberate:
    when Excel *opens* a raw TSV it auto-converts values, turning gene names
    like SEPT2 / MARCH1 into dates and e-values / identifiers into rounded
    numbers or scientific notation. Writing each cell as an explicit inline
    string prevents all of that. (Trade-off: genuinely numeric columns will
    be stored as text, so they will not auto-sort numerically in Excel.)

  * REFUSE + REPORT on anything Excel cannot store losslessly. No partial or
    truncated workbook is ever produced. The caller is told exactly what and
    where the problem is. Refusal triggers:
        - sheet has more than 1,048,576 rows      (Excel row limit)
        - sheet has more than 16,384 columns      (Excel column limit)
        - any cell longer than 32,767 characters  (Excel cell limit)
        - any cell with XML-illegal control chars (cannot be stored)
        - file is not valid UTF-8 text            (cannot read safely)

Public API:
    validate_rows( rows ) -> list[ str ]                  # [] means OK
    rows_to_xlsx_bytes( rows ) -> bytes                   # raises ConversionRefused
    read_table( input_path, delimiter = None ) -> rows
    convert_path_to_bytes( input_path ) -> ( ok, report, xlsx_bytes_or_None )
    convert_file( input_path, output_path ) -> ( ok, report )

Command line:
    python3 tsv_to_xlsx.py INPUT.tsv [-o OUTPUT.xlsx]
"""

from pathlib import Path
import argparse
import csv
import io
import sys
import zipfile


# Excel hard limits (these are the format's limits, not arbitrary cutoffs).
MAX_ROWS = 1_048_576
MAX_COLUMNS = 16_384
MAX_CELL_CHARACTERS = 32_767

# How many individual problems to spell out before summarizing the rest.
MAX_REPORTED_PROBLEMS = 25

# Characters that are illegal in XML 1.0 text (so they cannot live in an .xlsx).
# Tab (0x09), newline (0x0A), and carriage return (0x0D) are legal and kept.
ILLEGAL_XML_ORDINALS = set( range( 0x00, 0x09 ) ) | { 0x0B, 0x0C } | set( range( 0x0E, 0x20 ) )

# Allow reading pathologically long cells so we can REPORT them clearly
# (exact cell + length) instead of crashing on csv's default field limit.
# Raise the limit as high as this platform allows.
_field_size_limit = sys.maxsize
while True:
    try:
        csv.field_size_limit( _field_size_limit )
        break
    except OverflowError:
        _field_size_limit = int( _field_size_limit / 10 )


class ConversionRefused( Exception ):
    """Raised when a table cannot be converted to .xlsx without data loss."""

    def __init__( self, problems ):
        self.problems = problems
        super().__init__( '; '.join( problems ) )


# ============================================================================
# Static .xlsx package parts (everything except the worksheet, which is built
# per table). These are the minimal set of OOXML parts Excel needs to open.
# ============================================================================

_CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    '</Types>'
)

_ROOT_RELATIONSHIPS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    '</Relationships>'
)

_WORKBOOK_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
    '</workbook>'
)

_WORKBOOK_RELATIONSHIPS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    '</Relationships>'
)


# ============================================================================
# Helpers
# ============================================================================

def _column_letter( column_index ):
    """Convert a 0-based column index to an Excel column label (0 -> 'A')."""
    label = ''
    column_index += 1
    while column_index:
        column_index, remainder = divmod( column_index - 1, 26 )
        label = chr( 65 + remainder ) + label
    return label


def _escape_xml_text( text ):
    """Escape the three characters that matter inside an XML text node."""
    return text.replace( '&', '&amp;' ).replace( '<', '&lt;' ).replace( '>', '&gt;' )


def _has_illegal_xml_characters( text ):
    return any( ord( character ) in ILLEGAL_XML_ORDINALS for character in text )


# ============================================================================
# Validation (the refuse-and-report contract)
# ============================================================================

def validate_rows( rows ):
    """Return a list of human-readable problems. An empty list means the table
    can be written to .xlsx with no loss or corruption."""
    problems = []

    row_count = len( rows )
    if row_count > MAX_ROWS:
        problems.append(
            f"Sheet has {row_count:,} rows, which exceeds Excel's limit of {MAX_ROWS:,} rows."
        )

    column_count = max( ( len( row ) for row in rows ), default = 0 )
    if column_count > MAX_COLUMNS:
        problems.append(
            f"Sheet has {column_count:,} columns, which exceeds Excel's limit of {MAX_COLUMNS:,} columns."
        )

    header = rows[ 0 ] if rows else []
    cell_problems = []
    for row_index, row in enumerate( rows ):
        for column_index, cell in enumerate( row ):
            cell_length = len( cell )
            cell_reference = _column_letter( column_index ) + str( row_index + 1 )
            column_label = header[ column_index ] if column_index < len( header ) else ''
            if cell_length > MAX_CELL_CHARACTERS:
                cell_problems.append(
                    f"Cell {cell_reference} (column '{column_label[ :60 ]}') has "
                    f"{cell_length:,} characters, which exceeds Excel's limit of "
                    f"{MAX_CELL_CHARACTERS:,} characters per cell."
                )
            elif _has_illegal_xml_characters( cell ):
                cell_problems.append(
                    f"Cell {cell_reference} (column '{column_label[ :60 ]}') contains "
                    f"control characters that Excel cannot store."
                )

    if len( cell_problems ) > MAX_REPORTED_PROBLEMS:
        hidden_count = len( cell_problems ) - MAX_REPORTED_PROBLEMS
        problems.extend( cell_problems[ :MAX_REPORTED_PROBLEMS ] )
        problems.append( f"...and {hidden_count:,} more cell(s) over the limit." )
    else:
        problems.extend( cell_problems )

    return problems


# ============================================================================
# Workbook construction
# ============================================================================

def _build_shared_strings_and_worksheet( rows ):
    """Build the sharedStrings.xml and sheet1.xml parts together.

    Each distinct cell value is stored ONCE in the shared-string table and
    referenced by index from the worksheet. This is what makes .xlsx far
    smaller than the source TSV for tables with repeated values (clade names,
    Pfam IDs, repeated identifiers). Values remain text, so nothing is coerced."""
    strings___indexes = {}
    ordered_strings = []
    total_string_cells = 0

    worksheet_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>',
    ]
    for row_index, row in enumerate( rows ):
        row_number = row_index + 1
        cells = []
        for column_index, cell in enumerate( row ):
            cell_reference = _column_letter( column_index ) + str( row_number )
            if cell == '':
                cells.append( f'<c r="{cell_reference}"/>' )
            else:
                index = strings___indexes.get( cell )
                if index is None:
                    index = len( ordered_strings )
                    strings___indexes[ cell ] = index
                    ordered_strings.append( cell )
                total_string_cells += 1
                cells.append( f'<c r="{cell_reference}" t="s"><v>{index}</v></c>' )
        worksheet_parts.append( f'<row r="{row_number}">' + ''.join( cells ) + '</row>' )
    worksheet_parts.append( '</sheetData></worksheet>' )

    shared_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{total_string_cells}" uniqueCount="{len( ordered_strings )}">',
    ]
    for value in ordered_strings:
        shared_parts.append( f'<si><t xml:space="preserve">{_escape_xml_text( value )}</t></si>' )
    shared_parts.append( '</sst>' )

    return ''.join( shared_parts ), ''.join( worksheet_parts )


def rows_to_xlsx_bytes( rows ):
    """Build a complete .xlsx workbook from rows. Raises ConversionRefused if
    the table would lose or corrupt data."""
    problems = validate_rows( rows )
    if problems:
        raise ConversionRefused( problems )

    shared_strings_xml, worksheet_xml = _build_shared_strings_and_worksheet( rows )
    buffer = io.BytesIO()
    with zipfile.ZipFile( buffer, 'w', zipfile.ZIP_DEFLATED ) as archive:
        archive.writestr( '[Content_Types].xml', _CONTENT_TYPES_XML )
        archive.writestr( '_rels/.rels', _ROOT_RELATIONSHIPS_XML )
        archive.writestr( 'xl/workbook.xml', _WORKBOOK_XML )
        archive.writestr( 'xl/_rels/workbook.xml.rels', _WORKBOOK_RELATIONSHIPS_XML )
        archive.writestr( 'xl/sharedStrings.xml', shared_strings_xml )
        archive.writestr( 'xl/worksheets/sheet1.xml', worksheet_xml )
    return buffer.getvalue()


# ============================================================================
# Reading and top-level conversion entry points
# ============================================================================

def read_table( input_path, delimiter = None ):
    """Read a TSV/CSV file into a list of rows (each row a list of strings).
    Delimiter defaults to comma for .csv and tab for everything else.
    Reads as strict UTF-8 so encoding problems surface instead of being
    silently replaced."""
    input_path = Path( input_path )
    if delimiter is None:
        delimiter = ',' if input_path.suffix.lower() == '.csv' else '\t'

    rows = []
    with open( input_path, 'r', encoding = 'utf-8', newline = '' ) as input_table:
        reader = csv.reader( input_table, delimiter = delimiter )
        for parts in reader:
            rows.append( parts )
    return rows


def convert_path_to_bytes( input_path, delimiter = None ):
    """Read a TSV/CSV file and convert it to .xlsx bytes.
    Returns ( ok, report, xlsx_bytes ). On refusal: ( False, [problems], None )."""
    input_path = Path( input_path )
    try:
        rows = read_table( input_path, delimiter )
    except UnicodeDecodeError as decode_error:
        return ( False, [ f"File is not valid UTF-8 text ({ decode_error }); cannot convert safely." ], None )
    except csv.Error as parse_error:
        return ( False, [ f"Could not parse the table ({ parse_error })." ], None )

    problems = validate_rows( rows )
    if problems:
        return ( False, problems, None )

    return ( True, [], rows_to_xlsx_bytes( rows ) )


def convert_file( input_path, output_path, delimiter = None ):
    """Convert a TSV/CSV file to an .xlsx file on disk.
    Returns ( ok, report ). The output file is written ONLY on success, so a
    refused conversion never leaves a partial/lossy workbook behind."""
    ok, report, xlsx_bytes = convert_path_to_bytes( input_path, delimiter )
    if not ok:
        return ( False, report )

    output_path = Path( output_path )
    output_path.parent.mkdir( parents = True, exist_ok = True )
    with open( output_path, 'wb' ) as output_xlsx:
        output_xlsx.write( xlsx_bytes )
    return ( True, [] )


def main():
    parser = argparse.ArgumentParser(
        description = 'Convert a TSV/CSV table to .xlsx (strict refuse-and-report; no silent data loss).'
    )
    parser.add_argument( 'input', help = 'Path to the input .tsv or .csv file' )
    parser.add_argument( '-o', '--output', default = None, help = 'Path for the output .xlsx (default: input with .xlsx)' )
    args = parser.parse_args()

    input_path = Path( args.input )
    output_path = Path( args.output ) if args.output else input_path.with_suffix( '.xlsx' )

    ok, report = convert_file( input_path, output_path )
    if not ok:
        print( f"REFUSED: {input_path} was NOT converted to Excel (data would be lost or corrupted):", file = sys.stderr )
        for problem in report:
            print( f"  - {problem}", file = sys.stderr )
        sys.exit( 1 )

    print( f"OK: {input_path} -> {output_path}" )


if __name__ == '__main__':
    main()
