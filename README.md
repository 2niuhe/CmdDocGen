# CmdDocGen

<div align="center">
    <img src="https://raw.githubusercontent.com/2niuhe/CmdDocGen/main/assets/logo.png" width="200" alt="CmdDocGen Logo">
</div>

**Universal Command Line Help Information Extraction and Man Page Generation Tool**

*Powered by LLM for intelligent subcommand analysis*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/cmddocgen.svg)](https://badge.fury.io/py/cmddocgen)

</div>

## Overview

CmdDocGen is a universal command line help information extraction tool that can automatically generate standard man page format documentation. It leverages the power of Large Language Models (LLMs) to parse complex help text and supports recursive processing of subcommands.

## Key Features

- **Universal Support**: Works with any command line tool's help documentation
- **Standard Format**: Automatically generates man page format documentation
- **LLM-Powered Analysis**: Uses LLM to intelligently parse complex help text
- **Recursive Processing**: Supports recursive extraction of subcommands
- **Multiple Output Formats**: Generate man pages, JSON, or raw text outputs
- **Performance Optimization**: 
  - Caching mechanism for improved performance
  - "Raw" format option to skip LLM processing for deeper subcommands
- **Multiple LLM Providers**: Compatible with various LLM providers

## Installation

### From PyPI (Recommended)

```bash
pip install cmddocgen
```

### From Source

```bash
git clone https://github.com/2niuhe/CmdDocGen.git
cd CmdDocGen
pip install .
```

## Configuration

### Environment Variables

CmdDocGen uses environment variables for LLM configuration. Start by copying the example configuration file:

```bash
cp .env.example .env
```

Then edit the `.env` file with your settings:

```bash
# LLM API Base URL
LLM_BASE_URL=https://api.your-llm-provider.com/v1

# LLM API Key
LLM_API_KEY=your-api-key-here

# LLM Model Name
LLM_MODEL=gpt-4o-mini

# LLM Parameters
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=8096
```

### Example Configurations

#### Using AI Proxy

```bash
LLM_BASE_URL=https://api.aiproxy.io/v1
LLM_API_KEY=your-aiproxy-api-key
LLM_MODEL=gpt-4o-mini
```

#### Using DeepSeek

```bash
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=your-deepseek-api-key
LLM_MODEL=deepseek-chat
```

## Usage

### Basic Usage

```bash
cmddocgen COMMAND [OPTIONS]
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `COMMAND` | Command to extract help information from |
| `--output-dir`, `-o` | Output directory (default: "man_pages") |
| `--format`, `-f` | Output format: "man", "json", "raw", or "all" (default: "all") |
| `--max-depth`, `-d` | Maximum recursion depth (default: 1) |
| `--max-subcommands`, `-m` | Maximum subcommands per level (default: 150) |
| `--help-format` | Help command format: "default" (--help) or "cliff" (help subcommand) |
| `--verbose`, `-v` | Show detailed log information |

### Output Formats

- **all**: Generate all output formats (man page, JSON, and raw text)
- **man**: Generate only man page format
- **json**: Generate only JSON format
- **raw**: Generate only raw text format (skips LLM processing for subcommands at max depth)

### Examples

```bash
# Extract help information for the ls command
cmddocgen ls

# Extract help information for docker command and its subcommands
cmddocgen docker --max-depth 2

# Specify output directory
cmddocgen docker --output-dir "./docs"

# Use raw format for faster processing (only processes root command with LLM)
cmddocgen openstack --format raw --max-depth 1

# Use cliff help format for OpenStack commands
cmddocgen glance --help-format cliff --max-depth 2
```

## Performance Optimization

### Raw Format

The `--format raw` option provides a significant performance boost when you only need the raw help text. When using this format:

1. Only commands up to the specified `max-depth` are processed with LLM
2. Deeper subcommands are skipped for LLM processing
3. Only raw text files are saved (no JSON or man pages)

This is particularly useful for large command sets where you want to explore the command structure without the overhead of full LLM processing.

## Development

1. Clone the repository
2. Copy the configuration file
3. Create a virtual environment
4. Install dependencies

```bash
git clone https://github.com/2niuhe/CmdDocGen.git
cd CmdDocGen
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

MIT License

## Important Notes

- Make sure to properly configure the LLM-related environment variables
- Generated documentation will be saved in the specified output directory
- Cache files are stored in the `cache/` directory
- For large command sets with many subcommands, consider limiting the recursion depth or using the `--format raw` option