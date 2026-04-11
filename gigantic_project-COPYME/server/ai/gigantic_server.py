#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 April 02 | Purpose: GIGANTIC data server with brutalist design - config-driven, reusable
# Human: Eric Edsinger

"""
GIGANTIC Data Server: Centralized web server for GIGANTIC project data.

Serves files directly from subproject upload_to_server/ directories.
All configuration is read from START_HERE-server_config.yaml.

Usage:
    python3 gigantic_server.py [options]

Options:
    --config PATH           Path to config file (default: ../START_HERE-server_config.yaml)
    --port PORT             Override port from config
    --subprojects-dir PATH  Override subprojects directory path

Access:
    Via SSH tunnel from HPC:
        ssh -L PORT:NODE:PORT YOUR_USERNAME@your.hpc.server
    Then open in browser:
        http://localhost:PORT/
"""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import http.server
import socketserver
import socket
import argparse
import sys
import urllib.parse
import threading
import time
import re


# ============================================================================
# Configuration Parser
# ============================================================================

class ServerConfig:
    """Parses and holds server configuration from YAML file."""

    def __init__( self, config_path: Path ):
        """
        Parse configuration from YAML file.

        Uses a simple manual parser to avoid PyYAML dependency.
        Supports: scalars, simple lists, one-level maps.

        Args:
            config_path: Path to START_HERE-server_config.yaml
        """
        self.config_path = config_path
        self.raw = {}

        if not config_path.exists():
            print( f"ERROR: Config file not found: {config_path}" )
            sys.exit( 1 )

        self._parse( config_path )

        # Extract configuration values with defaults
        self.project_name = self._get_string( 'project_name', 'GIGANTIC DATA' )
        self.port = self._get_integer( 'port', 9456 )
        self.refresh_interval_seconds = self._get_integer( 'refresh_interval_seconds', 300 )

        # Subprojects: either "all" or a list
        subprojects_value = self.raw.get( 'subprojects', 'all' )
        if isinstance( subprojects_value, str ):
            self.subprojects_mode = subprojects_value.strip().strip( '"' ).strip( "'" )
            self.subprojects_list = []
        elif isinstance( subprojects_value, list ):
            self.subprojects_mode = 'list'
            self.subprojects_list = subprojects_value
        else:
            self.subprojects_mode = 'all'
            self.subprojects_list = []

        # Display customization
        self.display_names = self._get_map( 'display_names' )
        self.exclude_from_display = self._get_list( 'exclude_from_display' )
        self.section_sort_order = self._get_list( 'section_sort_order' )

        # File filtering
        self.exclude_file_patterns = self._get_list( 'exclude_file_patterns' )
        self.subproject_file_exclusions = self._get_map( 'subproject_file_exclusions' )

        # SLURM settings
        slurm_map = self._get_map( 'slurm' )
        self.slurm_account = slurm_map.get( 'account', 'your_account' )
        self.slurm_qos = slurm_map.get( 'qos', 'your_qos' )
        self.slurm_partition = slurm_map.get( 'partition', 'hpg-default' )
        self.slurm_time_hours = int( slurm_map.get( 'time_hours', 725 ) )
        self.slurm_memory_gb = int( slurm_map.get( 'memory_gb', 4 ) )
        self.slurm_cpus = int( slurm_map.get( 'cpus', 1 ) )
        self.slurm_mail_user = slurm_map.get( 'mail_user', '' )

        # Credits
        credits_map = self._get_map( 'credits' )
        self.credits_ai = credits_map.get( 'ai', 'Claude Code' )
        self.credits_human = credits_map.get( 'human', '' )

    def _parse( self, config_path: Path ):
        """
        Simple YAML parser for flat structure with lists and one-level maps.
        Handles: scalars, lists (- item), and nested maps (key: value under a parent).
        """
        with open( config_path, 'r' ) as f:
            lines = f.readlines()

        current_key = None
        current_list = None
        current_map = None
        current_map_key = None

        for line in lines:
            stripped = line.rstrip()

            # Skip empty lines and comments
            if not stripped or stripped.lstrip().startswith( '#' ):
                continue

            # Calculate indentation
            indent = len( line ) - len( line.lstrip() )

            # Top-level key: value
            if indent == 0 and ':' in stripped:
                # Save any pending list or map
                if current_list is not None and current_key:
                    self.raw[ current_key ] = current_list
                    current_list = None
                if current_map is not None and current_map_key:
                    self.raw[ current_map_key ] = current_map
                    current_map = None
                    current_map_key = None

                parts_line = stripped.split( ':', 1 )
                key = parts_line[ 0 ].strip()
                value = parts_line[ 1 ].strip() if len( parts_line ) > 1 else ''

                # Remove inline comments (but not inside quoted strings)
                if value and not value.startswith( '"' ) and not value.startswith( "'" ):
                    value = re.split( r'\s+#', value )[ 0 ].strip()

                # Remove quotes
                value = value.strip( '"' ).strip( "'" )

                if value == '' or value == '{}' or value == '[]':
                    # Could be a list or map starting on next lines
                    if value == '{}':
                        self.raw[ key ] = {}
                        current_key = None
                    elif value == '[]':
                        self.raw[ key ] = []
                        current_key = None
                    else:
                        current_key = key
                        current_list = None
                        current_map = None
                else:
                    self.raw[ key ] = value
                    current_key = key

            # Indented list item: - value
            elif indent > 0 and stripped.lstrip().startswith( '-' ):
                item = stripped.lstrip()[ 1: ].strip()
                item = item.strip( '"' ).strip( "'" )

                # Remove inline comments
                if item and not item.startswith( '"' ) and not item.startswith( "'" ):
                    item = re.split( r'\s+#', item )[ 0 ].strip()
                    item = item.strip( '"' ).strip( "'" )

                if current_list is None:
                    current_list = []
                current_list.append( item )

                # If we were building a map, this list belongs to the map's last key
                if current_map is not None and current_map_key:
                    # Actually this is a list value within a map - handle separately
                    pass

            # Indented key: value (map entry)
            elif indent > 0 and ':' in stripped:
                parts_line = stripped.strip().split( ':', 1 )
                sub_key = parts_line[ 0 ].strip()
                sub_value = parts_line[ 1 ].strip() if len( parts_line ) > 1 else ''

                # Remove inline comments and quotes
                if sub_value and not sub_value.startswith( '"' ) and not sub_value.startswith( "'" ):
                    sub_value = re.split( r'\s+#', sub_value )[ 0 ].strip()
                sub_value = sub_value.strip( '"' ).strip( "'" )

                if current_map is None:
                    current_map = {}
                    current_map_key = current_key
                current_map[ sub_key ] = sub_value

        # Save any pending structures
        if current_list is not None and current_key:
            self.raw[ current_key ] = current_list
        if current_map is not None and current_map_key:
            self.raw[ current_map_key ] = current_map

    def _get_string( self, key: str, default: str = '' ) -> str:
        value = self.raw.get( key, default )
        if isinstance( value, str ):
            return value
        return default

    def _get_integer( self, key: str, default: int = 0 ) -> int:
        value = self.raw.get( key, default )
        try:
            return int( value )
        except ( ValueError, TypeError ):
            return default

    def _get_list( self, key: str ) -> list:
        value = self.raw.get( key, [] )
        if isinstance( value, list ):
            return value
        return []

    def _get_map( self, key: str ) -> dict:
        value = self.raw.get( key, {} )
        if isinstance( value, dict ):
            return value
        return {}


# ============================================================================
# Subproject Data
# ============================================================================

class SubprojectData:
    """Represents a GIGANTIC subproject with its data folders."""

    def __init__( self, upload_dir: Path, name: str, config: ServerConfig ):
        """
        Initialize subproject data structure.

        Args:
            upload_dir: Path to the subproject's upload_to_server/ directory
            name: Subproject directory name
            config: Server configuration
        """
        self.upload_dir = upload_dir
        self.name = name
        self.config = config
        self.folders = {}  # folder_name -> Path

    def discover_folders( self ):
        """Discover top-level folders in this subproject's upload_to_server/ directory."""
        try:
            if not self.upload_dir.exists():
                return

            for item in self.upload_dir.iterdir():
                if item.is_dir():
                    self.folders[ item.name ] = item
        except PermissionError:
            pass

    def should_exclude_file( self, file_path: Path ) -> bool:
        """
        Determine if a file should be excluded from the server.

        Args:
            file_path: Path to the file

        Returns:
            True if file should be excluded
        """
        filename = file_path.name
        filename_lower = filename.lower()

        # Exclude hidden files
        if filename.startswith( '.' ):
            return True

        # Check global exclusion patterns
        for pattern in self.config.exclude_file_patterns:
            if pattern.lower() in filename_lower:
                return True

        # Check subproject-specific exclusions
        name_lower = self.name.lower()
        for keyword, exclusion_patterns in self.config.subproject_file_exclusions.items():
            if keyword.lower() in name_lower:
                if isinstance( exclusion_patterns, list ):
                    for exclusion_pattern in exclusion_patterns:
                        if exclusion_pattern.lower() in filename_lower:
                            return True
                elif isinstance( exclusion_patterns, str ):
                    if exclusion_patterns.lower() in filename_lower:
                        return True

        return False


# ============================================================================
# Main Server
# ============================================================================

class GIGANTICServer:
    """Main server class for GIGANTIC data."""

    def __init__( self, config: ServerConfig, subprojects_dir: Path, port_override: Optional[ int ] = None ):
        """
        Initialize the GIGANTIC server.

        Args:
            config: Server configuration
            subprojects_dir: Path to the subprojects/ directory
            port_override: Optional port override from CLI
        """
        self.config = config
        self.subprojects_dir = subprojects_dir
        self.port = port_override if port_override is not None else config.port
        self.subprojects = []

        # Discover all data
        self.discover_data()

    @staticmethod
    def clean_display_name( name: str ) -> str:
        """
        Convert technical names to human-readable display names.

        Args:
            name: Technical name (e.g., 'nitric_oxide-synthases')

        Returns:
            Human-readable name (e.g., 'nitric oxide synthases')
        """
        return name.replace( '_', ' ' ).replace( '-', ' ' )

    def get_display_name( self, subproject_name: str ) -> str:
        """
        Get the display name for a subproject.
        Uses config display_names first, then auto-formats from directory name.

        Args:
            subproject_name: Directory name of the subproject

        Returns:
            Human-readable display name
        """
        # Check config for custom display name
        if subproject_name in self.config.display_names:
            return self.config.display_names[ subproject_name ]

        # Auto-format: replace underscores/dashes with spaces, uppercase
        return self.clean_display_name( subproject_name ).upper()

    def should_exclude_subproject( self, subproject_name: str ) -> bool:
        """
        Determine if a subproject should be excluded from the landing page.

        Args:
            subproject_name: Subproject directory name

        Returns:
            True if subproject should be excluded
        """
        name_lower = subproject_name.lower()
        for excluded in self.config.exclude_from_display:
            if excluded.lower() in name_lower:
                return True
        return False

    def get_section_sort_order( self, section_name: str ) -> int:
        """
        Get sort order for sections on folder pages.
        Uses config section_sort_order list for priority.

        Args:
            section_name: Section/subfolder name

        Returns:
            Sort priority (lower = earlier)
        """
        section_lower = section_name.lower()
        for index, keyword in enumerate( self.config.section_sort_order ):
            if keyword.lower() in section_lower:
                return index
        return 99

    def _get_subproject_names( self ) -> List[ str ]:
        """
        Get list of subproject names to serve based on config.

        Returns:
            List of subproject directory names
        """
        if self.config.subprojects_mode == 'all':
            # Auto-discover all subprojects with upload_to_server/ directories
            names = []
            for item in sorted( self.subprojects_dir.iterdir() ):
                if item.is_dir():
                    upload_dir = item / 'upload_to_server'
                    if upload_dir.exists() and upload_dir.is_dir():
                        names.append( item.name )
            return names
        else:
            return self.config.subprojects_list

    def discover_data( self ):
        """Discover all subprojects and their data from upload_to_server/ directories."""
        print( "Discovering data files..." )
        print( f"  Subprojects directory: {self.subprojects_dir}" )
        print()

        if not self.subprojects_dir.exists():
            print( f"  WARNING: Subprojects directory does not exist: {self.subprojects_dir}" )
            return

        subproject_names = self._get_subproject_names()

        for subproject_name in subproject_names:
            upload_dir = self.subprojects_dir / subproject_name / 'upload_to_server'

            if not upload_dir.exists():
                continue

            subproject = SubprojectData( upload_dir, subproject_name, self.config )
            subproject.discover_folders()

            if subproject.folders:
                self.subprojects.append( subproject )
                print( f"  {subproject_name}: {len( subproject.folders )} folder(s)" )
            else:
                # Check if upload_to_server has files directly (no subdirectories)
                files_direct = [
                    f for f in upload_dir.iterdir()
                    if f.is_file() and not subproject.should_exclude_file( f )
                ]
                if files_direct:
                    # Create a virtual folder for files at the root level
                    subproject.folders[ subproject_name ] = upload_dir
                    self.subprojects.append( subproject )
                    print( f"  {subproject_name}: {len( files_direct )} file(s)" )

        print()
        print( f"  Total subprojects: {len( self.subprojects )}" )
        total_folders = sum( len( sp.folders ) for sp in self.subprojects )
        print( f"  Total data folders: {total_folders}" )
        print()

    def discover_files_recursive( self, directory: Path, subproject: SubprojectData, base_path: Path ) -> Dict[ str, List[ Path ] ]:
        """
        Recursively discover all files within a directory, organizing them by subfolder.

        Args:
            directory: Directory to search
            subproject: SubprojectData instance for exclusion rules
            base_path: Base path for computing relative paths

        Returns:
            Dictionary mapping relative subfolder paths to lists of files
        """
        subfolders___files = {}

        try:
            for item in directory.iterdir():
                if item.is_dir():
                    try:
                        # Check if this directory contains files directly
                        files_in_directory = [
                            f for f in item.iterdir()
                            if f.is_file() and not subproject.should_exclude_file( f )
                        ]

                        if files_in_directory:
                            relative_path = item.relative_to( base_path )
                            subfolders___files[ str( relative_path ) ] = files_in_directory

                        # Recurse into subdirectories
                        nested_files = self.discover_files_recursive( item, subproject, base_path )
                        subfolders___files.update( nested_files )

                    except ( PermissionError, OSError ):
                        pass

                elif item.is_file() and not subproject.should_exclude_file( item ):
                    # Files at the root of the folder
                    root_key = '.'
                    if root_key not in subfolders___files:
                        subfolders___files[ root_key ] = []
                    subfolders___files[ root_key ].append( item )

        except ( PermissionError, OSError ):
            pass

        return subfolders___files

    @staticmethod
    def get_file_icon( extension: str ) -> str:
        """
        Return an emoji icon based on file extension.

        Args:
            extension: File extension (e.g., '.txt', '.pdf')

        Returns:
            Emoji icon as string
        """
        icons = {
            '.txt': '&#128196;',
            '.tsv': '&#128202;',
            '.csv': '&#128202;',
            '.pdf': '&#128213;',
            '.svg': '&#128444;',
            '.png': '&#128444;',
            '.jpg': '&#128444;',
            '.jpeg': '&#128444;',
            '.fasta': '&#129516;',
            '.fa': '&#129516;',
            '.faa': '&#129516;',
            '.fna': '&#129516;',
            '.aa': '&#129516;',
            '.log': '&#128203;',
            '.html': '&#127760;',
            '.json': '&#128203;',
            '.xml': '&#128203;',
            '.gz': '&#128230;',
            '.zip': '&#128230;',
            '.tar': '&#128230;',
        }
        return icons.get( extension.lower(), '&#128196;' )

    @staticmethod
    def format_file_size( size_bytes: int ) -> str:
        """
        Format file size in human-readable form.

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted string (e.g., '4.2 MB')
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / ( 1024 * 1024 ):.1f} MB"
        else:
            return f"{size_bytes / ( 1024 * 1024 * 1024 ):.2f} GB"

    def get_hostname( self ) -> str:
        """Get the hostname for accessing the server."""
        try:
            hostname = socket.getfqdn()
            if hostname and hostname != 'localhost':
                return hostname
            return socket.gethostname()
        except Exception:
            return 'localhost'

    # ========================================================================
    # HTML Generation
    # ========================================================================

    def _css_common( self ) -> str:
        """Return common CSS used across all pages."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'Arial', sans-serif;
            background-color: #000000;
            color: #FFFFFF;
            line-height: 1.6;
            padding: 0;
            margin: 0;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        footer {
            margin-top: 60px;
            padding: 40px;
            text-align: center;
            background-color: #FFFFFF;
            border-top: 8px solid #000000;
            color: #000000;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 1px;
        }
"""

    def _footer_html( self ) -> str:
        """Return the footer HTML."""
        credits_lines = [ f"AI: {self.config.credits_ai.upper()}" ]
        if self.config.credits_human:
            credits_lines.append( f"HUMAN: {self.config.credits_human.upper()}" )

        credits_html = '<br>\n        '.join( credits_lines )

        return f"""
    <footer>
        GIGANTIC DATA SERVER<br>
        {credits_html}
    </footer>
"""

    def generate_landing_page( self ) -> str:
        """Generate the main landing page HTML with brutalist design."""

        # Split project name for styling (first word white, second word pink)
        name_parts = self.config.project_name.split( ' ', 1 )
        if len( name_parts ) == 2:
            title_html = f'{name_parts[ 0 ]} <span class="pink">{name_parts[ 1 ]}</span>'
        else:
            title_html = self.config.project_name

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.project_name}</title>
    <style>
{self._css_common()}

        h1 {{
            font-size: 115px;
            font-weight: 900;
            letter-spacing: -3px;
            text-transform: uppercase;
            color: #FFFFFF;
            border: 8px solid #FFFFFF;
            padding: 30px;
            margin-bottom: 40px;
            background-color: #000000;
            line-height: 1.2;
            text-align: left;
        }}

        h1 .pink {{
            color: #FF007F;
            margin-left: 30px;
        }}

        h2 {{
            font-size: 32px;
            font-weight: 900;
            text-transform: uppercase;
            color: #000000;
            background-color: #FFFFFF;
            padding: 20px;
            margin: 40px 0 20px 0;
            border-left: 12px solid #000000;
            letter-spacing: 2px;
        }}

        .info {{
            background-color: #FFFFFF;
            border: 4px solid #000000;
            padding: 30px;
            margin-bottom: 40px;
            color: #000000;
            font-size: 16px;
        }}

        .folder-grid {{
            display: grid;
            grid-template-columns: repeat( auto-fill, minmax( 300px, 1fr ) );
            gap: 20px;
            margin-bottom: 40px;
        }}

        .folder-card {{
            background-color: #FFFFFF;
            border: 4px solid #000000;
            padding: 30px;
            text-align: center;
            transition: all 0.2s;
            text-decoration: none;
            display: block;
        }}

        .folder-card:hover {{
            background-color: #FF007F;
            transform: translateY( -5px );
            box-shadow: 8px 8px 0 #FFFFFF;
        }}

        .folder-name {{
            color: #000000;
            font-size: 20px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}

        .folder-card:hover .folder-name {{
            color: #FFFFFF;
        }}

        .folder-count {{
            color: #808080;
            font-size: 14px;
            font-weight: 600;
        }}

        .folder-card:hover .folder-count {{
            color: #FFFFFF;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title_html}</h1>
"""

        # Generate sections for each subproject
        for subproject in self.subprojects:
            if self.should_exclude_subproject( subproject.name ):
                continue

            display_name = self.get_display_name( subproject.name )

            html += f"""
        <h2>{display_name}</h2>
        <div class="folder-grid">
"""

            for folder_name, folder_path in sorted( subproject.folders.items() ):
                folder_display = self.clean_display_name( folder_name )
                url_path = urllib.parse.quote( f"{subproject.name}/{folder_name}" )

                html += f"""
            <a href="/{url_path}" class="folder-card">
                <div class="folder-name">{folder_display}</div>
            </a>
"""

            html += """
        </div>
"""

        html += f"""
        </div>

        <div class="info">
            <strong>Server Information:</strong><br>
            Port: {self.port}<br>
            Subprojects: {len( self.subprojects )}<br>
            Generated: {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}
        </div>
    </div>
{self._footer_html()}
</body>
</html>
"""
        return html

    def generate_folder_page( self, subproject_name: str, folder_name: str ) -> str:
        """
        Generate a page showing subfolders and files for a top-level folder.

        Args:
            subproject_name: Name of the subproject
            folder_name: Name of the top-level folder

        Returns:
            HTML string for the folder page
        """
        # Find the subproject and folder
        subproject = None
        for sp in self.subprojects:
            if sp.name == subproject_name:
                subproject = sp
                break

        if not subproject or folder_name not in subproject.folders:
            return self.generate_404_page()

        top_folder_path = subproject.folders[ folder_name ]
        folder_display = self.clean_display_name( folder_name )

        # Discover all subfolders and their files recursively
        subfolders___files = self.discover_files_recursive( top_folder_path, subproject, top_folder_path )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subproject_name} - {folder_display}</title>
    <style>
{self._css_common()}

        .breadcrumb {{
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            color: #808080;
        }}

        .breadcrumb a {{
            color: #FFFFFF;
            text-decoration: none;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 32px;
            display: flex;
            align-items: center;
        }}

        .breadcrumb a:hover {{
            color: #FF007F;
        }}

        .breadcrumb .arrow {{
            font-size: 32px;
            font-weight: 900;
            margin-right: 10px;
        }}

        h1 {{
            font-size: 64px;
            font-weight: 900;
            letter-spacing: -2px;
            text-transform: uppercase;
            color: #FFFFFF;
            border: 8px solid #FFFFFF;
            padding: 30px;
            margin-bottom: 40px;
            background-color: #000000;
            line-height: 1.2;
        }}

        .category {{
            background-color: #FFFFFF;
            margin-bottom: 30px;
            border: 6px solid #000000;
            overflow: hidden;
        }}

        .category-header {{
            background-color: #FFFFFF;
            color: #000000;
            padding: 25px 30px;
            font-size: 24px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 3px;
            border-bottom: 4px solid #000000;
        }}

        .file-list {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}

        .file-item {{
            padding: 20px 30px;
            border-bottom: 2px solid #000000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #FFFFFF;
            transition: all 0.2s;
        }}

        .file-item:last-child {{
            border-bottom: none;
        }}

        .file-item:hover {{
            background-color: #FF007F;
            transform: translateX( 10px );
        }}

        .file-item:hover .file-link {{
            color: #FFFFFF;
        }}

        .file-item:hover .file-info {{
            color: #FFFFFF;
        }}

        .file-link {{
            color: #000000;
            text-decoration: none;
            font-weight: 700;
            font-size: 16px;
            flex: 1;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .file-info {{
            display: flex;
            gap: 15px;
            color: #808080;
            font-size: 13px;
            font-weight: 600;
            align-items: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="breadcrumb">
            <a href="/"><span class="arrow">&larr;</span> {self.config.project_name}</a>
        </div>

        <h1>{folder_display}</h1>
"""

        # Sort sections by custom order then alphabetically
        sorted_subfolders = sorted(
            subfolders___files.keys(),
            key=lambda name: ( self.get_section_sort_order( name ), name )
        )

        for subfolder_name in sorted_subfolders:
            files_in_subfolder = subfolders___files[ subfolder_name ]

            if subfolder_name == '.':
                subfolder_display = 'Files'
            else:
                subfolder_display = self.clean_display_name( subfolder_name )

            html += f"""
        <div class="category">
            <div class="category-header">{subfolder_display}</div>
            <ul class="file-list">
"""

            for file_path in sorted( files_in_subfolder, key=lambda f: f.name ):
                file_url = urllib.parse.quote(
                    f"download/{subproject_name}/{folder_name}/{subfolder_name}/{file_path.name}",
                    safe='/'
                )

                size_str = self.format_file_size( file_path.stat().st_size )
                file_icon = self.get_file_icon( file_path.suffix )
                file_display_name = self.clean_display_name( file_path.name )

                html += f"""
                <li class="file-item">
                    <a href="/{file_url}" class="file-link" download>
                        {file_icon} {file_display_name}
                    </a>
                    <div class="file-info">
                        <span>{size_str}</span>
                    </div>
                </li>
"""

            html += """
            </ul>
        </div>
"""

        html += f"""
    </div>
{self._footer_html()}
</body>
</html>
"""
        return html

    def generate_404_page( self ) -> str:
        """Generate a 404 error page with brutalist design."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Not Found</title>
    <style>
{self._css_common()}

        body {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}

        .error-container {{
            text-align: center;
            padding: 40px;
        }}

        .error-code {{
            font-size: 128px;
            font-weight: 900;
            color: #FF007F;
            line-height: 1;
            margin-bottom: 20px;
        }}

        .error-message {{
            font-size: 32px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 40px;
        }}

        .back-link {{
            display: inline-block;
            background-color: #FFFFFF;
            color: #000000;
            padding: 20px 40px;
            text-decoration: none;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 4px solid #000000;
            transition: all 0.2s;
        }}

        .back-link:hover {{
            background-color: #FF007F;
            color: #FFFFFF;
            transform: translateY( -5px );
            box-shadow: 8px 8px 0 #FFFFFF;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">404</div>
        <div class="error-message">Page Not Found</div>
        <a href="/" class="back-link">&larr; Back to Home</a>
    </div>
</body>
</html>
"""
        return html

    # ========================================================================
    # Server Runtime
    # ========================================================================

    def auto_refresh_data( self, interval_seconds: int = 300 ):
        """
        Automatically refresh data discovery at configured interval.

        Args:
            interval_seconds: Seconds between refreshes
        """
        while True:
            time.sleep( interval_seconds )
            print( f"\n[{datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}] Auto-refreshing data..." )

            self.subprojects = []
            subproject_names = self._get_subproject_names()

            for subproject_name in subproject_names:
                upload_dir = self.subprojects_dir / subproject_name / 'upload_to_server'
                if not upload_dir.exists():
                    continue

                subproject = SubprojectData( upload_dir, subproject_name, self.config )
                subproject.discover_folders()

                if subproject.folders:
                    self.subprojects.append( subproject )
                else:
                    files_direct = [
                        f for f in upload_dir.iterdir()
                        if f.is_file() and not subproject.should_exclude_file( f )
                    ]
                    if files_direct:
                        subproject.folders[ subproject_name ] = upload_dir
                        self.subprojects.append( subproject )

            total_folders = sum( len( sp.folders ) for sp in self.subprojects )
            print( f"  Subprojects: {len( self.subprojects )}, Data folders: {total_folders}" )

    def start( self ):
        """Start the HTTP server."""
        server_instance = self
        static_dir = Path( __file__ ).parent / 'static'

        class RequestHandler( http.server.SimpleHTTPRequestHandler ):
            """Custom HTTP request handler for GIGANTIC server."""

            def do_GET( self ):
                """Handle GET requests."""
                parsed_path = urllib.parse.urlparse( self.path )
                path = parsed_path.path

                # Landing page
                if path == '/' or path == '/index.html':
                    self.send_response( 200 )
                    self.send_header( 'Content-type', 'text/html' )
                    self.end_headers()
                    self.wfile.write( server_instance.generate_landing_page().encode() )

                # Serve static files (icons, etc.)
                elif path.startswith( '/static/' ):
                    relative_path = path[ len( '/static/' ): ]
                    file_path = static_dir / relative_path

                    if file_path.exists() and file_path.is_file():
                        self.send_response( 200 )

                        content_types = {
                            '.svg': 'image/svg+xml',
                            '.png': 'image/png',
                            '.css': 'text/css',
                            '.js': 'application/javascript',
                        }
                        content_type = content_types.get( file_path.suffix, 'application/octet-stream' )

                        self.send_header( 'Content-type', content_type )
                        self.end_headers()

                        with open( file_path, 'rb' ) as f:
                            self.wfile.write( f.read() )
                    else:
                        self.send_response( 404 )
                        self.send_header( 'Content-type', 'text/html' )
                        self.end_headers()
                        self.wfile.write( b'<h1>404 - Not Found</h1>' )

                # Download file
                elif path.startswith( '/download/' ):
                    parts = path.split( '/' )[ 2: ]  # Skip '', 'download'

                    if len( parts ) >= 3:
                        subproject_name = urllib.parse.unquote( parts[ 0 ] )
                        top_folder_name = urllib.parse.unquote( parts[ 1 ] )
                        filename = urllib.parse.unquote( parts[ -1 ] )

                        # Subfolder path: everything between top_folder and filename
                        # May be empty when files are at the root of the folder
                        if len( parts ) > 3:
                            subfolder_parts = parts[ 2:-1 ]
                            subfolder_path_string = '/'.join( urllib.parse.unquote( p ) for p in subfolder_parts )
                        else:
                            subfolder_path_string = '.'

                        for sp in server_instance.subprojects:
                            if sp.name == subproject_name and top_folder_name in sp.folders:
                                top_folder_path = sp.folders[ top_folder_name ]
                                subfolder_path = top_folder_path / subfolder_path_string
                                file_path = subfolder_path / filename

                                if file_path.exists() and file_path.is_file():
                                    self.send_response( 200 )

                                    content_types = {
                                        '.txt': 'text/plain',
                                        '.tsv': 'text/tab-separated-values',
                                        '.csv': 'text/csv',
                                        '.pdf': 'application/pdf',
                                        '.svg': 'image/svg+xml',
                                        '.png': 'image/png',
                                        '.jpg': 'image/jpeg',
                                        '.jpeg': 'image/jpeg',
                                        '.html': 'text/html',
                                        '.json': 'application/json',
                                        '.xml': 'application/xml',
                                        '.aa': 'text/plain',
                                        '.fasta': 'text/plain',
                                        '.fa': 'text/plain',
                                        '.faa': 'text/plain',
                                        '.fna': 'text/plain',
                                        '.mafft': 'text/plain',
                                        '.clipkit-smartgap': 'text/plain',
                                        '.fasttree': 'text/plain',
                                        '.iqtree': 'text/plain',
                                        '.log': 'text/plain',
                                        '.gz': 'application/gzip',
                                        '.zip': 'application/zip',
                                        '.tar': 'application/x-tar',
                                    }
                                    content_type = content_types.get( file_path.suffix.lower(), 'application/octet-stream' )

                                    file_size = file_path.stat().st_size

                                    self.send_header( 'Content-type', content_type )
                                    self.send_header( 'Content-Length', str( file_size ) )
                                    self.send_header( 'Content-Disposition', f'attachment; filename="{filename}"' )
                                    self.end_headers()

                                    # Chunked streaming: 1 MB chunks
                                    CHUNK_SIZE = 1024 * 1024
                                    with open( file_path, 'rb' ) as f:
                                        while True:
                                            chunk = f.read( CHUNK_SIZE )
                                            if not chunk:
                                                break
                                            self.wfile.write( chunk )
                                    return

                    # File not found
                    self.send_response( 404 )
                    self.send_header( 'Content-type', 'text/html' )
                    self.end_headers()
                    self.wfile.write( server_instance.generate_404_page().encode() )

                # Folder page
                elif path.startswith( '/' ) and len( path.split( '/' ) ) >= 3:
                    parts = path.split( '/' )[ 1: ]
                    subproject_name = urllib.parse.unquote( parts[ 0 ] )
                    folder_name = urllib.parse.unquote( '/'.join( parts[ 1: ] ) )

                    self.send_response( 200 )
                    self.send_header( 'Content-type', 'text/html' )
                    self.end_headers()
                    self.wfile.write( server_instance.generate_folder_page( subproject_name, folder_name ).encode() )

                else:
                    self.send_response( 404 )
                    self.send_header( 'Content-type', 'text/html' )
                    self.end_headers()
                    self.wfile.write( server_instance.generate_404_page().encode() )

            def log_message( self, format, *args ):
                """Suppress default request logging (too verbose)."""
                pass

        # Start the server
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer( ( '', self.port ), RequestHandler ) as httpd:
            hostname = self.get_hostname()
            refresh_seconds = self.config.refresh_interval_seconds

            print( "=" * 80 )
            print( f"{self.config.project_name} SERVER STARTED" )
            print( "=" * 80 )
            print( f"Hostname: {hostname}" )
            print( f"Port: {self.port}" )
            print()
            print( "Access via SSH tunnel:" )
            print( f"  ssh -L {self.port}:{hostname}:{self.port} YOUR_USERNAME@YOUR_HPC_SERVER" )
            print()
            print( "Then open in browser:" )
            print( f"  http://localhost:{self.port}/" )
            print()
            print( f"Auto-refresh: Every {refresh_seconds} seconds" )
            print()
            print( "=" * 80 )
            print()

            # Start auto-refresh thread
            refresh_thread = threading.Thread(
                target=self.auto_refresh_data,
                args=( refresh_seconds, ),
                daemon=True
            )
            refresh_thread.start()

            httpd.serve_forever()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the GIGANTIC server."""
    parser = argparse.ArgumentParser(
        description='GIGANTIC Data Server - Centralized web server for project data'
    )

    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to config file (default: ../START_HERE-server_config.yaml relative to script)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Override port from config file'
    )

    parser.add_argument(
        '--subprojects-dir',
        type=str,
        default=None,
        help='Override subprojects directory path'
    )

    args = parser.parse_args()

    # Determine config path
    script_dir = Path( __file__ ).parent
    if args.config:
        config_path = Path( args.config )
    else:
        config_path = script_dir.parent / 'START_HERE-server_config.yaml'

    # Load configuration
    config = ServerConfig( config_path )

    # Determine subprojects directory
    if args.subprojects_dir:
        subprojects_dir = Path( args.subprojects_dir )
    else:
        subprojects_dir = script_dir.parent.parent / 'subprojects'

    # Validate subprojects directory
    if not subprojects_dir.exists():
        print( f"ERROR: Subprojects directory does not exist: {subprojects_dir}" )
        sys.exit( 1 )

    # Create and start server
    server = GIGANTICServer(
        config=config,
        subprojects_dir=subprojects_dir,
        port_override=args.port
    )

    server.start()


if __name__ == '__main__':
    main()
