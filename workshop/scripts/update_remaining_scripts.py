#!/usr/bin/env python3
"""
Script to update remaining download scripts with verbose mode
"""

import os
import re

def add_verbose_mode_to_script(script_path):
    """Add verbose mode to a download script"""
    
    if not os.path.exists(script_path):
        print(f"Script not found: {script_path}")
        return False
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Check if already has argparse
    if 'import argparse' in content:
        print(f"Script {script_path} already has argparse")
        return True
    
    # Find the main function
    main_pattern = r'def main\(\):\s*\n\s*"""[^"]*"""\s*\n'
    match = re.search(main_pattern, content)
    
    if not match:
        print(f"Could not find main function in {script_path}")
        return False
    
    # Replace the main function start
    old_main_start = match.group(0)
    
    # Extract the docstring
    docstring_match = re.search(r'"""([^"]*)"""', old_main_start)
    docstring = docstring_match.group(1) if docstring_match else "Main function"
    
    new_main_start = f'''def main():
    """{docstring}"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='{docstring}')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output (default: progress bar only)')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Auto-confirm import without prompting')
    args = parser.parse_args()
    
'''
    
    # Replace the main function
    content = content.replace(old_main_start, new_main_start)
    
    # Replace print statements with conditional verbose prints
    # This is a simple replacement - more complex logic would need manual review
    
    # Replace common patterns
    replacements = [
        (r'print\("✈️.*Import"\)', 'if args.verbose:\n        print("✈️  OpenFlights Data Import")'),
        (r'print\("=" \* \d+\)', 'if args.verbose:\n        print("=" * 40)'),
        (r'print\("⚠ \.env file not found"\)', 'if args.verbose:\n            print("⚠ .env file not found")'),
        (r'print\("Copy \.env\.example.*"\)', 'if args.verbose:\n            print("Copy .env.example to .env and configure your database settings")'),
        (r'print\("You can still download.*"\)', 'if args.verbose:\n            print("You can still download and analyze data without database connection")'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Write back the file
    with open(script_path, 'w') as f:
        f.write(content)
    
    print(f"Updated {script_path} with verbose mode")
    return True

def main():
    """Update remaining scripts with verbose mode"""
    
    scripts_to_update = [
        'scripts/download_airlines.py',
        'scripts/download_airports.py', 
        'scripts/download_routes.py'
    ]
    
    for script in scripts_to_update:
        print(f"Updating {script}...")
        add_verbose_mode_to_script(script)
    
    print("Done updating scripts")

if __name__ == "__main__":
    main()