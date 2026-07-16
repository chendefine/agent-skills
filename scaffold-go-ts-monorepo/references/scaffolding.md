# Reproducible greenfield scaffolding

Use this reference for `scripts/scaffold.py` and its bundled assets.

## Contents

- [Inputs and safety](#inputs-and-safety)
- [Generated baseline](#generated-baseline)
- [Ownership and generation](#ownership-and-generation)
- [Version policy](#version-policy)
- [Validation and maintenance](#validation-and-maintenance)

## Inputs and safety

Run the script from any directory. Require an absent `--target` by default; never merge into or overwrite an ordinary existing directory. Generate every new project in a sibling staging directory, run `task check` there, publish only after success, and run `task check` again from the final path. Derive `--name` from the target basename, the display `--title` from the slug, and `--go-module` from `<name>/apps/api` when omitted.

```bash
python scripts/scaffold.py \
  --target /work/example-admin \
  --title "Example Admin" \
  --go-module github.com/example/example-admin/apps/api
```

For an existing empty non-Git directory, require `--into-empty-directory`. Recheck that it remains a real empty directory immediately before replacing it with the validated staging tree:

```bash
python scripts/scaffold.py \
  --target /work/example-admin \
  --into-empty-directory \
  --name example-admin \
  --title "示例管理后台" \
  --html-lang zh-CN
```

For an existing empty Git root containing only `.git`, stage the complete scaffold beside it and move it into place only after the staged `task check` succeeds:

```bash
python scripts/scaffold.py \
  --target /work/example-admin \
  --into-empty-git-root \
  --name example-admin \
  --title "示例管理后台" \
  --html-lang zh-CN \
  --go-module github.com/example/example-admin/apps/api
```

Reject `--into-empty-directory` when the target is a symlink, contains any entry, or changes while generation runs. Reject `--into-empty-git-root` when the target is not the Git worktree root, contains any entry besides `.git`, or has any Git status output. Do not reinterpret an existing application repository as an empty target. Verify the target again before publishing and retain a failed staging directory for inspection; never delete an existing Git root during recovery.

An omitted `--go-module` intentionally produces a local placeholder such as `example-admin/apps/api`. Report it in dry-run and generated README output; replace it with the canonical VCS module path before publishing reusable Go packages.

Available choices:

- `--shadcn-base radix|base`, default `radix`.
- `--shadcn-preset`, default `nova`.
- `--title`, default title-cased `--name`; keep this human-facing value separate from the ASCII slug used for modules, images, services, and Compose projects.
- `--html-lang`, default `en`; use a simple BCP 47 tag such as `zh-CN` for localized titles.
- `--build-network host|default`, default `default`; select `host` only when the environment requires it.
- `--no-git-init` to leave Git ownership to an enclosing workflow.
- `--into-empty-directory` to publish a staged scaffold into an existing real directory with no entries.
- `--into-empty-git-root` to use the guarded staged handoff above; this implies no new Git initialization.
- `--dry-run` to validate inputs and print resolved choices without checking tools or writing files.

The script checks Node.js, pnpm, Go, and Go Task identity and minimum versions before staging. A failed external command leaves only the named sibling staging directory for inspection; remove only that generated path explicitly before retrying. Treat Docker as an optional post-generation validation boundary.

## Generated baseline

Generate one `apps/api` Go module and one `apps/web` pnpm application connected by `api/openapi.yaml`. Include:

- ginx/oapi-ginx generated request, response, server interface, and route registration code;
- handwritten config, middleware, handler, service, optional PostgreSQL/GORM repository, health endpoint, and graceful HTTP shutdown;
- Hey API generated Fetch client and SDK, one handwritten envelope/error adapter, and a shadcn health screen;
- tracked generated outputs with snapshot-based `task gen:check`;
- development Compose Watch with image-copied source and named dependency caches;
- one repository-root `.env` owner, `task env:init`, and dynamic-port `task verify:containers` smoke tests;
- separate runtime images, Git-derived version tags, and production Compose that neither builds nor pulls;
- root Task commands for generation, checks, builds, development, image creation, and production lifecycle.

Do not add business tables, authentication, domain endpoints, a database container, or CI without a consumer requirement.

## Ownership and generation

The initializer must call `npx create-vite` before writing any web integration file, then call `npx shadcn init` and `npx shadcn add`. Do not add a Vite project, shadcn component implementation, `package.json`, or pnpm lockfile to skill assets.

Assets may replace only project-specific integration files after official initialization: Vite proxy/alias configuration, OpenAPI generator configuration, API adapter, generic health screen, Dockerfile, and Nginx configuration.

Create Go dependency state with `go mod init`, pinned `go get`, `go get -tool`, and `go mod tidy`. Generate both language clients from the shared contract. Never copy generated Go/TypeScript output or a source repository's `go.sum`/`pnpm-lock.yaml` into the skill.

## Version policy

Pin exact initializer and generator versions in `scripts/scaffold.py`. Keep these environment overrides for controlled forward testing:

The validated web baseline pins TypeScript `6.0.3`. Its generated `tsconfig.json` and `tsconfig.app.json` declare relative `paths` aliases without the TypeScript 6-deprecated `baseUrl` option.

```text
SCAFFOLD_CREATE_VITE_VERSION
SCAFFOLD_SHADCN_VERSION
SCAFFOLD_PNPM_VERSION
SCAFFOLD_HEY_API_VERSION
SCAFFOLD_OXLINT_VERSION
SCAFFOLD_TAILWIND_VERSION
SCAFFOLD_TYPESCRIPT_VERSION
SCAFFOLD_REACT_VERSION
SCAFFOLD_REACT_DOM_VERSION
SCAFFOLD_REACT_TYPES_VERSION
SCAFFOLD_REACT_DOM_TYPES_VERSION
SCAFFOLD_NODE_TYPES_VERSION
SCAFFOLD_VITE_VERSION
SCAFFOLD_VITE_REACT_VERSION
SCAFFOLD_GO_VERSION
SCAFFOLD_GINX_VERSION
SCAFFOLD_GIN_VERSION
SCAFFOLD_VIPER_VERSION
SCAFFOLD_GORM_POSTGRES_VERSION
SCAFFOLD_GORM_VERSION
SCAFFOLD_OAPI_GINX_VERSION
```

Pin validated direct web dependencies exactly and generate `.npmrc` with `save-exact=true` so later shadcn additions do not reintroduce ranges. Let the generated lockfile own transitive dependency state. Update pins only after a full temporary-directory forward test. Inspect package-manager peer warnings, generated diffs, shadcn `info`, Go tool declarations, and Docker base compatibility before accepting a new set.

## Validation and maintenance

After changing the script or assets:

1. Run `python scripts/test_scaffold.py`, Python compilation, `--help`, `--dry-run`, invalid title/language, ordinary existing-target, guarded empty-directory, guarded empty-Git-root, dirty-Git-root, missing-tool, wrong-Task-executable, and insufficient-version checks.
2. Scaffold into a fresh absent target, an existing empty directory, and a clean `.git`-only target using real official CLIs. Confirm a localized title and HTML language in README, OpenAPI, and `apps/web/index.html`; confirm a failed external command leaves the requested target untouched.
3. Search the result for template tokens and source-project names.
4. Run `task gen:check`, `task lint`, `task test`, `task build`, `task check`, and `task compose:config`.
5. Verify the no-commit, clean commit, exact Git tag, dirty tree, and invalid tag paths in `resolve-image-tag.sh`.
6. When Docker is available, run generated `task verify:containers`, then seed deliberately stale project-scoped dependency volumes once, verify the diagnostic distinguishes them from incorrect images, run `task dev:reset`, and confirm clean volumes start successfully.
7. Run the skill-creator validator with its YAML dependency provisioned, for example `uv run --with pyyaml python /path/to/skill-creator/scripts/quick_validate.py /path/to/scaffold-go-ts-monorepo`, and forward-test the skill from a fresh agent context.

If external network or Docker daemon access is unavailable, complete the deterministic offline checks and report the skipped integration boundary precisely.
