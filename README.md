# ByFlyPy

[![CI](https://github.com/anomalyco/ByFlyPy/actions/workflows/ci.yml/badge.svg)](https://github.com/anomalyco/ByFlyPy/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ByFlyPy is a Python console application for checking account balance and statistics from ByFly (Belarusian ISP) personal cabinet.

## Features

- Check account balance and tariff plan
- View traffic and time statistics
- Generate graphs (traffic and time allocation)
- Support for multiple accounts
- SQLite database for storing credentials
- Interactive and non-interactive modes

## Installation

### Requirements

- Python 3.9+
- uv (recommended) or pip

### Install from source

```bash
# Clone the repository
git clone https://github.com/peleccom/ByFlyPy.git
cd ByFlyPy

# Install with uv (recommended)
make install

# Or with pip
pip install -e ".[dev,plot]"
```

## Usage

### Command Line

```bash

# Check balance
byfly --phone +375331234567 --login 1721234

byfly --api-v1 -l 1721234

# Interactive mode
byfly.py -i

# Generate traffic graph
python byfly.py --api-v1 -l YOUR_LOGIN -p YOUR_PASSWORD -g traf

# Generate time graph
python byfly.py --api-v1 -l YOUR_LOGIN -p YOUR_PASSWORD -g time

# Save graph to file
python byfly.py --api-v1 -l YOUR_LOGIN -p YOUR_PASSWORD -g traf -s graph.png
```

### Python API

```python
from byflypy import ByFlyApiClient

# Create client instance
client = ByFlyApiClient("login", "password")

# Login
client.login()

# Get account info
info = user.get_account_info_page()
print(f"Balance: {info.balance}")
print(f"Plan: {info.plan}")

# Get statistics sessions
sessions = user.get_log()
for session in sessions:
    print(f"{session.begin} - {session.end}: {session.ingoing} MB")
```

## Development

```bash
# Run tests
make test

# Run linter
make check

# Install development dependencies
make install
```

## Database

Store credentials securely in SQLite database:

```bash
# Create database with interactive mode
python database.py users.db

# Use database with byfly
python byfly.py -l login --db users.db
```

## Project Structure

```
ByFlyPy/
├── src/
├── tests/          # pytest test suite
├── pyproject.toml    # Project configuration
├── Makefile          # Development commands
└── testdata/         # Test fixtures
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests and linter (`make test && make check`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- Original author: Александр
- Created: 28.10.2011
