"""Initiative 10 — installer tests (synthetic; no real installs)."""

import contextlib
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from initiatives.i10 import installer


@contextlib.contextmanager
def _patched_install_env(fake):
    """Patch Path.home and the install record to a fake install tree."""
    with mock.patch.object(Path, "home", return_value=fake["home"]):
        with mock.patch.object(installer, "INSTALL_RECORD", fake["record"]):
            yield


def _make_fake_install(tmp, *, with_sentinel=True):
    """Build a fake install tree: venv + shim + record + data dir."""
    tmp = Path(tmp)
    fake_home = tmp / "home"
    bin_dir = fake_home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    install_root = tmp / "iroot"
    venv_bin = install_root / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    venv_py = venv_bin / "python"
    venv_py.write_text("#!/bin/sh\n", encoding="utf-8")
    shim = bin_dir / "veto"
    shim.write_text(
        "#!/usr/bin/env bash\n# written by the installer\n", encoding="utf-8"
    )
    data = tmp / "data"
    data.mkdir()
    (data / "outcomes.jsonl").write_text("{}\n", encoding="utf-8")
    if with_sentinel:
        (data / installer.DATA_SENTINEL).write_text("{}\n", encoding="utf-8")
    record = install_root / "install.json"
    record.write_text(json.dumps({"data_dir": str(data)}), encoding="utf-8")
    return {
        "home": fake_home,
        "root": install_root,
        "venv_py": venv_py,
        "shim": shim,
        "data": data,
        "record": record,
    }


@contextlib.contextmanager
def _drop_backup_env():
    """Ensure no backup passphrase leaks in from the ambient environment."""
    with mock.patch.dict(os.environ):
        os.environ.pop("VETO_BACKUP_PASSPHRASE", None)
        yield


class TestEnvironmentChecks(unittest.TestCase):
    def test_checks_return_named_results(self):
        checks = installer.check_environment()
        names = {c.name for c in checks}
        self.assertTrue({"python", "pip", "disk", "install-dir"} <= names)

    def test_python_check_passes_on_modern_python(self):
        checks = {c.name: c for c in installer.check_environment()}
        self.assertTrue(checks["python"].ok)

    def test_environment_ok_logic(self):
        ok = [installer.Check("a", True, "d")]
        bad = [installer.Check("a", False, "d", severity="error")]
        warn = [installer.Check("a", False, "d", severity="warning")]
        self.assertTrue(installer.environment_ok(ok))
        self.assertFalse(installer.environment_ok(bad))
        self.assertTrue(installer.environment_ok(warn))  # warnings never block


class TestVenvCheckSeverity(unittest.TestCase):
    def test_missing_venv_module_is_error_severity(self):
        """C3: the venv-module check must fail fast (error, not warning) with
        an actionable remediation, so `curl | bash` dies before mutating."""

        def boom(*args, **kwargs):
            raise subprocess.CalledProcessError(1, args[0])

        with mock.patch.object(installer.subprocess, "run", side_effect=boom):
            checks = {c.name: c for c in installer.check_environment()}
        venv_check = checks["venv"]
        self.assertFalse(venv_check.ok)
        self.assertEqual(venv_check.severity, "error")
        self.assertIn("python3-venv", venv_check.fix)
        self.assertFalse(installer.environment_ok([venv_check]))


class TestVenvRepair(unittest.TestCase):
    @staticmethod
    def _fake_run(calls):
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if len(cmd) >= 3 and cmd[1] == "-m" and cmd[2] == "venv":
                py = Path(cmd[3]) / "bin" / "python"
                py.parent.mkdir(parents=True, exist_ok=True)
                py.write_text("#!/bin/sh\n", encoding="utf-8")
            return mock.Mock(returncode=0)

        return fake_run

    def test_corrupt_venv_is_removed_and_rebuilt(self):
        """C2: venv dir present but interpreter missing -> rebuild, not crash."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "iroot"
            venv_dir = root / "venv"
            (venv_dir / "lib").mkdir(parents=True)
            (venv_dir / "pyvenv.cfg").write_text("broken\n", encoding="utf-8")
            calls = []
            with mock.patch.object(
                installer.subprocess, "run", side_effect=self._fake_run(calls)
            ):
                info = installer.setup_dependencies(install_root=root)
            self.assertIn("removed corrupt venv", info["steps"])
            self.assertIn("created venv", info["steps"])
            pip_cmds = [
                c for c in calls if len(c) >= 4 and c[1] == "-m" and c[2] == "pip"
            ]
            self.assertEqual(len(pip_cmds), 1)
            self.assertTrue(str(pip_cmds[0][0]).endswith("venv/bin/python"))

    def test_healthy_venv_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "iroot"
            venv_bin = root / "venv" / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "python").write_text("#!/bin/sh\n", encoding="utf-8")
            calls = []
            with mock.patch.object(
                installer.subprocess, "run", side_effect=self._fake_run(calls)
            ):
                info = installer.setup_dependencies(install_root=root)
            self.assertIn("venv already present", info["steps"])
            venv_creations = [
                c for c in calls if len(c) >= 3 and c[1] == "-m" and c[2] == "venv"
            ]
            self.assertEqual(venv_creations, [])


class TestInstallerPins(unittest.TestCase):
    def test_extra_deps_are_exact_pins(self):
        """M1: installer-managed deps carry == pins for reproducibility."""
        self.assertTrue(installer.INSTALL_EXTRA_DEPS)
        names = []
        for dep in installer.INSTALL_EXTRA_DEPS:
            self.assertRegex(dep, r"^[A-Za-z0-9_.-]+==[^,;\s]+$")
            names.append(dep.split("==")[0].lower())
        self.assertIn("cryptography", names)


class TestInstallRecord(unittest.TestCase):
    def test_write_install_record_stamps_profile_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "install-root"
            answers = installer.OnboardingAnswers(
                full_name="Test User",
                email="test@example.com",
                data_dir=str(Path(tmp) / "data"),
                channel="stable",
            )
            with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                rec_path = installer.write_install_record(answers, install_root=root)
            record = json.loads(rec_path.read_text(encoding="utf-8"))
            self.assertEqual(record["channel"], "stable")
            self.assertFalse(record["sync_opt_in"])  # local-only default
            profile = json.loads(
                (Path(tmp) / "data" / "profiles" / "profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(profile["schema_version"], "profile-v1")

    def test_write_install_record_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = installer.OnboardingAnswers(data_dir=str(Path(tmp) / "data"))
            with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                installer.write_install_record(answers, install_root=root)
                installer.write_install_record(answers, install_root=root)
            self.assertTrue((root / "install.json").exists())

    def test_install_record_is_owner_only(self):
        """M4: install.json is written with mode 0o600."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "iroot"
            answers = installer.OnboardingAnswers(data_dir=str(Path(tmp) / "data"))
            with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                rec_path = installer.write_install_record(answers, install_root=root)
            self.assertEqual(stat.S_IMODE(rec_path.stat().st_mode), 0o600)

    def test_sentinel_written_at_install(self):
        """The purge sentinel is created with the data dir."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "iroot"
            data = Path(tmp) / "data"
            with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                installer.write_install_record(
                    installer.OnboardingAnswers(data_dir=str(data)), install_root=root
                )
            self.assertTrue((data / installer.DATA_SENTINEL).is_file())


class TestDataDirValidation(unittest.TestCase):
    def test_rejects_existing_file(self):
        """M3: a data dir that exists as a file is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "afile"
            f.write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                installer.validate_data_dir(str(f))
            self.assertTrue(f.is_file())  # untouched

    def test_rejects_root_and_home(self):
        """M3: `/` and $HOME-exact are rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            fake_home.mkdir()
            with mock.patch.object(Path, "home", return_value=fake_home):
                with self.assertRaises(ValueError):
                    installer.validate_data_dir("/")
                with self.assertRaises(ValueError):
                    installer.validate_data_dir(str(fake_home))

    def test_validation_happens_before_any_mkdir(self):
        """M3: an invalid data dir creates nothing (no install root either)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "iroot"
            with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                with self.assertRaises(ValueError):
                    installer.write_install_record(
                        installer.OnboardingAnswers(data_dir="/"), install_root=root
                    )
            self.assertFalse(root.exists())


class TestPurgeValidation(unittest.TestCase):
    def test_refused_purge_leaves_install_intact_then_retry_purges(self):
        """C1: validate-first — a refused purge deletes NOTHING (venv, shim,
        record, data all survive), and a later correct confirmation purges."""
        with tempfile.TemporaryDirectory() as tmp:
            fake = _make_fake_install(tmp)
            with _patched_install_env(fake), _drop_backup_env():
                with self.assertRaises(ValueError):
                    installer.uninstall(fake["root"], purge_data=True, confirm="nope")
                self.assertTrue(fake["venv_py"].exists())
                self.assertTrue(fake["shim"].exists())
                self.assertTrue(fake["record"].exists())
                self.assertTrue((fake["data"] / "outcomes.jsonl").exists())
                # Retry with the correct path-echoing confirmation purges.
                target = fake["data"].resolve()
                result = installer.uninstall(
                    fake["root"],
                    purge_data=True,
                    confirm=f"PURGE MY DATA {target}",
                    no_backup_ack=True,
                )
            self.assertEqual(result["purged_data"], [str(target)])
            self.assertFalse(fake["data"].exists())

    def test_purge_requires_path_echo_in_confirmation(self):
        """The old bare 'PURGE MY DATA' and a wrong path both refuse."""
        with tempfile.TemporaryDirectory() as tmp:
            fake = _make_fake_install(tmp)
            with _patched_install_env(fake), _drop_backup_env():
                with self.assertRaises(ValueError):
                    installer.uninstall(
                        fake["root"], purge_data=True, confirm="PURGE MY DATA"
                    )
                with self.assertRaises(ValueError):
                    installer.uninstall(
                        fake["root"],
                        purge_data=True,
                        confirm="PURGE MY DATA /somewhere/else",
                    )
                self.assertTrue(fake["data"].exists())
                self.assertTrue(fake["record"].exists())
                self.assertTrue(fake["venv_py"].exists())

    def test_purge_refuses_home_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = _make_fake_install(tmp)
            fake["record"].write_text(
                json.dumps({"data_dir": str(fake["home"])}), encoding="utf-8"
            )
            with _patched_install_env(fake), _drop_backup_env():
                target = fake["home"].resolve()
                with self.assertRaisesRegex(ValueError, "home directory"):
                    installer.uninstall(
                        fake["root"],
                        purge_data=True,
                        confirm=f"PURGE MY DATA {target}",
                        no_backup_ack=True,
                    )
                # Install 100% intact.
                self.assertTrue(fake["record"].exists())
                self.assertTrue(fake["venv_py"].exists())
                self.assertTrue(fake["shim"].exists())

    def test_purge_refuses_filesystem_root(self):
        with self.assertRaisesRegex(ValueError, "filesystem root"):
            installer.validate_purge_target("/")

    def test_purge_refuses_system_root(self):
        with self.assertRaises(ValueError):
            installer.validate_purge_target("/etc")

    def test_purge_refuses_unmanaged_directory(self):
        """No sentinel and not under the install root -> refuse."""
        with tempfile.TemporaryDirectory() as tmp:
            stray = Path(tmp) / "stray"
            stray.mkdir()
            with self.assertRaisesRegex(ValueError, "not a Veto-managed"):
                installer.validate_purge_target(stray)

    def test_purge_refuses_install_root_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "iroot"
            root.mkdir()
            with self.assertRaisesRegex(ValueError, "install root"):
                installer.validate_purge_target(root, install_root=root)

    def test_purge_without_record_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            (fake_home / ".local" / "bin").mkdir(parents=True)
            root = Path(tmp) / "iroot"
            root.mkdir()
            missing = root / "install.json"  # does not exist
            with mock.patch.object(Path, "home", return_value=fake_home):
                with mock.patch.object(installer, "INSTALL_RECORD", missing):
                    with self.assertRaisesRegex(ValueError, "no install record"):
                        installer.uninstall(
                            root,
                            purge_data=True,
                            confirm="PURGE MY DATA /x",
                            no_backup_ack=True,
                        )

    def test_purge_allows_sentinel_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "data"
            d.mkdir()
            (d / installer.DATA_SENTINEL).write_text("{}\n", encoding="utf-8")
            self.assertEqual(installer.validate_purge_target(d), d.resolve())

    def test_purge_allows_dir_under_install_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "iroot"
            d = root / "data"
            d.mkdir(parents=True)
            self.assertEqual(
                installer.validate_purge_target(d, install_root=root), d.resolve()
            )


class TestPrePurgeBackup(unittest.TestCase):
    def test_backup_taken_when_passphrase_available(self):
        """Finding 2: a pre-purge backup is taken automatically when a
        passphrase is available (env var here)."""
        with tempfile.TemporaryDirectory() as tmp:
            fake = _make_fake_install(tmp)
            with _patched_install_env(fake):
                with mock.patch.dict(
                    os.environ, {"VETO_BACKUP_PASSPHRASE": "test-backup-passphrase"}
                ):
                    target = fake["data"].resolve()
                    result = installer.uninstall(
                        fake["root"],
                        purge_data=True,
                        confirm=f"PURGE MY DATA {target}",
                    )
            backup_path = result["pre_purge_backup"]
            self.assertIsNotNone(backup_path)
            self.assertTrue(Path(backup_path).is_file())
            self.assertFalse(fake["data"].exists())

    def test_refused_without_passphrase_and_without_ack(self):
        """Fail closed: no passphrase + no explicit ack -> no purge, intact."""
        with tempfile.TemporaryDirectory() as tmp:
            fake = _make_fake_install(tmp)
            with _patched_install_env(fake), _drop_backup_env():
                target = fake["data"].resolve()
                with self.assertRaisesRegex(ValueError, "pre-purge backup"):
                    installer.uninstall(
                        fake["root"],
                        purge_data=True,
                        confirm=f"PURGE MY DATA {target}",
                    )
                self.assertTrue(fake["data"].exists())
                self.assertTrue(fake["record"].exists())
                self.assertTrue(fake["venv_py"].exists())


class TestUninstallSafety(unittest.TestCase):
    def test_uninstall_never_purges_data_without_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            (data / "outcomes.jsonl").write_text("{}\n", encoding="utf-8")
            (data / installer.DATA_SENTINEL).write_text("{}\n", encoding="utf-8")
            root = Path(tmp) / "iroot"
            root.mkdir()
            (root / "install.json").write_text(
                json.dumps({"data_dir": str(data)}), encoding="utf-8"
            )
            with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                with self.assertRaises(ValueError):
                    installer.uninstall(root, purge_data=True, confirm="yes please")
            # Data survives the refused purge.
            self.assertTrue((data / "outcomes.jsonl").exists())

    def test_uninstall_purges_only_with_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            (fake_home / ".local" / "bin").mkdir(parents=True)
            data = Path(tmp) / "data"
            data.mkdir()
            (data / installer.DATA_SENTINEL).write_text("{}\n", encoding="utf-8")
            root = Path(tmp) / "iroot"
            root.mkdir()
            (root / "install.json").write_text(
                json.dumps({"data_dir": str(data)}), encoding="utf-8"
            )
            target = data.resolve()
            with mock.patch.object(Path, "home", return_value=fake_home):
                with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                    with _drop_backup_env():
                        result = installer.uninstall(
                            root,
                            purge_data=True,
                            confirm=f"PURGE MY DATA {target}",
                            no_backup_ack=True,
                        )
            self.assertEqual(result["purged_data"], [str(target)])
            self.assertFalse(data.exists())

    def test_uninstall_without_purge_keeps_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            (fake_home / ".local" / "bin").mkdir(parents=True)
            data = Path(tmp) / "data"
            data.mkdir()
            root = Path(tmp) / "iroot"
            root.mkdir()
            (root / "install.json").write_text(
                json.dumps({"data_dir": str(data)}), encoding="utf-8"
            )
            with mock.patch.object(Path, "home", return_value=fake_home):
                with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                    result = installer.uninstall(root)
            self.assertEqual(result["purged_data"], [])
            self.assertTrue(data.exists())

    def test_installer_never_clobbers_foreign_veto_shim(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            (fake_home / ".local" / "bin").mkdir(parents=True)
            foreign = fake_home / ".local" / "bin" / "veto"
            foreign.write_text("#!/usr/bin/env bash\necho user-tool\n", encoding="utf-8")
            with mock.patch.object(Path, "home", return_value=fake_home):
                shim = installer.install_shim(install_root=Path(tmp) / "iroot")
            # Untouched: still the user's file.
            self.assertEqual(
                foreign.read_text(encoding="utf-8"), "#!/usr/bin/env bash\necho user-tool\n"
            )
            self.assertEqual(shim, foreign)

    def test_uninstall_leaves_foreign_veto_shim_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            (fake_home / ".local" / "bin").mkdir(parents=True)
            foreign = fake_home / ".local" / "bin" / "veto"
            foreign.write_text("#!/usr/bin/env bash\necho user-tool\n", encoding="utf-8")
            root = Path(tmp) / "iroot"
            root.mkdir()
            (root / "install.json").write_text(json.dumps({"data_dir": str(Path(tmp)/"d")}), encoding="utf-8")
            with mock.patch.object(Path, "home", return_value=fake_home):
                with mock.patch.object(installer, "INSTALL_RECORD", root / "install.json"):
                    result = installer.uninstall(root)
            self.assertTrue(foreign.exists())
            self.assertNotIn(str(foreign), result["removed"])

    def test_uninstall_leaves_dangling_veto_symlink_alone(self):
        """M2: the written-by-installer marker check applies to symlinks too —
        a symlink named `veto` was never written by the installer."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            bin_dir = fake_home / ".local" / "bin"
            bin_dir.mkdir(parents=True)
            link = bin_dir / "veto"
            link.symlink_to(bin_dir / "does-not-exist")  # dangling
            root = Path(tmp) / "iroot"
            root.mkdir()
            record = root / "install.json"
            record.write_text(
                json.dumps({"data_dir": str(Path(tmp) / "d")}), encoding="utf-8"
            )
            with mock.patch.object(Path, "home", return_value=fake_home):
                with mock.patch.object(installer, "INSTALL_RECORD", record):
                    result = installer.uninstall(root)
            self.assertTrue(link.is_symlink())  # untouched, dangling or not
            self.assertNotIn(str(link), result["removed"])


class TestShimPathCheck(unittest.TestCase):
    def test_detection(self):
        """Finding 6: shim_on_path detects whether ~/.local/bin is on PATH."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            bin_dir = fake_home / ".local" / "bin"
            bin_dir.mkdir(parents=True)
            with mock.patch.object(Path, "home", return_value=fake_home):
                with mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}):
                    self.assertFalse(installer.shim_on_path())
                with mock.patch.dict(
                    os.environ, {"PATH": f"/usr/bin{os.pathsep}{bin_dir}"}
                ):
                    self.assertTrue(installer.shim_on_path())
                with mock.patch.dict(os.environ, {"PATH": ""}):
                    self.assertFalse(installer.shim_on_path(bin_dir))


class TestPassphraseNeverOnArgv(unittest.TestCase):
    """Rule 1 (i10-wide): no passphrase may appear on any argv in WS1 files."""

    def _read(self, rel):
        return (installer.BASE_DIR / rel).read_text(encoding="utf-8")

    def test_no_script_passes_passphrase_on_argv(self):
        for rel in (
            "scripts/veto-backup.sh",
            "scripts/veto-uninstall.sh",
            "scripts/veto-install.sh",
            "launch/install.sh",
        ):
            for i, line in enumerate(self._read(rel).splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                self.assertNotIn(
                    "--passphrase ", stripped, f"{rel}:{i}: passphrase on argv"
                )
                self.assertNotIn(
                    "--passphrase=", stripped, f"{rel}:{i}: passphrase on argv"
                )

    def test_backup_script_hands_passphrase_via_env(self):
        text = self._read("scripts/veto-backup.sh")
        self.assertIn("export VETO_BACKUP_PASSPHRASE", text)

    def test_installer_cli_has_no_passphrase_flag(self):
        # Unrecognized flag -> argparse exits before anything runs.
        with self.assertRaises(SystemExit):
            installer.main(["uninstall", "--passphrase", "secret"])


if __name__ == "__main__":
    unittest.main()
