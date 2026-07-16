#!/usr/bin/env python3
"""Create a reproducible Go API + React/TypeScript monorepo."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = SKILL_ROOT / "assets" / "scaffold"

DEFAULT_TYPESCRIPT_VERSION = "6.0.3"
CREATE_VITE_VERSION = os.getenv("SCAFFOLD_CREATE_VITE_VERSION", "9.1.1")
SHADCN_VERSION = os.getenv("SCAFFOLD_SHADCN_VERSION", "4.13.0")
PNPM_VERSION = os.getenv("SCAFFOLD_PNPM_VERSION", "10.33.0")
HEY_API_VERSION = os.getenv("SCAFFOLD_HEY_API_VERSION", "0.99.0")
OXLINT_VERSION = os.getenv("SCAFFOLD_OXLINT_VERSION", "1.71.0")
TAILWIND_VERSION = os.getenv("SCAFFOLD_TAILWIND_VERSION", "4.3.2")
TYPESCRIPT_VERSION = os.getenv("SCAFFOLD_TYPESCRIPT_VERSION", DEFAULT_TYPESCRIPT_VERSION)
REACT_VERSION = os.getenv("SCAFFOLD_REACT_VERSION", "19.2.7")
REACT_DOM_VERSION = os.getenv("SCAFFOLD_REACT_DOM_VERSION", "19.2.7")
REACT_TYPES_VERSION = os.getenv("SCAFFOLD_REACT_TYPES_VERSION", "19.2.17")
REACT_DOM_TYPES_VERSION = os.getenv("SCAFFOLD_REACT_DOM_TYPES_VERSION", "19.2.3")
NODE_TYPES_VERSION = os.getenv("SCAFFOLD_NODE_TYPES_VERSION", "24.13.3")
VITE_VERSION = os.getenv("SCAFFOLD_VITE_VERSION", "8.1.4")
VITE_REACT_VERSION = os.getenv("SCAFFOLD_VITE_REACT_VERSION", "6.0.3")
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
HTML_LANG_RE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a ginx/OpenAPI API and Vite/shadcn web monorepo.",
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="Absent target, guarded empty directory, or guarded empty Git root",
    )
    parser.add_argument("--name", help="Project slug; defaults to the target directory name")
    parser.add_argument("--title", help="Display title; defaults to title-cased --name")
    parser.add_argument("--html-lang", default="en", help="HTML language tag; defaults to en")
    parser.add_argument("--go-module", help="Go module; defaults to <name>/apps/api")
    parser.add_argument("--shadcn-base", choices=("radix", "base"), default="radix")
    parser.add_argument("--shadcn-preset", default="nova")
    parser.add_argument("--build-network", choices=("host", "default"), default="default")
    parser.add_argument("--no-git-init", action="store_true", help="Do not initialize Git")
    target_mode = parser.add_mutually_exclusive_group()
    target_mode.add_argument(
        "--into-empty-directory",
        action="store_true",
        help="Stage and publish into an existing empty non-Git directory",
    )
    target_mode.add_argument(
        "--into-empty-git-root",
        action="store_true",
        help="Stage and move into an existing clean directory containing only .git",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def default_title(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def selected_target_mode(args: argparse.Namespace) -> str:
    if args.into_empty_git_root:
        return "empty-git-root"
    if args.into_empty_directory:
        return "empty-directory"
    return "absent"


def validate_real_directory(target: Path, description: str) -> None:
    if target.is_symlink() or not target.is_dir():
        fail(f"{description} must be a real directory: {target}")


def validate_empty_directory_shape(target: Path) -> None:
    validate_real_directory(target, "empty directory target")
    if any(target.iterdir()):
        fail("--into-empty-directory requires a target with no entries")


def validate_empty_git_root_shape(target: Path) -> None:
    validate_real_directory(target, "empty Git root target")
    entries = {path.name for path in target.iterdir()}
    if entries != {".git"}:
        fail("--into-empty-git-root requires a target containing only .git")


def validate(args: argparse.Namespace) -> tuple[Path, str, str, str, str, str, str]:
    target = args.target.expanduser().resolve()
    name = args.name if args.name is not None else target.name
    title = args.title if args.title is not None else default_title(name)
    module = args.go_module if args.go_module is not None else f"{name}/apps/api"
    module_source = "explicit" if args.go_module is not None else "placeholder"
    target_mode = selected_target_mode(args)

    if target_mode == "empty-git-root":
        validate_empty_git_root_shape(target)
    elif target_mode == "empty-directory":
        validate_empty_directory_shape(target)
    elif target.exists():
        fail(f"target already exists: {target}")
    if not PROJECT_RE.fullmatch(name):
        fail("project name must contain lowercase letters, digits, and single hyphens")
    if (
        not title
        or title != title.strip()
        or len(title) > 100
        or not all(char.isalnum() or char in " -_.()" for char in title)
    ):
        fail("project title must be 1-100 letters/digits with spaces or -_.() punctuation")
    if not HTML_LANG_RE.fullmatch(args.html_lang):
        fail("HTML language must be a simple BCP 47 tag such as en or zh-CN")
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
    return target, name, title, args.html_lang, module, module_source, target_mode


def require_tools(no_git_init: bool, verify_existing_git: bool) -> None:
    tools = ["node", "npx", "pnpm", "go", "gofmt", "task"]
    if not no_git_init or verify_existing_git:
        tools.append("git")
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        fail(f"missing required tools: {', '.join(missing)}")
    require_minimum_version(["node", "--version"], "Node.js", "24.0.0")
    require_minimum_version(["pnpm", "--version"], "pnpm", PNPM_VERSION)
    require_minimum_version(["go", "version"], "Go", GO_VERSION, prefix="go")
    require_minimum_version(["task", "--version"], "Go Task", "3.0.0")
    verify_go_task()


def numeric_version(value: str, *, prefix: str = "") -> tuple[int, int, int]:
    pattern = rf"{re.escape(prefix)}(\d+)\.(\d+)(?:\.(\d+))?"
    match = re.search(pattern, value)
    if match is None:
        fail(f"cannot parse version from: {value.strip()}")
    return tuple(int(part or 0) for part in match.groups())


def require_minimum_version(
    command: list[str],
    label: str,
    minimum: str,
    *,
    prefix: str = "",
) -> None:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    output = result.stdout or result.stderr
    actual = numeric_version(output, prefix=prefix)
    required = numeric_version(minimum)
    if actual < required:
        fail(f"{label} {minimum}+ is required; found {output.strip()}")


def verify_go_task() -> None:
    with tempfile.TemporaryDirectory(prefix="scaffold-task-probe-") as directory:
        probe = Path(directory)
        (probe / "Taskfile.yml").write_text(
            'version: "3"\n\ntasks:\n  probe:\n    cmds:\n      - echo codex-go-task-probe\n',
        )
        result = subprocess.run(
            ["task", "probe", "--silent"],
            cwd=probe,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() != "codex-go-task-probe":
            fail("the task executable did not behave like Go Task")


def verify_empty_git_root(target: Path) -> None:
    validate_empty_git_root_shape(target)
    root = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if root.returncode != 0 or Path(root.stdout.strip()).resolve() != target:
        fail(f"target is not a Git worktree root: {target}")
    status = subprocess.run(
        ["git", "-C", str(target), "status", "--porcelain=v1", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout:
        fail("--into-empty-git-root requires a clean Git status")


def verify_empty_directory(target: Path) -> None:
    validate_empty_directory_shape(target)


def publish_scaffold(work_target: Path, target: Path, target_mode: str) -> None:
    if target_mode == "empty-git-root":
        verify_empty_git_root(target)
        for source_path in sorted(work_target.iterdir()):
            shutil.move(str(source_path), target / source_path.name)
        work_target.rmdir()
    elif target_mode == "empty-directory":
        verify_empty_directory(target)
        target.rmdir()
        work_target.rename(target)
    elif target_mode == "absent":
        if target.exists():
            fail(f"target appeared while scaffolding; staged output retained at {work_target}")
        work_target.rename(target)
    else:
        fail(f"unsupported target mode: {target_mode}")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    location = f" (in {cwd})" if cwd else ""
    print(f"+ {' '.join(command)}{location}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def replacements(
    name: str,
    title: str,
    module: str,
    module_source: str,
    build_network: str,
) -> dict[str, str]:
    if module_source == "placeholder":
        module_notice = (
            f"Go module 当前使用本地占位路径 `{module}`；发布前请改为代码托管平台的规范模块路径。"
        )
    else:
        module_notice = f"Go module 使用 `{module}`。"
    if build_network == "host":
        build_network_notice = (
            "构建网络已显式配置为 `host`。仅在当前环境确实需要访问宿主网络时保留该值；可在根 `.env` 中覆盖。"
        )
    else:
        build_network_notice = (
            "构建网络默认使用 `default`。仅当容器构建无法访问依赖源且已确认是 Docker 网络边界时，才在根 `.env` 中设置 `BUILD_NETWORK=host` 后重试。"
        )
    return {
        "__PROJECT_NAME__": name,
        "__PROJECT_TITLE__": title,
        "__GO_MODULE__": module,
        "__GO_MODULE_NOTICE__": module_notice,
        "__BUILD_NETWORK__": build_network,
        "__BUILD_NETWORK_NOTICE__": build_network_notice,
        "__PNPM_VERSION__": PNPM_VERSION,
        "__GO_VERSION__": GO_VERSION,
        "__GINX_VERSION__": GINX_VERSION,
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
    pinned_dependencies = {
        "react": REACT_VERSION,
        "react-dom": REACT_DOM_VERSION,
    }
    pinned_dev_dependencies = {
        "@hey-api/openapi-ts": HEY_API_VERSION,
        "@tailwindcss/vite": TAILWIND_VERSION,
        "@types/node": NODE_TYPES_VERSION,
        "@types/react": REACT_TYPES_VERSION,
        "@types/react-dom": REACT_DOM_TYPES_VERSION,
        "@vitejs/plugin-react": VITE_REACT_VERSION,
        "oxlint": OXLINT_VERSION,
        "tailwindcss": TAILWIND_VERSION,
        "typescript": TYPESCRIPT_VERSION,
        "vite": VITE_VERSION,
    }
    for dependency, version in pinned_dependencies.items():
        if dependency in package.get("dependencies", {}):
            package["dependencies"][dependency] = version
    for dependency, version in pinned_dev_dependencies.items():
        if dependency in package.get("devDependencies", {}):
            package["devDependencies"][dependency] = version
    package_path.write_text(json.dumps(package, indent=2) + "\n")


def configure_typescript_aliases(web: Path) -> None:
    root_config = web / "tsconfig.json"
    root_text = root_config.read_text()
    if '"compilerOptions"' not in root_text:
        root_text = root_text.replace(
            "{\n",
            '{\n  "compilerOptions": {\n    "paths": { "@/*": ["./src/*"] }\n  },\n',
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
            '"compilerOptions": {\n    "paths": { "@/*": ["./src/*"] },',
            1,
        )
    if '"DOM.Iterable"' not in app_text:
        app_text = app_text.replace('"DOM"]', '"DOM", "DOM.Iterable"]', 1)
    app_config.write_text(app_text)


def configure_index_html(web: Path, title: str, html_lang: str) -> None:
    index_path = web / "index.html"
    index_text = index_path.read_text()
    updated, lang_count = re.subn(
        r'<html lang="[^"]+">',
        f'<html lang="{html_lang}">',
        index_text,
        count=1,
    )
    updated, title_count = re.subn(
        r"<title>.*?</title>",
        f"<title>{html.escape(title)}</title>",
        updated,
        count=1,
        flags=re.DOTALL,
    )
    if lang_count != 1 or title_count != 1:
        fail(f"cannot configure title or language in {index_path}")
    index_path.write_text(updated)


def dry_run_summary(
    target: Path,
    name: str,
    title: str,
    html_lang: str,
    module: str,
    module_source: str,
    target_mode: str,
    args: argparse.Namespace,
) -> None:
    warnings = []
    if module_source == "placeholder":
        warnings.append("Go module is a local placeholder; replace it before publishing")
    summary = {
        "target": str(target),
        "name": name,
        "title": title,
        "html_lang": html_lang,
        "go_module": module,
        "go_module_source": module_source,
        "target_mode": target_mode,
        "staged_generation": True,
        "shadcn": {"version": SHADCN_VERSION, "base": args.shadcn_base, "preset": args.shadcn_preset},
        "create_vite_version": CREATE_VITE_VERSION,
        "pnpm_version": PNPM_VERSION,
        "typescript_version": TYPESCRIPT_VERSION,
        "web_dependencies": {
            "react": REACT_VERSION,
            "react-dom": REACT_DOM_VERSION,
            "vite": VITE_VERSION,
            "@vitejs/plugin-react": VITE_REACT_VERSION,
        },
        "tailwind_version": TAILWIND_VERSION,
        "hey_api_version": HEY_API_VERSION,
        "oxlint_version": OXLINT_VERSION,
        "go_version": GO_VERSION,
        "go_dependencies": list(GO_DEPENDENCIES),
        "go_tool": GO_TOOL,
        "build_network": args.build_network,
        "git_init": not args.no_git_init and target_mode != "empty-git-root",
        "into_empty_directory": args.into_empty_directory,
        "into_empty_git_root": args.into_empty_git_root,
        "commands": ["create-vite", "shadcn init", "shadcn add card badge", "task gen", "task check"],
        "warnings": warnings,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def scaffold(args: argparse.Namespace) -> None:
    target, name, title, html_lang, module, module_source, target_mode = validate(args)
    if args.dry_run:
        dry_run_summary(target, name, title, html_lang, module, module_source, target_mode, args)
        return

    require_tools(args.no_git_init, args.into_empty_git_root)
    if target_mode == "empty-git-root":
        verify_empty_git_root(target)
    elif target_mode == "empty-directory":
        verify_empty_directory(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    work_target = Path(tempfile.mkdtemp(prefix=f".{name}-scaffold-", dir=target.parent))
    print(f"Staging scaffold for {target_mode} target: {work_target}", flush=True)
    if module_source == "placeholder":
        print(
            f"warning: Go module {module!r} is a local placeholder; replace it before publishing",
            file=sys.stderr,
            flush=True,
        )
    values = replacements(name, title, module, module_source, args.build_network)

    render_tree(ASSET_ROOT / "root", work_target, values)
    render_tree(ASSET_ROOT / "api", work_target / "apps" / "api", values)

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
        cwd=work_target,
    )
    web = work_target / "apps" / "web"
    update_package_json(web)
    (web / ".npmrc").write_text("save-exact=true\n")
    run(
        [
            "pnpm",
            "add",
            "--save-exact",
            f"react@{REACT_VERSION}",
            f"react-dom@{REACT_DOM_VERSION}",
        ],
        cwd=web,
    )
    run(
        [
            "pnpm",
            "add",
            "--save-dev",
            "--save-exact",
            f"@types/node@{NODE_TYPES_VERSION}",
            f"@types/react@{REACT_TYPES_VERSION}",
            f"@types/react-dom@{REACT_DOM_TYPES_VERSION}",
            f"@vitejs/plugin-react@{VITE_REACT_VERSION}",
            f"typescript@{TYPESCRIPT_VERSION}",
            f"tailwindcss@{TAILWIND_VERSION}",
            f"@tailwindcss/vite@{TAILWIND_VERSION}",
            f"vite@{VITE_VERSION}",
        ],
        cwd=web,
    )
    render_tree(ASSET_ROOT / "web", web, values)
    configure_typescript_aliases(web)
    configure_index_html(web, title, html_lang)
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
    update_package_json(web)
    run(["pnpm", "install", "--lockfile-only"], cwd=web)

    api = work_target / "apps" / "api"
    run(["go", "mod", "init", module], cwd=api)
    run(["go", "mod", "edit", f"-go={GO_VERSION}"], cwd=api)
    run(["go", "get", *GO_DEPENDENCIES], cwd=api)
    run(["go", "get", "-tool", GO_TOOL], cwd=api)

    if not args.no_git_init and target_mode != "empty-git-root":
        run(["git", "init", "-b", "main"], cwd=work_target)

    run(["task", "gen"], cwd=work_target)
    run(["go", "mod", "tidy"], cwd=api)
    go_files = [str(path.relative_to(api)) for path in sorted(api.rglob("*.go"))]
    run(["gofmt", "-w", *go_files], cwd=api)
    run(["task", "check"], cwd=work_target)

    publish_scaffold(work_target, target, target_mode)
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
