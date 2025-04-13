#!/usr/bin/env python3
"""
CmdDocGen - Universal Command Line Help Information Extraction Tool

This tool can extract help information from any command line tool and convert it to standard man page format.
"""

import argparse
import json
import os
import subprocess
import logging
from collections import deque
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

# Import new LLM module
from cmddocgen.llm import LLMParser

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CmdDocGen.Extractor")


class CommandNode:
    """Command tree node class for building n-ary tree structure"""

    def __init__(self, name: str, description: str = "", parent: Optional["CommandNode"] = None) -> None:
        self.name = name  # Command name
        self.description = description  # Command description
        self.parent = parent  # Parent node
        self.children: Dict[str, "CommandNode"] = {}  # Child command dictionary {command name: CommandNode}
        self.raw_help = ""  # Raw help text
        self.parsed_help: Dict[str, Any] = {}  # Parsed help information

    def add_child(self, name: str, description: str = "") -> "CommandNode":
        """Add child command"""
        if name not in self.children:
            self.children[name] = CommandNode(name, description, self)
        return self.children[name]

    def get_full_command(self) -> str:
        """Get full command path from root node to current node"""
        if not self.parent:
            return self.name
        return f"{self.parent.get_full_command()} {self.name}"

    def __str__(self) -> str:
        return f"{self.name} ({len(self.children)} subcommands)"


class HelpExtractor:
    """Universal command line help information extraction tool"""

    def __init__(
        self,
        command: Optional[str] = None,
        output_dir: str = "man_pages",
        max_depth: int = 2,
        max_subcommands_per_level: int = 150,
        help_format: str = "default",
    ) -> None:
        """Initialize help extractor"""
        self.command = command
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.max_subcommands_per_level = max_subcommands_per_level
        self.help_format = help_format

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Initialize LLM parser
        self.parser = LLMParser()

        # Help command format configuration
        self.help_command_formats = {
            # Default format: command --help
            "default": lambda cmd: [*cmd.split(), "--help"],
            # cliff format: command help subcommand
            "cliff": lambda cmd: self._cliff_help_format(cmd),
            # Other formats can be added here...
        }

        # Command format mapping
        self.command_format_mapping = {
            "cliff": "cliff",
            # Other command mappings can be added here...
        }

        logger.info(
            f"HelpExtractor initialized, max depth: {max_depth}, max subcommands per level: {max_subcommands_per_level}"
        )

    def _cliff_help_format(self, cmd: str) -> List[str]:
        """Handle cliff command help format"""
        parts = cmd.split()
        if len(parts) == 1:
            # Root command: cliff --help
            return [parts[0], "--help"]
        else:
            # Subcommand: cliff help subcommand
            return [parts[0], "help", " ".join(parts[1:])]

    def _get_help_command(self, command: str) -> List[str]:
        """Determine which help format to use based on command"""
        # Get root command
        root_command = command.split()[0]

        # Find corresponding format
        format_name = self.command_format_mapping.get(root_command, self.help_format)
        format_func = self.help_command_formats[format_name]

        # Generate help command
        help_command = format_func(command)
        logger.info(
            f"Using '{format_name}' format to get help info for command '{command}': {' '.join(help_command)}"
        )

        return help_command

    def extract_help(self, command: str) -> Dict[str, Any]:
        """Extract command help information, using n-ary tree structure to manage commands"""
        logger.info(f"Starting to extract help information for command '{command}'")

        # Create command tree root node
        root_node = CommandNode(command)

        # Use queue for breadth-first traversal
        queue = deque([(root_node, 0)])  # (node, depth)

        # Set of processed commands to avoid duplicates
        processed_commands = set()

        # Print initial state
        print(f"\nStarting to process command tree, root node: {command}")
        print("=" * 50)

        # Breadth-first traversal to process all commands
        while queue:
            current_node, depth = queue.popleft()

            # Get full command path
            full_command = current_node.get_full_command()

            # Check if already processed
            if full_command in processed_commands:
                logger.info(f"Skipping already processed command: {full_command}")
                continue

            # Mark as processed
            processed_commands.add(full_command)

            # Process current command
            logger.info(f"Processing command: {full_command} (depth: {depth})")

            # Get help command
            help_command = self._get_help_command(full_command)

            # Execute command to get help information
            help_text, success = self.run_command(help_command)

            if not success:
                logger.error(
                    f"Failed to get help information for command '{full_command}'"
                )
                current_node.raw_help = help_text
                continue

            # Save raw help text
            current_node.raw_help = help_text

            # Save raw help text for each command
            self._save_raw_help_text(full_command, help_text, help_command)

            # Use LLM to parse help text
            logger.info(
                f"Starting to parse help text for command '{full_command}' using LLM"
            )
            parsed_help, raw_response = self.parser.parse_help_text(
                full_command, help_text
            )

            # Save parsed help information
            current_node.parsed_help = parsed_help

            # Generate and save man page for each command
            self._save_man_page(
                full_command,
                {
                    "command": full_command,
                    "parsed_help": parsed_help,
                    "raw_help": help_text,
                },
            )

            # If depth is not reached, process subcommands
            if depth < self.max_depth:
                # Get subcommand list
                subcommands = parsed_help.get("subcommands", [])
                logger.info(
                    f"Command '{full_command}' has {len(subcommands)} subcommands"
                )

                # Limit number of subcommands per level
                for i, subcmd_info in enumerate(
                    subcommands[: self.max_subcommands_per_level]
                ):
                    subcmd_name = subcmd_info.get("name", "")
                    subcmd_desc = subcmd_info.get("description", "")

                    if not subcmd_name:
                        continue

                    # Clean subcommand name (remove quotes, extra spaces, etc.)
                    subcmd_name = subcmd_name.strip().strip("\"'")

                    # Check if subcommand name starts with option marker
                    if subcmd_name.startswith("-"):
                        logger.warning(
                            f"Subcommand name starts with '-', might be an option: '{subcmd_name}'"
                        )
                        continue

                    # Process aliases (subcommands with spaces, like "container ls")
                    if " " in subcmd_name:
                        logger.info(f"Skipping alias: '{subcmd_name}'")
                        continue

                    # Add to command tree
                    child_node = current_node.add_child(subcmd_name, subcmd_desc)

                    # Verify subcommand existence
                    child_command = child_node.get_full_command()
                    if self._verify_subcommand_exists(child_command):
                        # Add subcommand to queue
                        queue.append((child_node, depth + 1))
                        logger.info(
                            f"Adding subcommand to queue: {child_command} (depth: {depth + 1})"
                        )
                    else:
                        # Remove invalid subcommand
                        logger.warning(
                            f"Subcommand does not exist, removing: {child_command}"
                        )
                        del current_node.children[subcmd_name]

                if len(subcommands) > self.max_subcommands_per_level:
                    logger.warning(
                        f"Command '{full_command}' has {len(subcommands)} subcommands, but only processing first {self.max_subcommands_per_level}"
                    )

        # Print complete command tree after processing
        print("\nCommand tree built:")
        self._print_command_tree(root_node)

        logger.info(
            f"Help information extraction for command '{command}' completed, processed {len(processed_commands)} commands"
        )

        # Convert command tree to dictionary structure
        result = self._command_tree_to_dict(root_node)
        return result

    def _command_tree_to_dict(self, node: CommandNode) -> Dict[str, Any]:
        """Convert command tree to dictionary structure"""
        result: Dict[str, Any] = {
            "command": node.name,
            "description": node.description,
            "raw_help": node.raw_help,
            "parsed_help": node.parsed_help,
            "exists": bool(node.raw_help),
            "subcommands": {},
        }

        # Recursively process subcommands
        for child_name, child_node in node.children.items():
            result["subcommands"][child_name] = self._command_tree_to_dict(child_node)

        return result

    def _print_command_tree(
        self, root_node: CommandNode, prefix: str = "", is_last: bool = True, depth: int = 0
    ) -> None:
        """Print command tree visualization"""
        if depth == 0:
            print("\nCurrent command tree:")
            print("=" * 50)

        # Print current node
        connector = "└── " if is_last else "├── "
        exists_mark = "✓"  # All nodes are verified to exist
        print(f"{prefix}{connector}{exists_mark} {root_node.name}")

        # Prepare next level prefix
        next_prefix = prefix + ("    " if is_last else "│   ")

        # Recursively print child nodes
        children = list(root_node.children.items())
        for i, (child_name, child_node) in enumerate(children):
            is_last_child = i == len(children) - 1
            self._print_command_tree(child_node, next_prefix, is_last_child, depth + 1)

        if depth == 0:
            print("=" * 50)

    def _print_command_tree_dict(self, command_info: Dict[str, Any], level: int = 0) -> None:
        """Print command tree structure"""
        cmd_name = command_info["command"]
        prefix = "  " * level

        # Print current command
        exists_mark = "✓" if command_info["exists"] else "✗"
        print(f"{prefix}{exists_mark} {cmd_name}")

        # Print subcommands
        for subcmd_name, subcmd_info in command_info.get("subcommands", {}).items():
            self._print_command_tree_dict(subcmd_info, level + 1)

    def run_command(self, cmd: List[str]) -> Tuple[str, bool]:
        """Execute command and get output, return (output content, success)"""
        cmd_str = " ".join(cmd)
        logger.info(f"Executing command: {cmd_str}")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=10,
            )
            output_length = len(result.stdout)
            success = result.returncode == 0

            if success:
                logger.info(
                    f"Command executed successfully, output length: {output_length} characters"
                )
            else:
                logger.warning(
                    f"Command execution failed, return code: {result.returncode}, output length: {output_length} characters"
                )

            return result.stdout, success
        except subprocess.TimeoutExpired:
            logger.error(f"Command execution timed out: {cmd_str}")
            return (
                f"Error: Command execution timed out after 10 seconds: {cmd_str}",
                False,
            )
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Command execution failed: {cmd_str}, error: {e}")
            return f"Error executing command: {e}", False

    def _verify_subcommand_exists(self, full_command: str) -> bool:
        """Verify subcommand existence by trying to execute"""
        logger.info(f"Verifying subcommand existence: {full_command}")

        # Try to execute subcommand's help option
        _, success = self.run_command([*full_command.split(), "--help"])

        if success:
            logger.info(f"Subcommand verification successful: {full_command}")
        else:
            logger.warning(
                f"Subcommand verification failed, might not exist: {full_command}"
            )

        return success

    def generate_man_page(self, command_info: Dict[str, Any]) -> str:
        """Generate man page format documentation"""
        logger.info(f"Generating man page for command '{command_info['command']}'")

        parsed_help = command_info["parsed_help"]
        command = command_info["command"]

        # Extract command name (without path)
        command_name = command.split()[-1]

        # Generate man page header
        man_page = f'.TH {command_name.upper()} 1 "{self._get_date()}" "CmdDocGen" "User Commands"\n'

        # Add name section
        man_page += f".SH NAME\n{command_name} \\- {parsed_help['description']}\n"

        # Add synopsis section
        man_page += f".SH SYNOPSIS\n.B {command}\n"
        if "usage" in parsed_help:
            man_page += f".PP\n{parsed_help['usage']}\n"

        # Add description
        man_page += f".SH DESCRIPTION\n{parsed_help['description']}\n"

        # Add arguments
        if "arguments" in parsed_help:
            man_page += ".SH ARGUMENTS\n"
            for arg in parsed_help["arguments"]:
                man_page += f".TP\n.B {arg['name']}\n{arg['description']}\n"

        # Add options
        if "options" in parsed_help:
            man_page += ".SH OPTIONS\n"
            for opt in parsed_help["options"]:
                man_page += f".TP\n.B {opt['name']}\n{opt['description']}\n"
                if "default" in opt:
                    man_page += f"Default: {opt['default']}\n"

        # Add examples
        if "examples" in parsed_help:
            man_page += ".SH EXAMPLES\n"
            for example in parsed_help["examples"]:
                man_page += f".PP\n.nf\n{example}\n.fi\n"

        # Add subcommands
        if "subcommands" in parsed_help or "subcommands" in command_info:
            man_page += ".SH SUBCOMMANDS\n"
            # Get subcommands from parsed help
            for subcmd in parsed_help.get("subcommands", []):
                man_page += f".TP\n.B {subcmd['name']}\n{subcmd['description']}\n"

            # Get more detailed information from processed subcommands
            for subcmd_name, subcmd_info in command_info.get("subcommands", {}).items():
                subcmd_desc = subcmd_info["parsed_help"]["description"]
                if subcmd_desc:
                    man_page += f".TP\n.B {subcmd_name}\n{subcmd_desc}\n"

        # Add author and reporting bugs sections
        man_page += ".SH AUTHOR\nAutomatically generated man page\n"
        man_page += (
            ".SH REPORTING BUGS\nPlease report bugs to the appropriate channel\n"
        )

        logger.info(f"Man page generation completed for command '{command}'")
        return man_page

    def save_outputs(self, command: str, command_info: Dict[str, Any]) -> None:
        """Save output files"""
        # Create safe filename
        safe_name = command.replace(" ", "_").replace("/", "_")
        logger.info(
            f"Saving output files for command '{command}', safe filename: {safe_name}"
        )

        # Save JSON structure
        json_path = os.path.join(self.output_dir, f"{safe_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(command_info, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON file: {json_path}")

        # Generate and save man page
        man_page = self.generate_man_page(command_info)
        man_path = os.path.join(self.output_dir, f"{safe_name}.man")
        with open(man_path, "w", encoding="utf-8") as f:
            f.write(man_page)
        logger.info(f"Saved man page file: {man_path}")

        # Save raw help text
        raw_path = os.path.join(self.output_dir, f"{safe_name}.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(command_info["raw_help"])
        logger.info(f"Saved raw help text: {raw_path}")

        # Print subcommand statistics
        subcommands = command_info["parsed_help"].get("subcommands", [])
        processed_subcommands = len(command_info.get("subcommands", {}))

        print("Saved output files:")
        print(f"  - JSON: {json_path}")
        print(f"  - Man Page: {man_path}")
        print(f"  - Raw Text: {raw_path}")
        print("Subcommand statistics:")
        print(f"  - Identified subcommands: {len(subcommands)}")
        print(f"  - Processed subcommands: {processed_subcommands}")

        print("\nSubcommand tree:")
        self._print_command_tree_dict(command_info)

    def _get_date(self) -> str:
        """Get current date for man page"""
        return datetime.now().strftime("%B %Y")

    def _save_raw_help_text(
        self, command: str, help_text: str, help_command: List[str]
    ) -> None:
        """Save command's raw help text"""
        # Create safe filename
        safe_name = command.replace(" ", "_").replace("/", "_")

        # Add command line before help text
        command_line = " ".join(help_command)
        help_text_with_command = f"# Command: {command_line}\n\n{help_text}"

        # Save raw help text
        raw_path = os.path.join(self.output_dir, f"{safe_name}.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(help_text_with_command)
        logger.info(f"Saved raw help text for command '{command}': {raw_path}")

    def _save_man_page(self, command: str, command_info: Dict[str, Any]) -> None:
        """Generate and save man page for command"""
        # Generate man page
        man_page = self.generate_man_page(command_info)

        # Create safe filename
        safe_name = command.replace(" ", "_").replace("/", "_")

        # Save man page
        man_path = os.path.join(self.output_dir, f"{safe_name}.man")
        with open(man_path, "w", encoding="utf-8") as f:
            f.write(man_page)
        logger.info(f"Saved man page for command '{command}': {man_path}")


def main() -> None:
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Universal command line help information extraction tool"
    )
    parser.add_argument("command", help="Command to extract help information from")
    parser.add_argument(
        "--output-dir", "-o", default="man_pages", help="Output directory"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["man", "json", "all"],
        default="all",
        help="Output format",
    )
    parser.add_argument(
        "--max-depth",
        "-d",
        type=int,
        default=1,
        help="Maximum recursion depth (default: 1)",
    )
    parser.add_argument(
        "--max-subcommands",
        "-m",
        type=int,
        default=150,
        help="Maximum subcommands per level (default: 150)",
    )
    parser.add_argument(
        "--help-format",
        choices=["default", "cliff"],
        default="default",
        help="Help command format, options: default (--help), cliff (help subcommand)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed log information"
    )

    args = parser.parse_args()

    # If verbose mode is specified, set log level to DEBUG
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose log mode enabled")

    logger.info(f"Starting to extract help information for command '{args.command}'...")
    print(f"Starting to extract help information for command '{args.command}'...")

    extractor = HelpExtractor(
        command=args.command,
        output_dir=args.output_dir,
        max_depth=args.max_depth,
        max_subcommands_per_level=args.max_subcommands,
        help_format=args.help_format,
    )

    # Record start time
    start_time = datetime.now()

    result = extractor.extract_help(args.command)

    # Record end time and calculate duration
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()

    extractor.save_outputs(args.command, result)

    # Print statistics
    print("Extraction completed!")
    print("Statistics:")
    print(f"  - Total duration: {elapsed_time:.2f} seconds")
    logger.info(f"Extraction completed! Total duration: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
