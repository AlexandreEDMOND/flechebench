# FlecheBench

FlecheBench is a research-oriented benchmark for evaluating how large language
models solve French "mots fleches" / arrowword-style puzzles.

The project is intentionally small at this stage. It does not yet generate real
puzzles, call LLM APIs, scrape websites, or evaluate full grids. The current
goal is to establish a clean Python foundation that can grow into a reproducible
benchmark.

## Planned Benchmark Modes

FlecheBench is planned around four evaluation settings:

1. **Clue-only solving**: the model receives a clue and the expected answer
   length.
2. **Pattern-aware solving**: the model also receives known letters, such as
   `C _ A _`.
3. **Full-grid solving**: the model receives a whole grid and all clues.
4. **Agentic solving**: the model can propose candidates, check consistency,
   and backtrack.

## Current Status

Implemented in this first version:

- Typed standard-library data structures for cells, entries, puzzles,
  predictions, and evaluation results.
- Basic validation for puzzle dimensions, entry positions, and answer lengths.
- Minimal word-level metrics.
- Prompt template helpers for the planned benchmark modes.
- A `BaseSolver` interface and `DummySolver` placeholder.
- Lightweight tests that run without external services.

Not implemented yet:

- Real LLM calls.
- Web scraping.
- Lexical resource import.
- Synthetic grid generation.
- Full-grid consistency checking.
- Agentic search or backtracking.

## Planned Model Inference

FlecheBench is expected to use `opencode go` for running model inference in a
future stage. No inference adapter is implemented yet, but the following model
identifiers are currently available through `opencode models` in the local
development environment.

Recommended initial candidates from the `opencode-go` provider:

- `opencode-go/deepseek-v4-flash`
- `opencode-go/deepseek-v4-pro`
- `opencode-go/glm-5.1`
- `opencode-go/glm-5.2`
- `opencode-go/kimi-k2.6`
- `opencode-go/kimi-k2.7-code`
- `opencode-go/mimo-v2.5`
- `opencode-go/mimo-v2.5-pro`
- `opencode-go/minimax-m2.7`
- `opencode-go/minimax-m3`
- `opencode-go/qwen3.6-plus`
- `opencode-go/qwen3.7-max`
- `opencode-go/qwen3.7-plus`

Other available `opencode` models:

- `opencode/big-pickle`
- `opencode/deepseek-v4-flash-free`
- `opencode/mimo-v2.5-free`
- `opencode/nemotron-3-ultra-free`
- `opencode/north-mini-code-free`

These names are environment-specific and should be refreshed before publishing
benchmark results.

## Development

This repository uses Python 3.11+ and currently has no runtime dependencies.

Run tests with:

```bash
uv run python -m unittest
```

The package uses a `src/` layout:

```text
src/flechebench/
  data/
  evaluation/
  generation/
  prompts/
  solvers/
```

See `ROADMAP.md` for the staged implementation plan.

## Le Parisien / RCI Jeux Scraping

Experimental tooling is available for scraping the public Le Parisien mots
fleches grids served by RCI Jeux.

Fetch the 10 latest published Force 1 grids:

```bash
uv run python scripts/scrape_leparisien.py --force 1 --count 10
```

The scraper writes one JSON file per grid plus an `index.json`:

```text
data/leparisien/force1/
  index.json
  mfleches_1_4002.json
  ...
```

Each JSON contains the raw RCI payload and a normalized representation:

- `grid`: original grid rows. Uppercase characters are answer letters;
  lowercase characters are clue cells.
- `clue_cells`: clue-cell coordinates and linked entry ids.
- `entries`: normalized clues, answers, direction, length, start coordinates,
  and source clue-cell metadata.

For a scale test across all four difficulty levels:

```bash
uv run python scripts/scrape_leparisien.py --all-forces --count 4000 --skip-missing
```

Existing JSON files are skipped by default, so interrupted scrapes can be
restarted without reprocessing completed grids. To force a fresh download:

```bash
uv run python scripts/scrape_leparisien.py --all-forces --count 4000 --skip-missing --redownload
```

By default, future-dated menu entries are ignored. To reproduce a scrape as of a
specific date:

```bash
uv run python scripts/scrape_leparisien.py --force 1 --count 10 --through-date 2026-07-05
```

To inspect a saved grid, open `viewer/leparisien_viewer.html` in a browser and
select one of the generated JSON files.
