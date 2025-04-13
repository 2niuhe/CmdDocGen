#!/usr/bin/env python3
"""
OpenStack Subcommand Processing Script

This script parses all OpenStack subcommands and processes them one by one using cmddocgen.
This solves the problem of OpenStack commands being too complex for LLM to parse all subcommands at once.
"""

import subprocess
import re
import os
import argparse
import time
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("OpenStackProcessor")

def get_openstack_commands():
    """Get all OpenStack subcommands"""
    logger.info("Getting OpenStack subcommand list...")
    
    try:
        result = subprocess.run(
            ["openstack", "help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute 'openstack help' command: {e}")
        output = e.stdout
    
    # Use regex to extract commands
    # Match lines in format "  command subcommand  Description..."
    # Subcommands are lowercase, descriptions start with uppercase
    command_pattern = re.compile(r"^\s{2}([a-z][a-z0-9 -]+?)\s{2,}([A-Z].+)$", re.MULTILINE)
    commands = []
    
    for match in command_pattern.finditer(output):
        command = match.group(1).strip()
        description = match.group(2).strip()
        commands.append((command, description))
    
    logger.info(f"Found {len(commands)} OpenStack subcommands")
    return commands

def save_command_list(commands, output_dir):
    """Save subcommand list to file"""
    os.makedirs(output_dir, exist_ok=True)
    list_file = os.path.join(output_dir, "command_list.txt")
    
    with open(list_file, "w") as f:
        for command, description in commands:
            f.write(f"{command}\n")
    
    logger.info(f"Subcommand list saved to: {list_file}")
    
    # Also save the complete list with descriptions
    full_list_file = os.path.join(output_dir, "command_list_with_descriptions.txt")
    with open(full_list_file, "w") as f:
        for command, description in commands:
            f.write(f"{command} - {description}\n")
    
    logger.info(f"Subcommand list with descriptions saved to: {full_list_file}")

def process_command(command, description, output_dir, max_depth=0, format_type="raw", help_format="cliff"):
    """Process a single OpenStack subcommand"""
    safe_command = command.replace(" ", "_")
    
    logger.info(f"Processing command: openstack {command}")
    
    try:
        cmddocgen_cmd = [
            "cmddocgen",
            f"openstack {command}",
            "-o", output_dir,
            "--format", format_type,
            "--help-format", help_format,
            "--max-depth", str(max_depth)
        ]
        
        result = subprocess.run(
            cmddocgen_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        
        logger.info(f"Command 'openstack {command}' processed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to process command 'openstack {command}': {e}")
        logger.error(f"Output: {e.stdout}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Process OpenStack subcommands and generate documentation using cmddocgen")
    parser.add_argument(
        "--output-dir", "-o",
        default="examples/openstack_commands",
        help="Output directory (default: examples/openstack_commands)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["man", "json", "raw", "all"],
        default="raw",
        help="Output format (default: raw)"
    )
    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        default=0,
        help="Maximum recursion depth (default: 0)"
    )
    parser.add_argument(
        "--help-format",
        choices=["default", "cliff"],
        default="cliff",
        help="Help command format (default: cliff)"
    )
    parser.add_argument(
        "--max-workers", "-w",
        type=int,
        default=4,
        help="Maximum number of parallel worker threads (default: 4)"
    )
    parser.add_argument(
        "--filter", 
        help="Only process commands containing the specified string (e.g. 'server' or 'image')"
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only generate command list, do not execute cmddocgen"
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get all subcommands
    commands = get_openstack_commands()
    
    # Save command list
    save_command_list(commands, args.output_dir)
    
    # If only generating list, exit
    if args.list_only:
        logger.info("Command list generated, exiting")
        return
    
    # If filter is specified, only process matching commands
    if args.filter:
        filtered_commands = [(cmd, desc) for cmd, desc in commands if args.filter in cmd]
        logger.info(f"{len(filtered_commands)} commands remaining after filtering")
        commands = filtered_commands
    
    # Record start time
    start_time = time.time()
    
    # Use thread pool to process commands in parallel
    successful = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = []
        for command, description in commands:
            future = executor.submit(
                process_command,
                command,
                description,
                args.output_dir,
                args.max_depth,
                args.format,
                args.help_format
            )
            futures.append((command, future))
        
        # Wait for all tasks to complete and collect results
        for command, future in futures:
            try:
                result = future.result()
                if result:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Exception occurred while processing command '{command}': {e}")
                failed += 1
    
    # Calculate total time
    elapsed_time = time.time() - start_time
    
    # Print statistics
    logger.info("Processing completed!")
    logger.info(f"Total commands processed: {len(commands)}")
    logger.info(f"Successful: {successful} commands")
    logger.info(f"Failed: {failed} commands")
    logger.info(f"Total time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
