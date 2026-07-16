# Reproducible greenfield scaffolding

Use this reference for `scripts/scaffold.py` and its bundled assets.

## Contents

- [Inputs and safety](#inputs-and-safety)
- [Generated baseline](#generated-baseline)
- [Ownership and generation](#ownership-and-generation)
- [Version policy](#version-policy)
- [Validation and maintenance](#validation-and-maintenance)

## Inputs and safety

Run the script from any directory. Require an absent `--target`; never merge into or overwrite an existing directory. Derive `--name` from the target basename and `--go-module` from `<name>/apps/api` when omitted.

```bash
python scripts/scaffold.py \
  --target /work/example-admin \
  --go-module github.com/example/example-admin/apps/api
```

Available choices:

- `--shadcn-base radix|base`, default `radix`.
- `--shadcn-preset`, default `nova`.
- `--build-network host|default`, default `host` to reproduce the validated baseline.
- `--no-git-init` to leave Git ownership to an enclosing workflow.
- `--dry-run` to validate inputs and print resolved choices without checking tools or writing files.

The script checks required executables before creating the target. A failed external command leaves the partial target for inspection; remove it explicitly before retrying.

## Generated baseline

Generate one `apps/api` Go module and one `apps/web` pnpm application connected by `api/openapi.yaml`. Include:

- ginx/oapi-ginx generated request, response, server interface, and route registration code;
- handwritten config, middleware, handler, service, optional PostgreSQL/GORM repository, health endpoint, and graceful HTTP shutdown;
- Hey API generated Fetch client and SDK, one handwritten envelope/error adapter, and a shadcn health screen;
- tracked generated outputs with snapshot-based `task gen:check`;
- development Compose Watch with image-copied source and named dependency caches;
- separate runtime images, Git-derived version tags, and production Compose that neither builds nor pulls;
- root Task commands for generation, checks, builds, development, image creation, and production lifecycle.

Do not add business tables, authentication, domain endpoints, a database container, or CI without a consumer requirement.

## Ownership and generation

The initializer must call `npx create-vite` before writing any web integration file, then call `npx shadcn init` and `npx shadcn add`. Do not add a Vite project, shadcn component implementation, `package.json`, or pnpm lockfile to skill assets.

Assets may replace only project-specific integration files after official initialization: Vite proxy/alias configuration, OpenAPI generator configuration, API adapter, generic health screen, Dockerfile, and Nginx configuration.

Create Go dependency state with `go mod init`, pinned `go get`, `go get -tool`, and `go mod tidy`. Generate both language clients from the shared contract. Never copy generated Go/TypeScript output or a source repository's `go.sum`/`pnpm-lock.yaml` into the skill.

## Version policy

Pin exact initializer and generator versions in `scripts/scaffold.py`. Keep these environment overrides for controlled forward testing:

```text
SCAFFOLD_CREATE_VITE_VERSION
SCAFFOLD_SHADCN_VERSION
SCAFFOLD_PNPM_VERSION
SCAFFOLD_HEY_API_VERSION
SCAFFOLD_OXLINT_VERSION
SCAFFOLD_TAILWIND_VERSION
SCAFFOLD_TYPESCRIPT_VERSION
SCAFFOLD_GO_VERSION
SCAFFOLD_GINX_VERSION
SCAFFOLD_GIN_VERSION
SCAFFOLD_VIPER_VERSION
SCAFFOLD_GORM_POSTGRES_VERSION
SCAFFOLD_GORM_VERSION
SCAFFOLD_OAPI_GINX_VERSION
```

Update pins only after a full temporary-directory forward test. Inspect package-manager peer warnings, generated diffs, shadcn `info`, Go tool declarations, and Docker base compatibility before accepting a new set.

## Validation and maintenance

After changing the script or assets:

1. Run Python compilation, `--help`, `--dry-run`, invalid-input, existing-target, and missing-tool checks.
2. Scaffold into a fresh temporary directory using real official CLIs.
3. Search the result for template tokens and source-project names.
4. Run `task gen:check`, `task lint`, `task test`, `task build`, `task check`, and `task compose:config`.
5. Verify the no-commit, clean commit, exact Git tag, dirty tree, and invalid tag paths in `resolve-image-tag.sh`.
6. When Docker is available, build both development and runtime targets, start Compose Watch, smoke-test direct and proxied health, then deploy the recorded production images.
7. Run the skill-creator validator and forward-test the skill from a fresh agent context.

If external network or Docker daemon access is unavailable, complete the deterministic offline checks and report the skipped integration boundary precisely.
