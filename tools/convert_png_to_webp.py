#!/usr/bin/env python3
"""
Convert all .png references to .webp in template files.
Handles portfolio image references in template files.
"""

import os
import re
from pathlib import Path

def convert_png_to_webp_in_file(filepath):
    """Convert .png to .webp in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_count = content.count('.png\')')
        
        # Replace .png') with .webp')
        new_content = content.replace('.png\')', '.webp\')')
        
        if original_count > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ {filepath}: Converted {original_count} references")
            return original_count
        else:
            print(f"- {filepath}: No .png references found")
            return 0
    except Exception as e:
        print(f"✗ {filepath}: Error - {e}")
        return 0

def main():
    # Files to convert
    files_to_convert = [
        'templates/partials/portfolioBody.html',
        'templates/partials/blogBody.html',
        'templates/partials/portfolioCard.html',
        'templates/partials/featuredProjects.html'
    ]
    
    total_converted = 0
    
    for filepath in files_to_convert:
        if os.path.exists(filepath):
            converted = convert_png_to_webp_in_file(filepath)
            total_converted += converted
        else:
            print(f"✗ {filepath}: File not found")
    
    print(f"\n✓ Total references converted: {total_converted}")

if __name__ == '__main__':
    main()
