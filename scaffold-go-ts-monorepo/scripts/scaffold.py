#!/usr/bin/env python3
"""Create a reproducible Go API + React/TypeScript monorepo."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = SKILL_ROOT / "assets" / "scaffold"

CREATE_VITE_VERSION = os.getenv("SCAFFOLD_CREATE_VITE_VERSION", "9.1.1")
SHADCN_VERSION = os.getenv("SCAFFOLD_SHADCN_VERSION", "4.13.0")
PNPM_VERSION = os.getenv("SCAFFOLD_PNPM_VERSION", "10.33.0")
HEY_API_VERSION = os.getenv("SCAFFOLD_HEY_API_VERSION", "0.99.0")
OXLINT_VERSION = os.getenv("SCAFFOLD_OXLINT_VERSION", "1.71.0")
TAILWIND_VERSION = os.getenv("SCAFFOLD_TAILWIND_VERSION", "4.3.2")
TYPESCRIPT_VERSION = os.getenv("SCAFFOLD_TYPESCRIPT_VERSION", "5.9.3")
GO_VERSION = os.getenv("SCAFFOLD_GO_VERSION", "1.26.0")
GINX_VERSION = os.getenv("SCAFFOLD_GINX_VERSION", "v0.0.12")
GIN_VERSION = os.getenv("SCAFFOLD_GIN_VERSION", "v1.12.0")
VIPER_VERSION = os.getenv("SCAFFOLD_VIPER_VERSION", "v1.21.0")
GORM_POSTGRES_VERSION = os.getenv("SCAFFOLD_GORM_POSTGRES_VERSION", "v1.6.0")
GORM_VERSION = os.getenv("SCAFFOLD_GORM_VERSION", "v1.31.2")
OAPI_GINX_VERSION = os.getenv("SCAFFOLD_OAPI_GINX_VERSION", "v0.0.12")

GO_DEPENDENCIES = (
    f"github.com/chendefine/ginx@{GINX_VERSION}",
    f"github.com/gin-gonic/gin@{GIN_VERSION}",
    f"github.com/spf13/viper@{VIPER_VERSION}",
    f"gorm.io/driver/postgres@{GORM_POSTGRES_VERSION}",
    f"gorm.io/gorm@{GORM_VERSION}",
)
GO_TOOL = f"github.com/chendefine/ginx/cmd/oapi-ginx@{OAPI_GINX_VERSION}"

PROJECT_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a ginx/OpenAPI API and Vite/shadcn web monorepo.",
    )
    parser.add_argument("--target", required=True, type=Path, help="New directory to create")
    parser.add_argument("--name", help="Project slug; defaults to the target directory name")
    parser.add_argument("--go-module", help="Go module; defaults to <name>/apps/api")
    parser.add_argument("--shadcn-base", choices=("radix", "base"), default="radix")
    parser.add_argument("--shadcn-preset", default="nova")
    parser.add_argument("--build-network", choices=("host", "default"), default="host")
    parser.add_argument("--no-git-init", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def validate(args: argparse.Namespace) -> tuple[Path, str, str]:
    target = args.target.expanduser().resolve()
    name = args.name if args.name is not None else target.name
    module = args.go_module if args.go_module is not None else f"{name}/apps/api"

    if target.exists():
        fail(f"target already exists: {target}")
    if not PROJECT_RE.fullmatch(name):
        fail("project name must contain lowercase letters, digits, and single hyphens")
    if (
        not module
        or any(char.isspace() for char in module)
        or module.startswith("/")
        or module.endswith("/")
        or "//" in module
    ):
        fail("Go module must be a non-empty module path without whitespace")
    if not args.shadcn_preset.strip():
        fail("shadcn preset must not be empty")
    return target, name, module


def require_tools(no_git_init: bool) -> None:
    tools = ["npx", "pnpm", "go", "gofmt", "task"]
    if not no_git_init:
        tools.append("git")
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        fail(f"missing required tools: {', '.join(missing)}")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    location = f" (in {cwd})" if cwd else ""
    print(f"+ {' '.join(command)}{location}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def replacements(name: str, module: str, build_network: str) -> dict[str, str]:
    title = " ".join(part.capitalize() for part in name.split("-"))
    return {
        "__PROJECT_NAME__": name,
        "__PROJECT_TITLE__": title,
        "__GO_MODULE__": module,
        "__BUILD_NETWORK__": build_network,
        "__PNPM_VERSION__": PNPM_VERSION,
        "__GO_VERSION__": GO_VERSION,
    }


def render_tree(source: Path, destination: Path, values: dict[str, str]) -> None:
    for source_path in sorted(source.rglob("*")):
        relative = source_path.relative_to(source)
        if source_path.is_dir():
            continue
        output_relative = relative.with_suffix("") if source_path.suffix == ".tmpl" else relative
        output_path = destination / output_relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = source_path.read_text()
        for token, value in values.items():
            content = content.replace(token, value)
        output_path.write_text(content)
        if output_path.suffix in {".sh", ".py"}:
            output_path.chmod(0o755)


def update_package_json(web: Path) -> None:
    package_path = web / "package.json"
    package = json.loads(package_path.read_text())
    package["name"] = "web"
    package["packageManager"] = f"pnpm@{PNPM_VERSION}"
    package["scripts"].update(
        {
            "gen": "openapi-ts",
            "lint": "oxlint",
            "typecheck": "tsc -b",
            "test": "pnpm run typecheck",
        }
    )
    package_path.write_text(json.dumps(package, indent=2) + "\n")


def configure_typescript_aliases(web: Path) -> None:
    root_config = web / "tsconfig.json"
    root_text = root_config.read_text()
    if '"compilerOptions"' not in root_text:
        root_text = root_text.replace(
            "{\n",
            '{\n  "compilerOptions": {\n    "baseUrl": ".",\n    "paths": { "@/*": ["./src/*"] }\n  },\n',
            1,
        )
        root_config.write_text(root_text)

    app_config = web / "tsconfig.app.json"
    app_text = app_config.read_text()
    marker = '"compilerOptions": {'
    if '"@/*"' not in app_text:
        if marker not in app_text:
            fail(f"cannot configure TypeScript alias in {app_config}")
        app_text = app_text.replace(
            marker,
            '"compilerOptions": {\n    "baseUrl": ".",\n    "paths": { "@/*": ["./src/*"] },',
            1,
        )
    if '"DOM.Iterable"' not in app_text:
        app_text = app_text.replace('"DOM"]', '"DOM", "DOM.Iterable"]', 1)
    app_config.write_text(app_text)


def dry_run_summary(
    target: Path,
    name: str,
    module: str,
    args: argparse.Namespace,
) -> None:
    summary = {
        "target": str(target),
        "name": name,
        "go_module": module,
        "shadcn": {"version": SHADCN_VERSION, "base": args.shadcn_base, "preset": args.shadcn_preset},
        "create_vite_version": CREATE_VITE_VERSION,
        "pnpm_version": PNPM_VERSION,
        "typescript_version": TYPESCRIPT_VERSION,
        "tailwind_version": TAILWIND_VERSION,
        "hey_api_version": HEY_API_VERSION,
        "oxlint_version": OXLINT_VERSION,
        "go_version": GO_VERSION,
        "go_dependencies": list(GO_DEPENDENCIES),
        "go_tool": GO_TOOL,
        "build_network": args.build_network,
        "git_init": not args.no_git_init,
        "commands": ["create-vite", "shadcn init", "shadcn add card badge", "task gen", "task check"],
    }
    print(json.dumps(summary, indent=2))


def scaffold(args: argparse.Namespace) -> None:
    target, name, module = validate(args)
    if args.dry_run:
        dry_run_summary(target, name, module, args)
        return

    require_tools(args.no_git_init)
    values = replacements(name, module, args.build_network)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir()

    render_tree(ASSET_ROOT / "root", target, values)
    render_tree(ASSET_ROOT / "api", target / "apps" / "api", values)

    run(
        [
            "npx",
            "--yes",
            f"create-vite@{CREATE_VITE_VERSION}",
            "apps/web",
            "--template",
            "react-ts",
            "--no-interactive",
        ],
        cwd=target,
    )
    web = target / "apps" / "web"
    update_package_json(web)
    run(["pnpm", "install"], cwd=web)
    run(
        [
            "pnpm",
            "add",
            "--save-dev",
            "--save-exact",
            f"typescript@{TYPESCRIPT_VERSION}",
            f"tailwindcss@{TAILWIND_VERSION}",
            f"@tailwindcss/vite@{TAILWIND_VERSION}",
        ],
        cwd=web,
    )
    render_tree(ASSET_ROOT / "web", web, values)
    configure_typescript_aliases(web)
    run(
        [
            "npx",
            "--yes",
            f"shadcn@{SHADCN_VERSION}",
            "init",
            "--base",
            args.shadcn_base,
            "--preset",
            args.shadcn_preset,
            "--yes",
            "--no-monorepo",
            "--no-rtl",
            "--pointer",
        ],
        cwd=web,
    )
    run(
        ["npx", "--yes", f"shadcn@{SHADCN_VERSION}", "add", "card", "badge", "--yes"],
        cwd=web,
    )
    for starter_file in (web / "src" / "App.css", web / "src" / "assets" / "react.svg"):
        starter_file.unlink(missing_ok=True)
    update_package_json(web)
    run(
        ["pnpm", "add", "--save-dev", "--save-exact", f"@hey-api/openapi-ts@{HEY_API_VERSION}", f"oxlint@{OXLINT_VERSION}"],
        cwd=web,
    )

    api = target / "apps" / "api"
    run(["go", "mod", "init", module], cwd=api)
    run(["go", "mod", "edit", f"-go={GO_VERSION}"], cwd=api)
    run(["go", "get", *GO_DEPENDENCIES], cwd=api)
    run(["go", "get", "-tool", GO_TOOL], cwd=api)

    if not args.no_git_init:
        run(["git", "init", "-b", "main"], cwd=target)

    run(["task", "gen"], cwd=target)
    run(["go", "mod", "tidy"], cwd=api)
    go_files = [str(path.relative_to(api)) for path in sorted(api.rglob("*.go"))]
    run(["gofmt", "-w", *go_files], cwd=api)
    run(["task", "check"], cwd=target)
    print(f"Scaffold complete: {target}")


def main() -> int:
    try:
        scaffold(parse_args())
    except subprocess.CalledProcessError as error:
        print(f"error: command failed with exit code {error.returncode}", file=sys.stderr)
        return error.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
