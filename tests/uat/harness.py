"""Shared harness for automated UAT acceptance journeys.

Conventions every journey follows (no exceptions):
- Real surfaces only: real CLIs via subprocess, or the real in-process CLI
  dispatch (``cli.main``) with the same store-redirection seams the shipped
  E2E suite uses. Never mock the machinery under test.
- Hermetic: every state file lives under a per-test temp dir. The base
  class enforces this three ways: (1) HOME/XDG_*/TMPDIR/TEMP/TMP are
  assigned into the temp dir for every subprocess it spawns (an explicit
  caller override still wins); (2) a repo-tree tripwire snapshots ``git
  status`` in setUp and fails the test if the run added, removed, or
  changed anything in the repo tree — including content changes to paths
  that were already dirty before the test, caught by before/after content
  fingerprints — and fails CLOSED if ``git status`` itself is
  unavailable on either side, so an unverifiable tree never reports
  green; (3) subclasses MUST call ``super().setUp()`` / must not
  bypass ``tearDown``.
- Synthetic fixtures only, labeled ``SYNTHETIC`` in the data itself.
- Every test method maps to exactly one roadmap epic. Set EPIC_MAP as a
  CLASS attribute: ``method_name -> (epic_id, epic_title,
  acceptance_source)`` where acceptance_source names the repo material the
  assertions trace to (roadmap epic text, Proof of value, exit gate, or
  initiative README rule). The base class validates the mapping at class
  definition time — the *effective* map (nearest EPIC_MAP up the MRO,
  falling back to a module-level EPIC_MAP) is checked against *every*
  test method the unittest loader would collect (default ``test``
  prefix, not just ``test_``), and a concrete class with test methods
  must have a non-empty effective map — and the report runner
  re-validates the module-level map. There are no per-story acceptance
  criteria in the repo; journeys must not invent story-level criteria.
- Hygiene: failure output echoes subprocess stdout/stderr verbatim. CLIs
  must receive secrets (passphrases, tokens) via environment variables,
  never argv — but note that anything a CLI echoes to stdout WILL appear
  in failure logs, so journeys should avoid printing secrets.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
CLI = REPO / "cli.py"

# Environment variables that route CLIs at user data dirs. Defaulted into
# the per-test temp dir unless the caller explicitly overrides them.
# TMPDIR/TEMP/TMP are included so subprocess ``tempfile`` usage lands in
# the per-test temp dir too.
_HERMETIC_ENV_DEFAULTS = (
    "HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME",
    "XDG_STATE_HOME", "TMPDIR", "TEMP", "TMP",
)


def _porcelain_entries() -> tuple[list[tuple[str, str]], bool]:
    """``(status_xy, path)`` entries from ``git status --porcelain -z``.

    The ``-z`` form is NUL-terminated and never quotes paths, so entries
    with spaces or unicode survive parsing. Rename/copy entries consume
    the extra source-path part git emits.

    Returns ``(entries, git_ok)``; ``git_ok`` is False when git failed,
    so callers can fail closed instead of silently passing on an empty
    listing.
    """
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "-z"], cwd=str(REPO),
            capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return [], False
        entries: list[tuple[str, str]] = []
        parts = out.stdout.split("\0")
        i = 0
        while i < len(parts):
            part = parts[i]
            i += 1
            if not part:
                continue
            xy, path = part[:2], part[3:]
            entries.append((xy, path))
            if "R" in xy or "C" in xy:
                i += 1  # skip the rename/copy source-path part
        return entries, True
    except Exception:
        return [], False


def _fingerprint(path: Path) -> str | None:
    """Content fingerprint for one porcelain-listed path.

    Regular files hash their bytes; directories hash a manifest of
    (relative path, size, content hash) so added/removed/changed files
    inside an untracked directory are all caught. Files over 8 MiB
    contribute size+mtime instead of bytes (bounded cost). ``None`` when
    the path cannot be read.

    Python build artifacts (``__pycache__`` / ``*.pyc`` / ``*.pyo`` /
    ``.pytest_cache``) are excluded from directory manifests: concurrent
    test processes legitimately regenerate them, and they carry no
    test-state meaning.

    Each child is stat'ed exactly once (TOCTOU): the single stat result
    drives the regular-file check, the >8 MiB size branch, and the
    race marker folded in when the bytes vanish between stat and read.
    """
    try:
        if path.is_symlink():
            return "link:" + os.readlink(path)
        if path.is_file():
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return "f:" + h.hexdigest()
        if path.is_dir():
            h = hashlib.sha256()
            for child in sorted(path.rglob("*")):
                try:
                    st = os.lstat(child)
                except OSError:
                    continue  # unreadable: excluded from the manifest
                if not stat.S_ISREG(st.st_mode):
                    continue  # skips symlinks, dirs, sockets, ...
                rel = child.relative_to(path).as_posix()
                if ("/__pycache__/" in f"/{rel}" or rel.startswith("__pycache__/")
                        or child.suffix in (".pyc", ".pyo")
                        or rel == ".pytest_cache" or rel.startswith(".pytest_cache/")):
                    continue
                h.update(rel.encode("utf-8") + b"\0")
                try:
                    if st.st_size > 8 * 1024 * 1024:
                        h.update(f"big:{st.st_size}:{st.st_mtime_ns}".encode())
                    else:
                        h.update(child.read_bytes())
                except OSError:
                    # Raced: stat succeeded but the bytes are gone before
                    # the read. Fold the observed metadata in so the
                    # before/after comparison still notices the change.
                    h.update(f"gone:{st.st_size}:{st.st_mtime_ns}".encode())
                h.update(b"\0")
            return "d:" + h.hexdigest()
    except OSError:
        return None
    return None


def _tree_state() -> tuple[set[str], dict[str, str | None], bool]:
    """One ``git status`` call: ``(status lines, path fingerprints, git_ok)``.

    Tracked-dirty paths AND untracked paths are fingerprinted: a plain
    set comparison of status lines misses content changes to a path that
    was already dirty (`` M SECURITY.md`` looks identical before and
    after a test rewrites it). ``None`` marks an unreadable path.
    ``git_ok`` is False when git failed; the tripwire fails closed in
    that case rather than treating an empty listing as a clean tree.
    """
    entries, ok = _porcelain_entries()
    lines = {f"{xy} {path}" for xy, path in entries}
    fps = {path: _fingerprint(REPO / path) for _, path in entries}
    return lines, fps, ok


class JourneyCase(unittest.TestCase):
    """Base class for one initiative's acceptance journey.

    Subclasses set EPIC_MAP (class attribute) and implement one test method
    per epic (or per coherent epic slice). Method docstrings are
    plain-English "what this checks" lines surfaced verbatim in the
    operator report.
    """

    EPIC_MAP: dict[str, tuple[str, str, str]] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # Effective map: the nearest EPIC_MAP defined on the class or a
        # real parent (walking the MRO, stopping before JourneyCase's own
        # {} default). A class that explicitly sets EPIC_MAP = {} keeps
        # that empty map — it does NOT inherit a parent's map silently.
        # With no map in the MRO, fall back to a module-level EPIC_MAP
        # (the other supported pattern; run_uat.py merges it the same
        # way). Either way the full method set below is checked.
        mro_map: dict | None = None
        for base in cls.__mro__:
            if base is JourneyCase:
                break
            if "EPIC_MAP" in base.__dict__:
                mro_map = base.__dict__["EPIC_MAP"] or {}
                break
        if mro_map is None:
            module = sys.modules.get(cls.__module__)
            mro_map = (getattr(module, "EPIC_MAP", None) or {}) if module else {}
        effective_map = mro_map
        # Test methods: everything unittest's own loader would collect.
        # Its default prefix is "test" (not "test_"), so a method named
        # "testhelper" really runs and must be mapped too.
        prefix = unittest.TestLoader().testMethodPrefix
        test_methods = {
            n for n in dir(cls)
            if n.startswith(prefix) and callable(getattr(cls, n))
        }
        if not test_methods:
            return  # abstract/base class: nothing to check
        if not effective_map:
            raise TypeError(
                f"{cls.__name__}: has test methods but no non-empty "
                f"EPIC_MAP in scope; every test method must map to exactly "
                f"one roadmap epic in EPIC_MAP.")
        missing = sorted(test_methods - set(effective_map))
        extra = sorted(set(effective_map) - test_methods)
        problems = []
        if missing:
            problems.append(f"test methods without EPIC_MAP entries: {missing}")
        if extra:
            problems.append(f"EPIC_MAP entries with no test method: {extra}")
        if problems:
            raise TypeError(
                f"{cls.__name__}: every test method must map to exactly one "
                f"roadmap epic in EPIC_MAP. " + "; ".join(problems))

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="uat-")
        self.workdir = Path(self.tmp.name)
        self._tree_before, self._fps_before, self._git_ok_before = _tree_state()

    def tearDown(self) -> None:
        try:
            before = getattr(self, "_tree_before", None)
            if before is None:
                return  # setUp never snapshotted; its failure is the error
            after, fps_after, git_ok_after = _tree_state()
            if not self._git_ok_before or not git_ok_after:
                # Fail closed: without git status on both sides we cannot
                # verify repo cleanliness, so this journey must not report
                # green.
                which = ("setUp and tearDown"
                         if not self._git_ok_before and not git_ok_after
                         else "setUp" if not self._git_ok_before
                         else "tearDown")
                raise AssertionError(
                    "repo-tree tripwire: `git status` failed in "
                    f"{which}; repo cleanliness is unverifiable — "
                    "failing closed.")
            vanished = sorted(before - after)
            new = sorted(after - before)
            # A vanished status line whose path no longer fingerprints was
            # deleted; one that still fingerprints changed status (e.g.
            # staged, reverted, renamed). Both are repo-tree mutations.
            deleted = sorted(
                line for line in vanished if line[3:] not in fps_after)
            restated = sorted(
                line for line in vanished if line[3:] in fps_after)
            changed = sorted(
                path for path, fp in fps_after.items()
                if path in self._fps_before and fp != self._fps_before[path])
            problems = []
            if deleted:
                problems.append(
                    "deleted during the test:\n" + "\n".join(deleted))
            if restated:
                problems.append(
                    "status line disappeared (path still present under a "
                    "different status — e.g. staged or reverted):\n"
                    + "\n".join(restated))
            if new:
                problems.append(
                    "added or changed status lines:\n" + "\n".join(new))
            if changed:
                problems.append(
                    "content changed under an identical status line "
                    "(path was already dirty before the test):\n"
                    + "\n".join(changed))
            if problems:
                raise AssertionError(
                    "repo-tree tripwire: this test mutated files in the "
                    "repo tree (all state must live in the temp dir):\n"
                    + "\n".join(problems))
        finally:
            tmp = getattr(self, "tmp", None)
            if tmp is not None:
                tmp.cleanup()

    # -- process helpers -------------------------------------------------
    def _merged_env(self, extra: dict | None) -> dict:
        # HOME/XDG_*/TMPDIR/TEMP/TMP are ASSIGNED into the temp dir, not
        # defaulted: the ambient process always has a real HOME, so
        # setdefault would keep it and subprocess CLIs could read/write
        # the user's real home. An explicit caller override in `extra`
        # still wins.
        env = dict(os.environ)
        explicit = set(extra or ())
        for var in _HERMETIC_ENV_DEFAULTS:
            if var not in explicit:
                env[var] = str(self.workdir)
        if extra:
            env.update(extra)
        return env

    def run_cli(self, *args: str, env: dict | None = None,
                timeout: int = 180, cwd: Path | None = None
                ) -> subprocess.CompletedProcess:
        """Run the real top-level CLI: ``python cli.py <args>``."""
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=str(cwd or REPO), capture_output=True, text=True,
            timeout=timeout, env=self._merged_env(env),
        )

    def run_module(self, *args: str, env: dict | None = None,
                   timeout: int = 180, cwd: Path | None = None
                   ) -> subprocess.CompletedProcess:
        """Run a real module CLI: ``python -m <args>``."""
        return subprocess.run(
            [sys.executable, "-m", *args],
            cwd=str(cwd or REPO), capture_output=True, text=True,
            timeout=timeout, env=self._merged_env(env),
        )

    def run_script(self, script: Path, *args: str, env: dict | None = None,
                   timeout: int = 180, cwd: Path | None = None
                   ) -> subprocess.CompletedProcess:
        """Run a real script CLI: ``python <script> <args>``."""
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(cwd or REPO), capture_output=True, text=True,
            timeout=timeout, env=self._merged_env(env),
        )

    def assert_ok(self, proc: subprocess.CompletedProcess,
                  what: str) -> str:
        """Assert a CLI invocation succeeded; on failure show evidence."""
        self.assertEqual(
            proc.returncode, 0,
            f"{what} exited rc={proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n"
            f"--- stderr (tail) ---\n{proc.stderr[-3000:]}",
        )
        return proc.stdout

    # -- hermeticity ------------------------------------------------------
    @staticmethod
    @contextlib.contextmanager
    def block_network():
        """Fail closed for IN-PROCESS Python network access.

        Blocks ``socket.socket`` (including direct ``_socket.socket``),
        ``socket.create_connection``, and ``socket.getaddrinfo`` (DNS).
        Any attempt raises AssertionError. Restores everything on exit.

        Scope limits, stated plainly:
        - In-process only. Subprocess CLIs (run_cli/run_module/run_script)
          get fresh interpreters and are NOT affected; a journey that needs
          a subprocess CLI to stay local must use local-only commands and
          assert that itself.
        - Cannot intercept references bound before entry (e.g. code that
          did ``from _socket import socket`` at import time).
        """
        import _socket

        def _deny(*args, **kwargs):
            raise AssertionError(
                "network call attempted during a journey that must stay local")

        saved = {
            "socket.socket": socket.socket,
            "socket.create_connection": socket.create_connection,
            "socket.getaddrinfo": socket.getaddrinfo,
            "_socket.socket": _socket.socket,
        }
        socket.socket = _deny  # type: ignore[assignment]
        socket.create_connection = _deny  # type: ignore[assignment]
        socket.getaddrinfo = _deny  # type: ignore[assignment]
        _socket.socket = _deny  # type: ignore[assignment]
        try:
            yield
        finally:
            socket.socket = saved["socket.socket"]
            socket.create_connection = saved["socket.create_connection"]
            socket.getaddrinfo = saved["socket.getaddrinfo"]
            _socket.socket = saved["_socket.socket"]

    # -- synthetic fixtures ----------------------------------------------
    @staticmethod
    def synthetic_resume() -> str:
        return (
            "SYNTHETIC FIXTURE RESUME - not a real person\n"
            "Alex Example | alex.example@example.com | 555-010-2030\n\n"
            "Senior Backend Engineer, FixtureCorp - 2021-2024\n"
            "- Shipped Python microservices handling 1M requests per day.\n"
            "- Cut PostgreSQL query times by 50 percent with new indexes.\n"
            "- Led a team of 4 engineers on a Kubernetes migration.\n\n"
            "Skills: Python, PostgreSQL, Django, Kubernetes, Redis\n"
        )

    @staticmethod
    def synthetic_jd(title: str = "Senior Backend Engineer",
                     company: str = "HiringCorp") -> str:
        return (
            "SYNTHETIC FIXTURE JOB POSTING - not a real opening\n"
            f"{title} - {company} (New York, NY)\n"
            "We are hiring a Senior Backend Engineer. You must have 5+ years\n"
            "of Python experience and deep PostgreSQL knowledge. Kubernetes\n"
            "experience is a must-have. You will lead a small team.\n"
            "Nice to have: Redis, Django.\n"
        )
