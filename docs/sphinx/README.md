# CPAU API Documentation

This directory contains the Sphinx documentation for the CPAU library.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -e ".[docs]"
```

This installs:
- `sphinx` - Documentation generator
- `sphinx-rtd-theme` - Read the Docs theme
- `sphinx-autodoc-typehints` - Better type hint rendering

### Build HTML Documentation

```bash
cd docs/sphinx
make html
```

The generated documentation will be in `_build/html/`.

### View the Documentation

Open the generated docs in your browser:

```bash
# macOS
open _build/html/index.html

# Linux
xdg-open _build/html/index.html

# Windows
start _build/html/index.html
```

Or use Python's built-in web server:

```bash
cd _build/html
python -m http.server 8000
# Then visit http://localhost:8000 in your browser
```

### Other Build Targets

```bash
make clean      # Remove built documentation
make html       # Build HTML documentation
make latexpdf   # Build PDF documentation (requires LaTeX)
make linkcheck  # Check all external links
make help       # Show all available targets
```

## Documentation Structure

- `conf.py` - Sphinx configuration
- `index.rst` - Main documentation page
- `api/` - API reference documentation (auto-generated from docstrings)

## Updating the Documentation

The API reference is automatically generated from the docstrings in the source code. To update:

1. Update the docstrings in `/src/cpau/*.py`
2. Rebuild the docs: `make clean && make html`
3. View the changes in your browser

## Publishing to Read the Docs

To publish your documentation on Read the Docs:

1. Create an account at https://readthedocs.org
2. Import your GitHub repository
3. Read the Docs will automatically build and host your documentation
4. Documentation will be available at `https://cpau.readthedocs.io`

Read the Docs automatically rebuilds documentation on every commit to your GitHub repository.
