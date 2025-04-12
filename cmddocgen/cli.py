#!/usr/bin/env python3
"""
CmdDocGen CLI - Command line interface for the CmdDocGen tool
A universal command line help information extraction tool powered by LLM for intelligent subcommand analysis
"""
import sys
import os
import subprocess

def main():
    """Entry point for the cmddocgen command"""
    # Get the path to cmd_doc_gen.py
    cmd_doc_gen_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cmd_doc_gen.py'))
    
    # Execute the script directly with the same arguments
    sys.exit(subprocess.call([sys.executable, cmd_doc_gen_path] + sys.argv[1:]))

if __name__ == "__main__":
    main()
