# FlecheBench Roadmap

FlecheBench is intended to become a research benchmark for evaluating how
large language models solve French "mots fleches" / arrowword-style puzzles.
This first version only establishes the project foundation: data structures,
metric skeletons, prompt formatting, and placeholder solver interfaces.

## Stage 0: Project Foundation

Status: current stage.

- Define the package layout and Python project metadata.
- Establish typed core data structures for puzzles, entries, predictions, and
  evaluation results.
- Add minimal deterministic metrics for word-level evaluation.
- Add prompt template helpers without any model calls.
- Add a dummy solver for smoke tests and examples.
- Add import and behavior tests that can run without external services.

Success criteria:

- `uv run python -m unittest` passes.
- The package can be imported from `src/`.
- A valid puzzle can be constructed and evaluated with placeholder predictions.

## Stage 1: Data Contract and Fixtures

- Finalize a versioned JSONL format for puzzles, entries, clues, grid geometry,
  predictions, and evaluation outputs.
- Add serialization and deserialization helpers.
- Add small hand-written fixture puzzles for tests and examples.
- Decide how blocked cells, clue cells, and answer cells are represented for
  full-grid tasks.

Success criteria:

- Fixture puzzles round-trip through the data format.
- Invalid fixtures fail with clear validation errors.
- Evaluation can be reproduced from saved predictions only.

## Stage 2: Lexical Resources

- Add local importers for open French lexical resources such as Lexique and
  OpenLexicon.
- Normalize accents, casing, hyphenation, apostrophes, and inflections in a
  documented way.
- Build a small local word index keyed by length, pattern, and normalized form.
- Keep raw resources out of the repository unless their licenses and sizes make
  that appropriate.

Success criteria:

- Lexical data import is deterministic.
- The repository documents how to obtain source data.
- Tests use tiny synthetic fixtures, not large external files.

## Stage 3: Synthetic Puzzle Generation

- Implement simple grid construction for answer entries.
- Generate clue-only and pattern-aware tasks from synthetic entries.
- Add deterministic seeds and generation manifests.
- Track generation constraints and known limitations.

Success criteria:

- A seed and config reproduce the same generated benchmark split.
- Generated entries satisfy length and placement constraints.
- The generator can produce small smoke-test grids quickly.

## Stage 4: Benchmark Modes

Implement the benchmark modes incrementally:

- Clue-only solving: clue plus answer length.
- Pattern-aware solving: clue plus answer length plus known letters.
- Full-grid solving: whole grid plus all clues.
- Agentic solving: candidate generation, consistency checks, and backtracking.

Success criteria:

- Each mode has a stable input schema and output schema.
- Metrics are deterministic and mode-specific.
- Baseline solvers can run end-to-end without external LLM calls.

## Stage 5: Model Integrations

- Add model runner interfaces after the benchmark contract is stable.
- Keep providers optional and isolated behind adapters.
- Store prompts, raw outputs, parsed predictions, and run metadata.
- Avoid provider-specific assumptions in the benchmark core.

Success criteria:

- New providers can be added without changing puzzle data structures.
- Failed or malformed model outputs are recorded reproducibly.
- Runs can be compared by model, prompt version, and benchmark split.

## Stage 6: Analysis and Reporting

- Add aggregate reporting by mode, answer length, clue type, pattern density,
  and grid size.
- Add confidence intervals or bootstrap summaries where useful.
- Export compact tables suitable for papers and experiment logs.

Success criteria:

- Results are easy to inspect and reproduce.
- Reports include enough metadata to compare experiments fairly.
- The benchmark remains lightweight enough for local development.
