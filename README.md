# EDAI

AI-powered CLI toolkit.

## Installation

```bash
pip install edai
```

Or install from source:

```bash
git clone https://github.com/your-org/edai.git
cd edai
pip install -e .
```

## Usage

```bash
# Show help
edai --help

# Say hello
edai hello
edai hello EDAI

# Check version
edai --version
```

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint & format
ruff check src tests
ruff format src tests

# Type check
mypy src
```

## License

GNU General Public License v3.0 or later.
