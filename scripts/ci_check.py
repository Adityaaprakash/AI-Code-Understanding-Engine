# scripts/ci_check.py
"""
Lightweight CI Verification Script for AI Code Understanding Engine.

Executes all project quality gates:
  1. Ruff lint check: `uv run ruff check .`
  2. Ruff formatting check: `uv run ruff format --check .`
  3. Mypy type check: `uv run mypy backend/`
  4. Pytest test suite with code coverage: `uv run pytest tests/ --cov=backend -v`

Exit code 0 indicates all quality gates passed.
Exit code 1 indicates a quality gate failure.
"""

import os
import subprocess
import sys


def run_step(title: str, command: list[str], env: dict[str, str] | None = None) -> None:
    """Execute a single quality gate command with clear output."""
    print("\n==================================================")
    print(f"RUNNING: {title}")
    print(f"COMMAND: {' '.join(command)}")
    print("==================================================")
    result = subprocess.run(command, env=env)
    if result.returncode != 0:
        print(f"\n❌ QUALITY GATE FAILED: {title} (exit code {result.returncode})")
        sys.exit(result.returncode)
    print(f"✅ PASSED: {title}")


def main() -> None:
    """Main entry point for local/CI test pipeline."""
    env = dict(os.environ)
    if "DATABASE_URL" not in env:
        env["DATABASE_URL"] = "postgresql+asyncpg://codelens:changeme@localhost:5432/codelens"

    run_step("Ruff Linting", ["uv", "run", "ruff", "check", "."], env=env)
    run_step("Ruff Format Check", ["uv", "run", "ruff", "format", "--check", "."], env=env)
    run_step("Mypy Type Analysis", ["uv", "run", "mypy", "backend/"], env=env)
    run_step(
        "Pytest Suite with Coverage",
        ["uv", "run", "pytest", "tests/", "--cov=backend", "--cov-report=term-missing", "-v"],
        env=env,
    )

    print("\n==================================================")
    print("🎉 ALL CI QUALITY GATES PASSED SUCCESSFULLY!")
    print("==================================================\n")


if __name__ == "__main__":
    main()
