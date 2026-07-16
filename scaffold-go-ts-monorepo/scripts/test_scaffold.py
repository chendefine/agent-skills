#!/usr/bin/env python3
"""Deterministic unit tests for the greenfield scaffold initializer."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("scaffold.py")
SPEC = importlib.util.spec_from_file_location("scaffold", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {SCRIPT}")
scaffold = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scaffold)


def arguments(target: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "target": target,
        "name": None,
        "title": None,
        "html_lang": "en",
        "go_module": None,
        "shadcn_base": "radix",
        "shadcn_preset": "nova",
        "build_network": "default",
        "no_git_init": False,
        "into_empty_directory": False,
        "into_empty_git_root": False,
        "dry_run": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class ValidationTests(unittest.TestCase):
    def test_absent_target_uses_placeholder_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "example-admin"
            result = scaffold.validate(arguments(target))
        self.assertEqual(result[4], "example-admin/apps/api")
        self.assertEqual(result[5], "placeholder")
        self.assertEqual(result[6], "absent")

    def test_existing_empty_directory_requires_explicit_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            with self.assertRaisesRegex(SystemExit, "target already exists"):
                scaffold.validate(arguments(target))

    def test_explicit_empty_directory_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = scaffold.validate(
                arguments(Path(directory), into_empty_directory=True, name="example-admin")
            )
        self.assertEqual(result[6], "empty-directory")

    def test_nonempty_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "user-file").write_text("preserve me")
            with self.assertRaisesRegex(SystemExit, "no entries"):
                scaffold.validate(
                    arguments(target, into_empty_directory=True, name="example-admin")
                )

    def test_explicit_module_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "example-admin"
            result = scaffold.validate(
                arguments(target, go_module="github.com/acme/example-admin/apps/api")
            )
        self.assertEqual(result[5], "explicit")

    def test_numeric_version_handles_tool_output(self) -> None:
        self.assertEqual(scaffold.numeric_version("go version go1.26.3-X", prefix="go"), (1, 26, 3))
        self.assertEqual(scaffold.numeric_version("v24.14.1"), (24, 14, 1))

    def test_dry_run_exposes_safety_choices(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "example-admin"
            args = arguments(target, dry_run=True)
            validated = scaffold.validate(args)
            output = io.StringIO()
            with redirect_stdout(output):
                scaffold.dry_run_summary(*validated, args)
        summary = json.loads(output.getvalue())
        self.assertEqual(summary["target_mode"], "absent")
        self.assertTrue(summary["staged_generation"])
        self.assertEqual(summary["build_network"], "default")
        self.assertTrue(summary["warnings"])

    def test_replacements_describe_selected_build_network(self) -> None:
        default_values = scaffold.replacements(
            "example-admin",
            "Example Admin",
            "example-admin/apps/api",
            "placeholder",
            "default",
        )
        host_values = scaffold.replacements(
            "example-admin",
            "Example Admin",
            "github.com/acme/example-admin/apps/api",
            "explicit",
            "host",
        )
        self.assertIn("BUILD_NETWORK=host", default_values["__BUILD_NETWORK_NOTICE__"])
        self.assertIn("已显式配置", host_values["__BUILD_NETWORK_NOTICE__"])

    def test_package_update_normalizes_validated_direct_versions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            package = {
                "name": "generated-name",
                "scripts": {},
                "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
                "devDependencies": {"typescript": "~5.0.0", "vite": "^8.0.0"},
            }
            (web / "package.json").write_text(json.dumps(package))
            scaffold.update_package_json(web)
            updated = json.loads((web / "package.json").read_text())
        self.assertEqual(updated["dependencies"]["react"], scaffold.REACT_VERSION)
        self.assertEqual(updated["devDependencies"]["typescript"], scaffold.TYPESCRIPT_VERSION)
        self.assertEqual(updated["devDependencies"]["vite"], scaffold.VITE_VERSION)

    def test_typescript_defaults_to_validated_6_0_patch(self) -> None:
        self.assertEqual(scaffold.DEFAULT_TYPESCRIPT_VERSION, "6.0.3")

    def test_typescript_aliases_do_not_use_deprecated_base_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "tsconfig.json").write_text(
                '{\n  "files": [],\n  "references": []\n}\n'
            )
            (web / "tsconfig.app.json").write_text(
                '{\n  "compilerOptions": {\n    "lib": ["ES2023", "DOM"]\n  }\n}\n'
            )
            scaffold.configure_typescript_aliases(web)
            root_config = (web / "tsconfig.json").read_text()
            app_config = (web / "tsconfig.app.json").read_text()
        self.assertIn('"paths": { "@/*": ["./src/*"] }', root_config)
        self.assertIn('"paths": { "@/*": ["./src/*"] }', app_config)
        self.assertIn('"DOM.Iterable"', app_config)
        self.assertNotIn('"baseUrl"', root_config)
        self.assertNotIn('"baseUrl"', app_config)


class PublishTests(unittest.TestCase):
    def test_publish_absent_target_renames_complete_staging_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            staging = parent / ".staging"
            target = parent / "example-admin"
            staging.mkdir()
            (staging / "sentinel").write_text("complete")
            scaffold.publish_scaffold(staging, target, "absent")
            self.assertEqual((target / "sentinel").read_text(), "complete")
            self.assertFalse(staging.exists())

    def test_publish_empty_directory_replaces_only_verified_empty_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            staging = parent / ".staging"
            target = parent / "example-admin"
            staging.mkdir()
            target.mkdir()
            (staging / "sentinel").write_text("complete")
            scaffold.publish_scaffold(staging, target, "empty-directory")
            self.assertEqual((target / "sentinel").read_text(), "complete")

    def test_publish_refuses_target_that_appears_during_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            staging = parent / ".staging"
            target = parent / "example-admin"
            staging.mkdir()
            target.mkdir()
            with self.assertRaisesRegex(SystemExit, "target appeared"):
                scaffold.publish_scaffold(staging, target, "absent")
            self.assertTrue(staging.exists())

    def test_publish_empty_git_root_preserves_git_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            staging = parent / ".staging"
            target = parent / "example-admin"
            staging.mkdir()
            target.mkdir()
            (target / ".git").mkdir()
            (staging / "sentinel").write_text("complete")
            with mock.patch.object(scaffold, "verify_empty_git_root"):
                scaffold.publish_scaffold(staging, target, "empty-git-root")
            self.assertTrue((target / ".git").is_dir())
            self.assertEqual((target / "sentinel").read_text(), "complete")


if __name__ == "__main__":
    unittest.main()
