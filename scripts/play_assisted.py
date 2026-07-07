"""Run the assisted mots fleches game loop on one saved puzzle."""

from __future__ import annotations

import argparse

from flechebench.game.assisted import (
    DEFAULT_GO_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_RUNNER,
    run_assisted_game,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--puzzle",
        default="data/leparisien/force1/mfleches_1_4012.json",
        help="Path to a saved Le Parisien puzzle JSON.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model id. Default is opencode-go/deepseek-v4-flash.",
    )
    parser.add_argument(
        "--runner",
        choices=["responses", "go", "opencode"],
        default=DEFAULT_RUNNER,
        help="Model runner: Zen Responses API, Go API, or local opencode CLI.",
    )
    parser.add_argument(
        "--api-endpoint",
        default=None,
        help="HTTP endpoint for responses/go runners.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Env file containing OPENCODE_API_KEY.",
    )
    parser.add_argument("--agent", default=None, help="Optional OpenCode agent name.")
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--max-passes", type=int, default=2)
    parser.add_argument(
        "--max-entries",
        type=int,
        default=None,
        help="Limit entries for a quick smoke run.",
    )
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per model call.")
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_GO_MAX_TOKENS,
        help="Max output tokens for the OpenCode Go API.",
    )
    args = parser.parse_args()

    run_assisted_game(
        args.puzzle,
        runner_name=args.runner,
        model=args.model,
        agent=args.agent,
        api_endpoint=args.api_endpoint,
        env_file=args.env_file,
        max_output_tokens=args.max_output_tokens,
        max_attempts_per_entry=args.max_attempts,
        max_passes=args.max_passes,
        max_entries=args.max_entries,
        timeout_seconds=args.timeout,
    )


if __name__ == "__main__":
    main()
