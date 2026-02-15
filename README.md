# Python CLI Package Boilerplate (PDM + Typer)

A modern Python CLI package boilerplate using PDM for package management and Typer for CLI functionality. The package is organized into clearly separated submodules (e.g., `my_package/cli/`, `my_package/utils/`) and follows the coding rules in `docs/python-coding-standards.md` with Google style docstrings.

## Versions

**Current version**: 1.0.0

## Table of Contents

- [Versions](#versions)
- [Badges](#badges)
- [Repository Contents](#repository-contents)
- [Getting Started (PDM)](#getting-started-pdm)
- [License](#license)
- [Contributing](#contributing)

## Badges

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Repository Contents

- **Python Coding Standards**: see `docs/python-coding-standards.md`.
- **Package**: `my_package/` with submodules:
  - `my_package/cli/` Typer app and commands
  - `my_package/utils/` reusable helpers
  - `my_package/__about__.py` version metadata
  - `my_package/__init__.py` top-level exports
- **Tests**: `tests/`
- **Build/Deps**: `pyproject.toml` managed by PDM

## Getting Started (PDM)

Prerequisite: install [PDM](https://pdm.fming.dev)

```bash
python3 -m pip install -U pdm
```

Install dependencies and set up a local venv:

```bash
pdm install
```

Run the CLI (installed console script):

```bash
pdm run my-package --help
pdm run my-package --version
pdm run my-package hello Alice
```

Run tests:

```bash
pdm run pytest
```

Code quality:

```bash
pdm run ruff check .
pdm run black .
```

Notes:

- Legacy files like `setup.py` and `requirements.txt` are no longer used with PDM.
- Entry point is defined in `pyproject.toml` under `[project.scripts]` as `my-package`.

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE) for more information.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
