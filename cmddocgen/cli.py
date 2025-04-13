#!/usr/bin/env python3
"""
CmdDocGen CLI - Command line interface for the CmdDocGen tool
A universal command line help information extraction tool powered by LLM for intelligent subcommand analysis
"""

import sys
import os
import subprocess

# Import the cmd_doc_gen module from the cmddocgen package
from cmddocgen.cmd_doc_gen import main as cmd_doc_gen_main


def main() -> None:
    """Entry point for the cmddocgen command"""
    # Execute the main function directly
    cmd_doc_gen_main()


if __name__ == "__main__":
    main()
