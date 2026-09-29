"""Regression tests for per-board fault isolation in all-boards search.

Covers finding E-02: a default ``search`` (board="all") used to abort the
whole search with ``Board '<name>' is not usable`` when a single board
could not be searched. The expected behavior now:

* an unusable board is skipped with a warning naming the board and why,
  and results from the remaining boards are returned (exit 0 on the CLI);
* when no board was usable the search raises ValueError listing every
  skipped board (exit 1 on the CLI);
* an explicit board choice still raises ``Board '<name>' is not usable``
  (unchanged per-board behavior).

Boards are stubbed in-memory; no network, no real API keys.
"""

from __future__ import annotations

import argparse
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import cli  # noqa: E402
import server  # noqa: E402


class _OkBoard:
    """Stub provider that always returns one job."""

    def __init__(self, name: str):
        self._name = name

    def search(self, query, location, limit=10, remote_only=False):
        return [
            {
                "id": f"{self._name}:1",
                "title": "Software Engineer",
                "company": "Example Co",
                "location": "Remote",
                "url": f"https://example.com/{self._name}/1",
                "board": self._name,
                "snippet": "",
            }
        ]


class _BrokenBoard:
    """Stub provider that is never usable (missing creds / stub)."""

    def __init__(self, reason: str):
        self._reason = reason

    def search(self, query, location, limit=10, remote_only=False):
        raise RuntimeError(self._reason)


class _RiskPolicyStub:
    """Fake risk policy that blocks the boards named in `blocked`."""

    def __init__(self, blocked: dict[str, str]):
        self._blocked = blocked

    def adjudicate_search(self, board, query=""):
        if board in self._blocked:
            return {"allowed": False, "reason": self._blocked[board]}
        return {"allowed": True, "reason": "", "tier": "test"}


_ADZUNA_REASON = "Adzuna needs ADZUNA_APP_ID and ADZUNA_APP_KEY env vars"


class SearchFaultIsolationTests(unittest.TestCase):
    def setUp(self):
        self._saved = (
            server.PROVIDERS,
            server.ACTIVE_BOARDS,
            server._risk_policy,
            server._compliance,
        )
        server._risk_policy = None
        server._compliance = None

    def tearDown(self):
        (
            server.PROVIDERS,
            server.ACTIVE_BOARDS,
            server._risk_policy,
            server._compliance,
        ) = self._saved

    def _use_boards(self, boards: dict):
        server.PROVIDERS = boards
        server.ACTIVE_BOARDS = set(boards)

    def test_all_search_skips_unusable_board(self):
        """One broken board: partial results returned, warning names it."""
        self._use_boards(
            {
                "greenhouse": _OkBoard("greenhouse"),
                "adzuna": _BrokenBoard(_ADZUNA_REASON),
            }
        )
        with self.assertLogs("veto-mcp", level="WARNING") as logs:
            jobs = server.search_jobs("software engineer", "Remote", board="all")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["board"], "greenhouse")
        warnings = "\n".join(logs.output)
        self.assertIn("'adzuna'", warnings)
        self.assertIn(_ADZUNA_REASON, warnings)

    def test_all_search_risk_blocked_board_skipped(self):
        """A risk-policy-blocked board is skipped for 'all' with a reason."""
        self._use_boards(
            {
                "greenhouse": _OkBoard("greenhouse"),
                "lever": _OkBoard("lever"),
            }
        )
        server._risk_policy = _RiskPolicyStub(
            {"lever": "daily search budget exhausted"}
        )
        with self.assertLogs("veto-mcp", level="WARNING"):
            jobs = server.search_jobs("software engineer", "Remote", board="all")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["board"], "greenhouse")

    def test_all_search_all_unusable_raises(self):
        """No usable board: ValueError lists every skipped board and why."""
        self._use_boards(
            {
                "adzuna": _BrokenBoard(_ADZUNA_REASON),
                "glassdoor": _BrokenBoard("stub board: not implemented"),
            }
        )
        with self.assertRaises(ValueError) as ctx:
            server.search_jobs("software engineer", "Remote", board="all")
        message = str(ctx.exception)
        self.assertIn("No board was usable", message)
        self.assertIn("adzuna", message)
        self.assertIn("glassdoor", message)
        self.assertIn(_ADZUNA_REASON, message)

    def test_explicit_board_still_raises(self):
        """Per-board search behavior is unchanged: unusable board raises."""
        self._use_boards({"adzuna": _BrokenBoard(_ADZUNA_REASON)})
        with self.assertRaises(ValueError) as ctx:
            server.search_jobs(
                "software engineer", "Remote", board="adzuna"
            )
        self.assertIn("Board 'adzuna' is not usable", str(ctx.exception))
        self.assertIn(_ADZUNA_REASON, str(ctx.exception))

    def test_explicit_board_risk_blocked_still_raises(self):
        self._use_boards({"lever": _OkBoard("lever")})
        server._risk_policy = _RiskPolicyStub(
            {"lever": "daily search budget exhausted"}
        )
        with self.assertRaises(ValueError) as ctx:
            server.search_jobs("software engineer", "Remote", board="lever")
        self.assertIn("Board 'lever' is not usable", str(ctx.exception))

    def _run_cli_search(self):
        args = argparse.Namespace(
            query="software engineer",
            location="",
            board="all",
            limit=3,
            remote=False,
            json=True,
        )
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.cmd_search(args)
        return code, out.getvalue(), err.getvalue()

    def test_cli_exit_zero_with_partial_results(self):
        self._use_boards(
            {
                "greenhouse": _OkBoard("greenhouse"),
                "adzuna": _BrokenBoard(_ADZUNA_REASON),
            }
        )
        code, out, err = self._run_cli_search()
        self.assertEqual(code, 0)
        self.assertNotIn("Error:", err)
        self.assertIn("greenhouse", out)

    def test_cli_exit_nonzero_when_no_board_usable(self):
        self._use_boards(
            {
                "adzuna": _BrokenBoard(_ADZUNA_REASON),
                "glassdoor": _BrokenBoard("stub board: not implemented"),
            }
        )
        code, out, err = self._run_cli_search()
        self.assertEqual(code, 1)
        self.assertIn("Error: No board was usable:", err)


if __name__ == "__main__":
    unittest.main()
