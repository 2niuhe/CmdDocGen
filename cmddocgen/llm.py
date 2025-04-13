#!/usr/bin/env python3
"""
CmdDocGen - LLM Integration Module

This module is responsible for interacting with language models (LLM) to parse command-line help text.
Supports configuring model parameters through environment variables.
"""

import json
import os
import re
import sys
import logging
import hashlib
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("CmdDocGen.LLM")

# Load environment variables from .env file
load_dotenv()


class LLMParser:
    """Class for parsing command-line help text using LLM"""

    def __init__(self) -> None:
        # Prefer to get configuration from environment variables, then from .env file
        logger.info("Initializing LLMParser...")

        self.base_url = os.getenv("LLM_BASE_URL")
        self.api_key = os.getenv("LLM_API_KEY")
        self.model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")  # Default to gpt-3.5-turbo
        self.temperature = float(os.getenv("LLM_TEMPERATURE", 0.2))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", 8192))

        logger.info(f"使用模型: {self.model}")
        logger.info(f"温度设置: {self.temperature}")
        logger.info(f"最大令牌数: {self.max_tokens}")

        if not self.api_key:
            print("\nError: Missing Required Configuration")
            print("-" * 50)
            print(
                "To use this tool, you need to configure the following environment variables:"
            )
            print("-" * 50)
            print("1. LLM_API_KEY - Your OpenAI API key")
            print("2. LLM_MODEL - The model to use (default: gpt-3.5-turbo)")
            print("3. LLM_BASE_URL - Optional: Your OpenAI API base URL")
            print("4. LLM_TEMPERATURE - Optional: Controls randomness (default: 0.2)")
            print("5. LLM_MAX_TOKENS - Optional: Maximum tokens (default: 8192)")
            print("-" * 50)
            print("You can set these variables in two ways:")
            print("1. Using environment variables:")
            print("   export LLM_API_KEY=your-api-key")
            print("2. Using a .env file:")
            print("   Create a .env file with these contents:")
            print("   LLM_API_KEY=your-api-key")
            print("   LLM_MODEL=gpt-3.5-turbo")
            print("-" * 50)
            print("Get your OpenAI API key from: https://platform.openai.com/api-keys")
            print("-" * 50)
            raise ValueError(
                "Required configuration missing. Please set up the environment variables as described above."
            )

        logger.info(f"Using model: {self.model}")
        logger.info(f"Temperature setting: {self.temperature}")
        logger.info(f"Maximum tokens: {self.max_tokens}")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info("LLMParser initialization complete")

        # Create cache directory
        self.cache_dir = os.path.join(os.getcwd(), "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Cache directory: {self.cache_dir}")

    def parse_help_text(
        self, command: str, help_text: str
    ) -> Tuple[Dict[str, Any], str]:
        """Parse command-line help text using LLM, returns (parsing result, raw response)"""
        # Check cache
        cache_key = self._get_cache_key(command, help_text)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Get parsing result for command '{command}' from cache")
            return cached_result["result"], cached_result["raw_response"]

        logger.info(f"Start parsing command '{command}' help text...")

        prompt = self._build_parsing_prompt(command, help_text)

        # For very long help text, may need to increase maximum tokens
        max_tokens = self.max_tokens
        if len(help_text) > 10000:  # For very long help text
            max_tokens = min(
                32768, self.max_tokens * 2
            )  # Increase tokens but not exceed model limit
            logger.info(
                f"Help text is very long, increase maximum tokens to: {max_tokens}"
            )

        logger.info("Send request to LLM...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional command-line document parser, skilled at structuring command-line help information into JSON format.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=max_tokens,
        )

        # Get raw response
        raw_response = response.choices[0].message.content
        if raw_response is None:
            raw_response = ""  # Ensure raw_response is always a string

        logger.info("Receive LLM response, start extracting JSON...")
        result = self._extract_json(raw_response)

        # Validate and log subcommand information
        self._validate_and_log_subcommands(command, result)

        # Save to cache
        self._save_to_cache(cache_key, {"result": result, "raw_response": raw_response})

        return result, raw_response

    def _build_parsing_prompt(self, command: str, help_text: str) -> str:
        """Build prompt for parsing help text"""
        # For very long help text, provide more specific guidance
        special_instructions = ""
        if len(help_text) > 10000:
            logger.info("Help text is very long, use special instructions...")
            special_instructions = """
This is a very complex command with extensive help text. Please focus on extracting:
1. The main command name and description
2. The basic usage syntax
3. The most important options (prioritize commonly used ones)
4. ALL available subcommands - it's critical to not miss any subcommands

It's okay to provide a simplified representation rather than trying to capture every detail.
"""

        # Enhanced subcommand extraction guidance
        subcommand_instructions = """
For subcommands extraction, follow these specific guidelines:
1. Look for sections labeled as "COMMANDS", "SUBCOMMANDS", "AVAILABLE COMMANDS", or similar.
2. Each subcommand should be a distinct command name (without spaces unless it's part of the name).
3. Exclude flags, options, or general descriptions that are not actual subcommands.
4. For each subcommand, extract both its name and a brief description.
5. EXTRACT ALL SUBCOMMANDS - do not skip or omit any subcommands listed in the help text.
6. Make sure each subcommand is properly formatted as a separate object in the JSON array.
7. Do not include the parent command name as part of the subcommand name.
8. Exclude examples, usage patterns, or other non-subcommand content.
9. If unsure whether something is a subcommand, check if it follows the command naming pattern.
10. It is CRITICAL to include ALL subcommands, even if there are many of them.
"""

        return f"""
Please carefully analyze the following command-line help text and extract structured information in JSON format.

Command: {command}

Help Text:
```
{help_text}
```
{special_instructions}
Please extract information according to the following rules:

1. Command Name: Extract the full command name, including subcommands.
2. Command Description: Extract the main function description of the command.
3. Usage: Extract the command usage syntax or format.
4. Positional Arguments: Extract all required or optional positional arguments, including their names, descriptions, and whether they are required.
5. Option Arguments: Extract all option arguments (starting with - or --), including short options, long options, descriptions, and default values.
6. Examples: Extract all usage examples.
7. Subcommand List: Extract ALL available subcommands and their brief descriptions. DO NOT OMIT ANY SUBCOMMANDS.

{subcommand_instructions}

Notes:
- For complex command-line help, please identify each section as accurately as possible.
- If some information does not exist, use an empty string or empty array.
- Make sure to correctly distinguish between positional arguments and option arguments.
- For options with multiple forms (such as -f and --file), merge them into a single option.
- If the help text contains multiple sections (such as COMMANDS, OPTIONS, etc.), correctly identify each section.
- If the help text format is non-standard, try to extract useful information.
- MOST IMPORTANTLY: Extract ALL subcommands listed in the help text, do not skip any.

Output in the following JSON format:
```json
{{
  "name": "command_name",
  "description": "command_description",
  "usage": "usage_syntax",
  "arguments": [
{{
  "name": "argument_name",
  "description": "argument_description",
  "required": true/false
}}
  ],
  "options": [
{{
  "name": "--option_name, -short_option",
  "description": "option_description",
  "default": "default_value(if_any)"
}}
  ],
  "examples": [
"example1",
"example2"
  ],
  "subcommands": [
{{
  "name": "subcommand_name",
  "description": "subcommand_description"
}}
  ]
}}
```

Please ensure the JSON format is correct and can be parsed. For very large command outputs, it's better to provide a complete but simplified structure than a truncated complex one.
"""

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        logger.info("Extract JSON from LLM response...")

        # Try to find JSON block
        json_pattern = r"```(?:json)?(.*?)```"
        matches = re.findall(json_pattern, content, re.DOTALL)

        if matches:
            # Use the first matched JSON block
            json_str = matches[0].strip()
            logger.info("Find JSON block, try to parse...")
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}")
                logger.info("Try to fix JSON...")
                return self._fix_and_parse_json(json_str)
        else:
            # If no JSON block found, try to parse the entire content
            logger.warning("No JSON block found, try to parse the entire content...")
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Parsing failed, try to fix JSON...")
                return self._fix_and_parse_json(content)

    def _fix_and_parse_json(self, json_str: str) -> Dict[str, Any]:
        """Try to fix and parse broken JSON string"""
        logger.info("Try to fix JSON string...")

        # Replace single quotes with double quotes
        fixed = json_str.replace("'", '"')

        # Remove trailing commas
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)

        # Try to fix missing quotes
        fixed = re.sub(r"([{,])\s*(\w+):", r'\1"\2":', fixed)

        # Handle truncated JSON - try to complete basic structure
        if fixed.count("{") > fixed.count("}"):
            fixed += "}"
        if fixed.count("[") > fixed.count("]"):
            fixed += "]"

        # Try to parse fixed JSON
        try:
            logger.info("Try to parse fixed JSON...")
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            logger.warning(f"Fixed JSON still cannot be parsed: {e}")
            # For very complex commands (like openstack), try to parse incrementally
            try:
                # Find the last complete object or array
                logger.info("Try to parse incrementally...")
                last_valid_pos = self._find_last_valid_json_position(fixed)
                if last_valid_pos > 0:
                    partial_json = fixed[:last_valid_pos]
                    # Ensure JSON structure is complete
                    if partial_json.strip().endswith((",", "[", "{")):
                        partial_json = partial_json.rstrip(",[ \t\n\r") + "}"
                    logger.info(f"Find valid JSON part, length: {last_valid_pos}")
                    return json.loads(partial_json)
            except Exception as e:
                logger.error(f"Incremental parsing failed: {e}")
                pass

            # If still cannot parse, return error information
            logger.error("Cannot parse JSON, return error information")
            return {
                "error": "Failed to parse LLM response as JSON",
                "raw_content": json_str[
                    :1000
                ],  # Increase display more content for debugging
            }

    def _find_last_valid_json_position(self, json_str: str) -> int:
        """Find the last valid position in JSON string"""
        logger.info("Find the last valid position in JSON string...")
        # Try to find the last complete object
        for i in range(len(json_str), 0, -1):
            try:
                # Try to add necessary closing brackets
                test_str = json_str[:i]
                open_braces = test_str.count("{")
                close_braces = test_str.count("}")
                open_brackets = test_str.count("[")
                close_brackets = test_str.count("]")

                # Add missing closing brackets
                test_str += "}" * (open_braces - close_braces)
                test_str += "]" * (open_brackets - close_brackets)

                json.loads(test_str)
                logger.info(f"Find valid position: {i}")
                return i
            except json.JSONDecodeError:
                continue
        logger.warning("No valid position found")
        return 0

    def _validate_and_log_subcommands(
        self, command: str, parsed_result: Dict[str, Any]
    ) -> None:
        """Validate and log subcommand information"""
        logger.info("Validate and log subcommand information...")

        # Check if parsing result contains subcommands
        subcommands = parsed_result.get("subcommands", [])

        if not subcommands:
            logger.info(
                f"Command '{command}' has no subcommands or failed to extract subcommands"
            )
            return

        # Validate subcommand format
        valid_subcommands = []
        invalid_subcommands = []

        for i, subcmd in enumerate(subcommands):
            if not isinstance(subcmd, dict):
                logger.warning(f"Subcommand #{i + 1} format is invalid: {subcmd}")
                invalid_subcommands.append(subcmd)
                continue

            name = subcmd.get("name", "")
            desc = subcmd.get("description", "")

            if not name:
                logger.warning(f"Subcommand #{i + 1} lacks name: {subcmd}")
                invalid_subcommands.append(subcmd)
                continue

            # # Check if subcommand name is valid
            # if " " in name and not name.startswith('"') and not name.startswith("'"):
            #     # Subcommand names usually do not contain spaces, unless quoted
            #     logger.warning(f"Subcommand name may be invalid: '{name}'")

            valid_subcommands.append(subcmd)
            logger.info(
                f"Subcommand: {name} - {desc[:50]}{'...' if len(desc) > 50 else ''}"
            )

        # Update parsing result's subcommand list
        if invalid_subcommands:
            logger.warning(f"Found {len(invalid_subcommands)} invalid subcommands")
            parsed_result["subcommands"] = valid_subcommands

        logger.info(f"Successfully extracted {len(valid_subcommands)} subcommands")

        # Print subcommand list summary
        if valid_subcommands:
            subcmd_names = [subcmd.get("name", "") for subcmd in valid_subcommands]
            logger.info(
                f"Subcommand list: {', '.join(subcmd_names[:10])}"
                + ("..." if len(subcmd_names) > 10 else "")
            )

            if len(subcmd_names) > 10:
                print(f"... and {len(subcmd_names) - 10} more subcommands not shown")
            print("-" * 50)
        else:
            print("\nNo subcommands found")
            print("-" * 50)

    def _get_cache_key(self, command: str, help_text: str) -> str:
        """Generate cache key"""
        # Use command and help text's hash value as cache key
        # Add model name and temperature to ensure different models or parameters do not conflict
        content = f"{command}|{help_text}|{self.model}|{self.temperature}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read cache file: {e}")
        return None

    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Save result to cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved result to cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save cache file: {e}")


def test_parser(command: str = "ls", help_option: str = "--help") -> Dict[str, Any]:
    """Test LLMParser functionality"""
    import subprocess

    parser = LLMParser()

    try:
        # Get command's help information
        cmd_parts = command.split()
        print(f"Execute command: {' '.join(cmd_parts + [help_option])}")
        help_text = subprocess.run(
            cmd_parts + [help_option],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        ).stdout

        print(f"\nGet command '{command}' help information...")
        print("-" * 50)
        print(f"Help text: {help_text}")
        print("-" * 50)

        # Parse help text
        result, raw_response = parser.parse_help_text(command, help_text)

        # Output raw response
        print("\nLLM raw response:")
        print("-" * 50)
        print(raw_response)
        print("-" * 50)

        # Output result
        print("\nParsing result:")
        print("-" * 50)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("-" * 50)

        # Print subcommand information
        subcommands = result.get("subcommands", [])
        if subcommands:
            print(f"\nFound {len(subcommands)} subcommands:")
            print("-" * 50)
            for i, subcmd in enumerate(subcommands[:100]):  # Limit display to first 100
                name = subcmd.get("name", "Unknown")
                desc = subcmd.get("description", "")
                print(
                    f"{i + 1}. {name}: {desc[:100]}{'...' if len(desc) > 100 else ''}"
                )

            if len(subcommands) > 100:
                print(f"... and {len(subcommands) - 100} more subcommands not shown")
            print("-" * 50)
        else:
            print("\nNo subcommands found")
            print("-" * 50)

        return result

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # If running this file directly, execute test
    if len(sys.argv) > 1:
        command = sys.argv[1]
        help_option = sys.argv[2] if len(sys.argv) > 2 else "--help"
        test_parser(command, help_option)
    else:
        print("Usage: python llm.py <command> [help option]")
        print("Example: python llm.py ls --help")
        print("Example: python llm.py git -h")
