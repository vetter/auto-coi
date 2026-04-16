# Automated COA / COI List Generator

> *Because there are better ways to use your time than hunting and pecking your COI list...*

A lightweight command-line tool that generates **Collaborators & Other Affiliations (COA)** / **Conflicts of Interest (COI)** lists for **NSF** and **DOE** proposals directly from [OpenAlex](https://openalex.org). Give it one or more ORCID IDs and it returns a clean, deduplicated, NSF/DOE-style CSV of recent co-authors — no more scraping CVs, guessing affiliations, or reconciling half a dozen BibTeX files the night before a deadline.

## Features

- **ORCID-driven** — identifies authors unambiguously, avoiding name collisions.
- **NSF/DOE-compliant lookback** — defaults to 48 months, fully configurable.
- **Multi-PI support** — pass multiple ORCIDs in a single run to build a team list.
- **Automatic deduplication** — cross-author instances collapsed by ORCID (or name + affiliation fallback).
- **Affiliation hygiene** — warns on missing affiliations and flags co-authors whose affiliation has changed across the window.
- **Acronym expansion** — common U.S. national-lab and university acronyms (ORNL, ANL, LBNL, MIT, …) are expanded to full names as expected by reviewers.
- **Polite-pool friendly** — pass your email to get faster, higher-quota OpenAlex responses.
- **No API keys, no accounts** — just ORCIDs and a network connection.

## Installation

Requires Python 3.8+. Pick whichever workflow you prefer — classic `pip` or the faster [`uv`](https://docs.astral.sh/uv/).

### Option A — pip / venv

```bash
git clone https://github.com/vetter/auto-coi.git
cd auto-coi
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Option B — uv (recommended)

```bash
git clone https://github.com/vetter/auto-coi.git
cd auto-coi
uv venv
uv pip install -r requirements.txt
```

### Option C — uv run (zero-install, one-liner)

`uv run` will create an ephemeral environment on the fly, so you don't even need to clone first:

```bash
uv run --with pandas --with requests --with python-dateutil \
    coa_generator.py 0000-0002-2449-6720 -e you@university.edu
```

## Usage

```bash
python coa_generator.py <ORCID> [<ORCID> ...] [options]
```

### Quick example

With `pip` / activated venv:

```bash
python coa_generator.py 0000-0002-2449-6720 -e you@university.edu
```

With `uv` (no activation needed):

```bash
uv run coa_generator.py 0000-0002-2449-6720 -e you@university.edu
```

### Multi-PI team list

```bash
python coa_generator.py 0000-0002-2449-6720 0000-0001-2345-6789 \
    -m 48 \
    -o team_coi.csv \
    -e you@university.edu
```

Or with `uv`:

```bash
uv run coa_generator.py 0000-0002-2449-6720 0000-0001-2345-6789 \
    -m 48 \
    -o team_coi.csv \
    -e you@university.edu
```

### Options

| Flag | Description | Default |
| --- | --- | --- |
| `orcids` | One or more ORCID IDs (positional, required) | — |
| `-o`, `--output` | Output CSV filename | `<LastName>-<YYYY-MM-DD>-CoAuthors.csv` |
| `-m`, `--months` | Lookback window in months | `48` |
| `-e`, `--email` | Email for OpenAlex polite pool | none |
| `-v`, `--verbose` | Verbose progress / debug output | off |
| `--no-dedup` | Keep every authorship instance | off |

## Output

A CSV with the columns expected by NSF/DOE COA templates:

- Senior/key person linked to
- First Name
- Last Name
- ORCiD
- Institutional affiliation
- Reason (`co-author`)
- Year last applied
- COMMENT (auto-notes, e.g. expanded acronyms or missing affiliations)

Rows are sorted by last name and ready to paste into the standard NSF/DOE table.

## Data Hygiene Warnings

During each run the tool prints warnings to help you catch issues before a program officer does:

- **Missing affiliations** — flagged per author with the year of the offending publication.
- **Affiliation changes** (ORCID-matched) — auto-resolved to the most recent affiliation, but reported.
- **Potential name conflicts** (no ORCID) — all variants are kept for manual review rather than silently merged.

## Caveats

- Coverage is only as good as [OpenAlex](https://openalex.org). Pubs that aren't indexed won't appear — check your own list before submitting.
- Affiliation data can lag reality; always eyeball the CSV before handing it to sponsored programs.
- The acronym table lives in the script — feel free to extend `ACRONYMS` for your institution.

## Credit

Jeffrey S. Vetter / Advanced Computing Systems Research

## License

[MIT](LICENSE) © Jeffrey S. Vetter
