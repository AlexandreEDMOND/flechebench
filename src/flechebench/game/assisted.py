"""Assisted game loop for trying one puzzle with an LLM."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_RESPONSES_MODEL = "gpt-5.4-mini"
DEFAULT_GO_MODEL = "opencode-go/deepseek-v4-flash"
DEFAULT_MODEL = DEFAULT_GO_MODEL
DEFAULT_RUNNER = "go"
DEFAULT_RESPONSES_ENDPOINT = "https://opencode.ai/zen/v1/responses"
DEFAULT_GO_ENDPOINT = "https://opencode.ai/zen/go/v1/chat/completions"
DEFAULT_GO_MAX_TOKENS = 8192


class ModelRunner(Protocol):
    """Small interface used by the game loop."""

    def ask(self, prompt: str) -> str:
        """Return the model's raw text output."""


@dataclass
class OpencodeRunner:
    """Run prompts through `opencode run`."""

    model: str = DEFAULT_MODEL
    agent: str | None = None
    timeout_seconds: int = 120
    work_dir: str | None = None

    def ask(self, prompt: str) -> str:
        cmd = ["opencode", "run", "--model", self.model]
        if self.agent:
            cmd.extend(["--agent", self.agent])
        if self.work_dir:
            cmd.extend(["--dir", self.work_dir])
        cmd.append(prompt)

        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise RuntimeError(
                f"opencode failed with exit code {completed.returncode}: {stderr}"
            )
        return completed.stdout.strip()


@dataclass
class OpencodeGoApiRunner:
    """Call OpenCode Go through its OpenAI-compatible chat completions API."""

    model: str = DEFAULT_GO_MODEL
    api_key: str | None = None
    endpoint: str = DEFAULT_GO_ENDPOINT
    timeout_seconds: int = 60
    max_tokens: int = DEFAULT_GO_MAX_TOKENS
    last_metadata: dict[str, Any] = field(default_factory=dict)

    def ask(self, prompt: str) -> str:
        api_key = self.api_key or os.environ.get("OPENCODE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENCODE_API_KEY is required for --runner go. "
                "Use --runner opencode to call the local opencode CLI instead."
            )

        body = {
            "model": go_model_id(self.model),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu reponds uniquement avec un JSON strict, "
                        "sans explication."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        request = Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "flechebench/0.1",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenCode Go API failed with HTTP {error.code}: {detail}")
        except URLError as error:
            raise RuntimeError(f"OpenCode Go API request failed: {error.reason}")

        self.last_metadata = chat_completion_metadata(payload)
        return chat_completion_text(payload)


@dataclass
class OpencodeResponsesRunner:
    """Call OpenCode Zen through its OpenAI Responses-compatible API."""

    model: str = DEFAULT_RESPONSES_MODEL
    api_key: str | None = None
    endpoint: str = DEFAULT_RESPONSES_ENDPOINT
    timeout_seconds: int = 60

    def ask(self, prompt: str) -> str:
        api_key = self.api_key or os.environ.get("OPENCODE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENCODE_API_KEY is required for --runner responses. "
                "Use --runner opencode to call the local opencode CLI instead."
            )

        body = {
            "model": responses_model_id(self.model),
            "instructions": (
                "Tu reponds uniquement avec un JSON strict: "
                "{\"answer\":\"...\"}. Ne donne pas d'explication."
            ),
            "input": prompt,
            "temperature": 0,
            "max_output_tokens": 32,
        }
        request = Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "flechebench/0.1",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenCode Responses API failed with HTTP {error.code}: {detail}"
            )
        except URLError as error:
            raise RuntimeError(f"OpenCode Responses API request failed: {error.reason}")

        return responses_text(payload)


@dataclass
class Attempt:
    answer: str
    normalized: str
    status: str
    detail: str


@dataclass
class EntryState:
    attempts: list[Attempt] = field(default_factory=list)
    solved: bool = False


@dataclass
class AssistedGame:
    """Entry-by-entry assisted loop with immediate correctness feedback."""

    puzzle: dict[str, Any]
    runner: ModelRunner
    max_attempts_per_entry: int = 3
    max_passes: int = 2
    max_entries: int | None = None

    def __post_init__(self) -> None:
        self.entries = list(self.puzzle["entries"])
        if self.max_entries is not None:
            self.entries = self.entries[: self.max_entries]
        self.states = {entry["entry_id"]: EntryState() for entry in self.entries}
        self.letters: dict[tuple[int, int], str] = {}

    def run(self) -> dict[str, Any]:
        total = len(self.entries)
        print(f"Grille {self.puzzle['puzzle_id']} - {total} entrees")
        print(self.render_grid())

        for pass_index in range(1, self.max_passes + 1):
            solved_before = self.solved_count()
            attempted_this_pass: set[str] = set()
            print(f"\n=== Passe {pass_index}/{self.max_passes} ===")

            while True:
                candidates = [
                    entry
                    for entry in self.entries
                    if not self.states[entry["entry_id"]].solved
                    and entry["entry_id"] not in attempted_this_pass
                ]
                if not candidates:
                    break

                entry = max(candidates, key=self.completion_rate)
                attempted_this_pass.add(entry["entry_id"])
                self.try_entry(entry, pass_index)

            solved_after = self.solved_count()
            if solved_after == total:
                break
            if solved_after == solved_before:
                print("\nAucune progression sur cette passe.")
                break

        summary = self.summary()
        print("\n=== Resultat ===")
        print(
            f"Resolues: {summary['solved']}/{summary['total']} | "
            f"Echouees: {summary['failed']} | Restantes: {summary['remaining']}"
        )
        print(self.render_grid())
        return summary

    def try_entry(self, entry: dict[str, Any], pass_index: int) -> None:
        entry_id = entry["entry_id"]
        state = self.states[entry_id]
        attempts_this_pass = 0

        while attempts_this_pass < self.max_attempts_per_entry and not state.solved:
            attempts_this_pass += 1
            attempt_number = len(state.attempts) + 1
            known = self.known_letters_count(entry)
            print(
                f"\nEntree {entry_id} - {entry['clue']} - "
                f"{entry['length']} lettres - passe {pass_index}"
            )
            print(f"Motif: {self.pattern_for_entry(entry)}")
            print(f"Completion: {known}/{entry['length']} ({self.completion_rate(entry):.0%})")
            print(self.render_grid(current_entry_id=entry_id))

            prompt = self.render_prompt(entry)
            raw = self.runner.ask(prompt)
            if not raw:
                metadata = getattr(self.runner, "last_metadata", None)
                if metadata:
                    print(
                        "Reponse API vide: "
                        f"finish_reason={metadata.get('finish_reason')}, "
                        f"completion_tokens={metadata.get('completion_tokens')}, "
                        f"reasoning_tokens={metadata.get('reasoning_tokens')}"
                    )
            answer = extract_answer(raw)
            normalized = normalize_answer(answer)
            attempt = self.evaluate_attempt(entry, answer, normalized)
            state.attempts.append(attempt)

            print(f"Proposition {attempt_number}: {answer!r} -> {normalized!r}")
            print(f"Resultat: {attempt.status}. {attempt.detail}")

            if attempt.status == "correct":
                self.place_entry(entry, normalized)
                state.solved = True
                print(self.render_progress())
                print(self.render_grid())
                return

        if not state.solved:
            print(
                f"Entree {entry_id} non resolue sur cette passe "
                f"apres {attempts_this_pass} tentatives."
            )

    def render_prompt(self, entry: dict[str, Any]) -> str:
        previous = self.states[entry["entry_id"]].attempts
        lines = [
            "Tu joues aux mots fleches en mode assiste.",
            "Reponds uniquement avec un JSON strict: {\"answer\":\"...\"}.",
            "Ne donne pas d'explication.",
            "",
            f"Grille: {self.puzzle['puzzle_id']}",
            f"Entree: {entry['entry_id']}",
            f"Definition: {entry['clue']}",
            f"Longueur attendue: {entry['length']}",
            f"Direction: {entry['direction']}",
            f"Motif connu: {self.pattern_for_entry(entry)}",
        ]
        if previous:
            lines.extend(["", "Tentatives precedentes et feedback:"])
            for attempt in previous:
                lines.append(f"- {attempt.normalized}: {attempt.status}. {attempt.detail}")
        return "\n".join(lines)

    def evaluate_attempt(self, entry: dict[str, Any], answer: str, normalized: str) -> Attempt:
        expected = normalize_answer(entry["answer"])
        if not normalized:
            return Attempt(answer, normalized, "invalid", "Reponse vide ou illisible.")
        if len(normalized) != entry["length"]:
            return Attempt(
                answer,
                normalized,
                "invalid",
                f"Longueur invalide: attendu {entry['length']}, recu {len(normalized)}.",
            )
        conflict = self.first_conflict(entry, normalized)
        if conflict:
            row, column, known, proposed = conflict
            return Attempt(
                answer,
                normalized,
                "invalid",
                f"Conflit grille en ({row},{column}): attendu {known}, recu {proposed}.",
            )
        if normalized != expected:
            return Attempt(answer, normalized, "incorrect", "Mauvaise reponse.")
        return Attempt(answer, normalized, "correct", "Bonne reponse.")

    def first_conflict(self, entry: dict[str, Any], answer: str) -> tuple[int, int, str, str] | None:
        for (row, column), proposed in zip(entry_positions(entry), answer):
            known = self.letters.get((row, column))
            if known is not None and known != proposed:
                return row, column, known, proposed
        return None

    def place_entry(self, entry: dict[str, Any], answer: str) -> None:
        for position, letter in zip(entry_positions(entry), answer):
            self.letters[position] = letter

    def pattern_for_entry(self, entry: dict[str, Any]) -> str:
        chars = [self.letters.get(position, "_") for position in entry_positions(entry)]
        return " ".join(chars)

    def known_letters_count(self, entry: dict[str, Any]) -> int:
        return sum(1 for position in entry_positions(entry) if position in self.letters)

    def completion_rate(self, entry: dict[str, Any]) -> float:
        if entry["length"] == 0:
            return 0.0
        return self.known_letters_count(entry) / entry["length"]

    def render_progress(self) -> str:
        return f"Avancement: {self.solved_count()}/{len(self.entries)} resolues"

    def render_grid(self, current_entry_id: str | None = None) -> str:
        clue_cells = {(cell["row"], cell["column"]) for cell in self.puzzle["clue_cells"]}
        answer_cells = {position for entry in self.entries for position in entry_positions(entry)}
        current_cells: set[tuple[int, int]] = set()
        if current_entry_id is not None:
            current_entry = next(
                entry for entry in self.entries if entry["entry_id"] == current_entry_id
            )
            current_cells = set(entry_positions(current_entry))

        rows = []
        for row in range(self.puzzle["height"]):
            cells = []
            for column in range(self.puzzle["width"]):
                position = (row, column)
                if position in clue_cells:
                    value = "#"
                elif position in self.letters:
                    value = self.letters[position]
                elif position in current_cells:
                    value = "?"
                elif position in answer_cells:
                    value = "."
                else:
                    value = " "
                cells.append(value)
            rows.append(" ".join(cells))
        return "\n".join(rows)

    def solved_count(self) -> int:
        return sum(1 for state in self.states.values() if state.solved)

    def summary(self) -> dict[str, int]:
        solved = self.solved_count()
        total = len(self.entries)
        failed = total - solved
        return {
            "total": total,
            "solved": solved,
            "failed": failed,
            "remaining": 0,
        }


def entry_positions(entry: dict[str, Any]) -> list[tuple[int, int]]:
    row = entry["start"]["row"]
    column = entry["start"]["column"]
    positions = []
    for index in range(entry["length"]):
        if entry["direction"] == "across":
            positions.append((row, column + index))
        else:
            positions.append((row + index, column))
    return positions


def normalize_answer(value: str) -> str:
    value = value.strip().replace("Œ", "OE").replace("œ", "oe")
    decomposed = unicodedata.normalize("NFD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return "".join(char for char in without_accents.upper() if "A" <= char <= "Z")


def extract_answer(raw_output: str) -> str:
    parsed = _parse_json_object(raw_output.strip())
    if parsed and isinstance(parsed.get("answer"), str):
        return parsed["answer"]

    for line in raw_output.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate
    return ""


def _parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def load_puzzle(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_env_file(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def go_model_id(model: str) -> str:
    return model.removeprefix("opencode-go/")


def responses_model_id(model: str) -> str:
    return model.removeprefix("opencode/")


def chat_completion_text(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"Unexpected OpenCode Go API response: {payload}") from error
    if not isinstance(content, str):
        raise RuntimeError(f"Unexpected OpenCode Go message content: {content!r}")
    return content.strip()


def chat_completion_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    choice = payload.get("choices", [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    usage = payload.get("usage", {})
    details = usage.get("completion_tokens_details", {})
    return {
        "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
        "content_length": len(message.get("content") or "") if isinstance(message, dict) else 0,
        "reasoning_length": (
            len(message.get("reasoning_content") or "") if isinstance(message, dict) else 0
        ),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
    }


def responses_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text.strip()

    output = payload.get("output")
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
        if parts:
            return "".join(parts).strip()

    raise RuntimeError(f"Unexpected OpenCode Responses API response: {payload}")


def run_assisted_game(
    puzzle_path: str | Path,
    *,
    runner_name: str = DEFAULT_RUNNER,
    model: str = DEFAULT_MODEL,
    agent: str | None = None,
    api_key: str | None = None,
    api_endpoint: str | None = None,
    env_file: str | Path | None = ".env",
    max_output_tokens: int = DEFAULT_GO_MAX_TOKENS,
    max_attempts_per_entry: int = 3,
    max_passes: int = 2,
    max_entries: int | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    if env_file is not None:
        load_env_file(env_file)

    puzzle = load_puzzle(puzzle_path)
    if runner_name == "responses":
        if api_endpoint is None:
            api_endpoint = DEFAULT_RESPONSES_ENDPOINT
        runner = OpencodeResponsesRunner(
            model=model,
            api_key=api_key,
            endpoint=api_endpoint,
            timeout_seconds=timeout_seconds,
            max_tokens=max_output_tokens,
        )
        game = AssistedGame(
            puzzle=puzzle,
            runner=runner,
            max_attempts_per_entry=max_attempts_per_entry,
            max_passes=max_passes,
            max_entries=max_entries,
        )
        return game.run()

    if runner_name == "go":
        if model == DEFAULT_RESPONSES_MODEL:
            model = DEFAULT_GO_MODEL
        if api_endpoint is None:
            api_endpoint = DEFAULT_GO_ENDPOINT
        runner = OpencodeGoApiRunner(
            model=model,
            api_key=api_key,
            endpoint=api_endpoint,
            timeout_seconds=timeout_seconds,
        )
        game = AssistedGame(
            puzzle=puzzle,
            runner=runner,
            max_attempts_per_entry=max_attempts_per_entry,
            max_passes=max_passes,
            max_entries=max_entries,
        )
        return game.run()

    if runner_name != "opencode":
        raise ValueError("runner_name must be 'responses', 'go', or 'opencode'")

    with tempfile.TemporaryDirectory(prefix="flechebench-opencode-") as work_dir:
        runner = OpencodeRunner(
            model=model,
            agent=agent,
            timeout_seconds=timeout_seconds,
            work_dir=work_dir,
        )
        game = AssistedGame(
            puzzle=puzzle,
            runner=runner,
            max_attempts_per_entry=max_attempts_per_entry,
            max_passes=max_passes,
            max_entries=max_entries,
        )
        return game.run()


def run_with_temp_opencode_dir(
    puzzle_path: str | Path,
    *,
    model: str = DEFAULT_MODEL,
    agent: str | None = None,
    max_attempts_per_entry: int = 3,
    max_passes: int = 2,
    max_entries: int | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    return run_assisted_game(
        puzzle_path,
        runner_name="opencode",
        model=model,
        agent=agent,
        max_attempts_per_entry=max_attempts_per_entry,
        max_passes=max_passes,
        max_entries=max_entries,
        timeout_seconds=timeout_seconds,
    )
