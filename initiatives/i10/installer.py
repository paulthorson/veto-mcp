#!/usr/bin/env python3
"""One-command installer for Veto (Epic 1).

``python3 initiatives/i10/installer.py install`` performs:

1. Environment checks — Python version, pip, disk space, writable data
   dir, optional network reachability.
2. Dependency setup — creates a virtualenv (default
   ``~/.local/share/veto/venv``), installs ``requirements.txt`` plus the
   packaging extras, optionally installs the Playwright Chromium browser.
3. Guided onboarding — name/email, data-directory choice, privacy
   defaults (local-only sync), writes the install record and a
   ``profile-v1``-stamped starter profile.
4. Wiring — prints the exact commands to run the CLI, web UI, and MCP
   server; writes a ``veto`` launcher shim.

``python3 initiatives/i10/installer.py uninstall [--purge-data]`` removes
the venv and install record; data is removed ONLY with ``--purge-data``
(and an explicit typed confirmation), so uninstall never destroys a
user's job-search history by accident.

Non-interactive use: pass ``--yes`` to accept defaults (CI / scripted
installs). Every step is idempotent — re-running ``install`` repairs a
partial install.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root
PACKAGE_DIR = Path(__file__).resolve().parent
PACKAGE_VERSION = "0.1.0"

INSTALL_ROOT = Path.home() / ".local" / "share" / "veto"
INSTALL_RECORD = INSTALL_ROOT / "install.json"
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "veto" / "data"
MIN_PYTHON = (3, 10)
MIN_DISK_BYTES = 500 * 1024 * 1024  # 500 MB


# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    severity: str = "error"  # "error" | "warning"
    fix: str = ""


def check_environment() -> list[Check]:
    """Run every environment check. ``ok`` overall means no error-severity
    check failed; warnings never block the install."""
    checks: list[Check] = []

    py = sys.version_info
    checks.append(
        Check(
            "python",
            (py.major, py.minor) >= MIN_PYTHON,
            f"Python {py.major}.{py.minor}.{py.micro}",
            fix=f"Install Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
        )
    )

    pip_ok = shutil.which("pip3") or shutil.which("pip")
    checks.append(
        Check(
            "pip",
            bool(pip_ok),
            f"pip at {pip_ok}" if pip_ok else "pip not found on PATH",
            fix="Install pip (python3 -m ensurepip)",
        )
    )

    try:
        usage = shutil.disk_usage(str(Path.home()))
        checks.append(
            Check(
                "disk",
                usage.free >= MIN_DISK_BYTES,
                f"{usage.free / 1024**3:.1f} GB free",
                fix="Free at least 500 MB of disk space",
            )
        )
    except OSError as exc:
        checks.append(Check("disk", False, f"could not query disk: {exc}"))

    try:
        probe = INSTALL_ROOT / ".write-probe"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        writable = True
        detail = f"{INSTALL_ROOT} is writable"
    except OSError as exc:
        writable = False
        detail = f"{INSTALL_ROOT} not writable: {exc}"
    checks.append(
        Check(
            "install-dir",
            writable,
            detail,
            fix="Run as a user who can write to ~/.local/share",
        )
    )

    venv_mod = True
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", "--help"],
            capture_output=True,
            check=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        venv_mod = False
    checks.append(
        Check(
            "venv",
            venv_mod,
            "python -m venv available" if venv_mod else "venv module missing",
            severity="warning",
            fix="Install python3-venv (apt) / python3 (brew)",
        )
    )

    return checks


def environment_ok(checks: list[Check]) -> bool:
    return all(c.ok for c in checks if c.severity == "error")


def print_checks(checks: list[Check]) -> None:
    for c in checks:
        mark = "✓" if c.ok else ("!" if c.severity == "warning" else "✗")
        print(f"  [{mark}] {c.name}: {c.detail}")
        if not c.ok and c.fix:
            print(f"       fix: {c.fix}")


# ---------------------------------------------------------------------------
# Dependency setup
# ---------------------------------------------------------------------------


def venv_python(install_root: Path = INSTALL_ROOT) -> Path:
    exe = install_root / "venv" / "bin" / "python"
    return exe if exe.exists() else Path(sys.executable)


def setup_dependencies(
    install_root: Path = INSTALL_ROOT,
    *,
    with_browser: bool = False,
    verbose: bool = False,
) -> dict:
    """Create the venv and install dependencies. Idempotent."""
    venv_dir = install_root / "venv"
    steps: list[str] = []
    if not (venv_dir / "bin" / "python").exists():
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=not verbose,
            timeout=300,
        )
        steps.append("created venv")
    else:
        steps.append("venv already present")

    vpy = venv_dir / "bin" / "python"
    req = BASE_DIR / "requirements.txt"
    extra = ["cryptography>=41"]
    cmd = [str(vpy), "-m", "pip", "install", "-r", str(req), *extra]
    subprocess.run(cmd, check=True, capture_output=not verbose, timeout=1200)
    steps.append("installed requirements.txt + cryptography")

    if with_browser:
        subprocess.run(
            [str(vpy), "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=not verbose,
            timeout=1200,
        )
        steps.append("installed playwright chromium")

    return {"venv": str(venv_dir), "steps": steps}


# ---------------------------------------------------------------------------
# Guided onboarding
# ---------------------------------------------------------------------------


@dataclass
class OnboardingAnswers:
    full_name: str = ""
    email: str = ""
    data_dir: str = ""
    sync_opt_in: bool = False  # local-only remains the default
    channel: str = "stable"


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{text}{suffix}: ").strip()
    except EOFError:
        answer = ""
    return answer or default


def guided_onboarding(answers: OnboardingAnswers | None = None) -> OnboardingAnswers:
    """Interactive onboarding. Pass ``answers`` for non-interactive runs."""
    if answers is not None:
        return answers
    print("\n— Veto onboarding —")
    print("Local-first: your data stays on this machine unless you opt in.\n")
    full_name = _prompt("Your full name")
    email = _prompt("Email (for tailored materials)")
    data_dir = _prompt("Data directory", str(DEFAULT_DATA_DIR))
    sync = _prompt("Enable encrypted device sync now? (yes/no)", "no")
    channel = _prompt("Release channel (stable/preview)", "stable")
    return OnboardingAnswers(
        full_name=full_name,
        email=email,
        data_dir=data_dir,
        sync_opt_in=sync.lower().startswith("y"),
        channel=channel if channel in ("stable", "preview") else "stable",
    )


def write_install_record(answers: OnboardingAnswers, install_root: Path = INSTALL_ROOT) -> Path:
    data_dir = Path(answers.data_dir or str(DEFAULT_DATA_DIR)).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "package": "veto",
        "package_version": PACKAGE_VERSION,
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "channel": answers.channel,
        "data_dir": str(data_dir),
        "sync_opt_in": answers.sync_opt_in,
        "python": sys.version.split()[0],
    }
    install_root.mkdir(parents=True, exist_ok=True)
    INSTALL_RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    # Starter profile stamped with the i10-required profile-v1 schema so
    # backup/sync/compat checks accept it from day one.
    profile_path = data_dir / "profiles" / "profile.json"
    if not profile_path.exists():
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps(
                {
                    "schema_version": "profile-v1",
                    "full_name": answers.full_name,
                    "email": answers.email,
                    "created_by": "veto-installer",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return INSTALL_RECORD


def install_shim(install_root: Path = INSTALL_ROOT) -> Path:
    """Write a ``veto`` launcher shim into ~/.local/bin."""
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "veto"
    venv_py = install_root / "venv" / "bin" / "python"
    shim.write_text(
        f"""#!/usr/bin/env bash
# Veto launcher (written by the installer). Do not edit by hand.
exec "{venv_py}" "{BASE_DIR}/cli.py" "$@"
""",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return shim


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------


def uninstall(
    install_root: Path = INSTALL_ROOT,
    *,
    purge_data: bool = False,
    confirm: str = "",
) -> dict:
    """Remove the venv, shim, and install record.

    Data is removed ONLY when ``purge_data=True`` AND ``confirm`` equals
    ``"PURGE MY DATA"`` — uninstall never destroys job-search history by
    accident.
    """
    removed: list[str] = []
    data_dir: Path | None = None
    if INSTALL_RECORD.exists():
        try:
            data_dir = Path(json.loads(INSTALL_RECORD.read_text())["data_dir"])
        except (KeyError, json.JSONDecodeError, ValueError):
            data_dir = None

    for path in (install_root / "venv", Path.home() / ".local" / "bin" / "veto"):
        if path.is_symlink() or path.is_file():
            path.unlink()
            removed.append(str(path))
        elif path.is_dir():
            shutil.rmtree(path)
            removed.append(str(path))

    if INSTALL_RECORD.exists():
        INSTALL_RECORD.unlink()
        removed.append(str(INSTALL_RECORD))

    purged: list[str] = []
    if purge_data:
        if confirm != "PURGE MY DATA":
            raise ValueError(
                "Refusing to purge data without explicit confirmation "
                "'PURGE MY DATA'."
            )
        if data_dir and data_dir.exists() and data_dir != Path.home():
            shutil.rmtree(data_dir)
            purged.append(str(data_dir))

    return {"removed": removed, "purged_data": purged}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_install(args: argparse.Namespace) -> int:
    print("Veto installer — environment checks")
    checks = check_environment()
    print_checks(checks)
    if not environment_ok(checks):
        print("\nEnvironment checks failed. Fix the ✗ items above and re-run.")
        return 1
    print("\nEnvironment OK. Installing dependencies…")
    info = setup_dependencies(
        with_browser=args.with_browser, verbose=args.verbose
    )
    for step in info["steps"]:
        print(f"  • {step}")
    answers = (
        OnboardingAnswers(
            full_name=args.name or "",
            email=args.email or "",
            data_dir=args.data_dir or "",
            sync_opt_in=False,
            channel=args.channel,
        )
        if args.yes
        else guided_onboarding()
    )
    record_path = write_install_record(answers)
    shim = install_shim()
    print(f"\nInstall record: {record_path}")
    print(f"Launcher shim:  {shim}")
    if answers.sync_opt_in:
        print(
            "\nSync opt-in recorded. Run `python3 -m initiatives.i10.sync enable` "
            "to pair your first device."
        )
    print(
        "\nDone. Try it:\n"
        f"  veto --help            # CLI\n"
        f"  veto serve             # local web UI\n"
        "  python3 doctor.py      # setup health check"
    )
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    try:
        result = uninstall(purge_data=args.purge_data, confirm=args.confirm or "")
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    for path in result["removed"]:
        print(f"  removed {path}")
    for path in result["purged_data"]:
        print(f"  PURGED data {path}")
    print("Uninstall complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="veto-installer", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Install Veto")
    p_install.add_argument("--yes", action="store_true", help="Accept defaults (non-interactive)")
    p_install.add_argument("--with-browser", action="store_true", help="Also install Playwright Chromium")
    p_install.add_argument("--name", default="", help="Full name (with --yes)")
    p_install.add_argument("--email", default="", help="Email (with --yes)")
    p_install.add_argument("--data-dir", default="", help="Data directory (with --yes)")
    p_install.add_argument("--channel", default="stable", choices=("stable", "preview"))
    p_install.add_argument("--verbose", action="store_true")
    p_install.set_defaults(func=cmd_install)

    p_check = sub.add_parser("check", help="Run environment checks only")
    p_check.set_defaults(func=lambda a: (print_checks(check_environment()), 0)[1])

    p_uninstall = sub.add_parser("uninstall", help="Remove Veto")
    p_uninstall.add_argument("--purge-data", action="store_true", help="Also delete the data directory")
    p_uninstall.add_argument("--confirm", default="", help="Must be 'PURGE MY DATA' with --purge-data")
    p_uninstall.set_defaults(func=cmd_uninstall)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
