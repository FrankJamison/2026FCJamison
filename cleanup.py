#!/usr/bin/env python3
"""Clean up unnecessary project files"""
import os
import shutil
from pathlib import Path

def cleanup():
    root = Path(__file__).parent
    
    # Files/dirs to remove
    to_remove = [
        'tools/extract_docx_text.py',
        'tools/markdown_to_pdf.py',
        'tools/extract_cv_text.sh',
        'tools/convert_portfolio_images_to_webp.py',
        'tools/rollout_webp_picture_tags.py',
        'tools/fix_webp_suffixes.py',
        'deploy',
    ]
    
    removed_count = 0
    
    # Remove listed items
    for item in to_remove:
        path = root / item
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"✓ Removed {item}")
            removed_count += 1
    
    # Remove __pycache__ directories
    for pycache in root.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache)
            print(f"✓ Removed {pycache.relative_to(root)}")
            removed_count += 1
        except:
            pass
    
    # Remove metadata files
    for metadata in root.glob('static/images/portfolio/*Zone.Identifier'):
        try:
            metadata.unlink()
            print(f"✓ Removed {metadata.relative_to(root)}")
            removed_count += 1
        except:
            pass
    
    print(f"\n✅ Cleanup complete! Removed {removed_count} items.")

if __name__ == '__main__':
    cleanup()
