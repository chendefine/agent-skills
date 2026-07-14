---
name: scaffold-go-ts-monorepo
description: Scaffold or reorganize a polyglot monorepo with a Go API and TypeScript web application, including app boundaries, app-local or reusable OpenAPI code generation, optional pnpm workspaces, unified task commands, Docker Compose development environments, explicit Docker build contexts, and affected-path Woodpecker CI. Use when Codex needs to create a Go + React/Vite repository, simplify or scale an existing full-stack monorepo, establish a shared API contract, or implement its development, container, and CI conventions.
---

# Scaffold Go + TypeScript Monorepo

Build one polyglot monorepo with separate TypeScript and Go toolchain domains. Connect them through a versioned contract and stable root commands without forcing either ecosystem into the other's module system.

## Read the architecture reference

Read [references/architecture.md](references/architecture.md) before proposing a tree or changing files. Start from its minimal shape, then add only the scale-out branches required by the user or existing repository.

## Follow the workflow

1. Inspect the repository before editing.
   - Read applicable `AGENTS.md` files and existing manifests, lockfiles, CI, container, contract, deployment, and task-runner configuration.
   - Determine whether the task is greenfield scaffolding or an in-place reorganization.
   - Preserve working tool choices and user changes unless they conflict with an explicit requirement.

2. Resolve choices that change ownership boundaries.
   - Default to `apps/web` plus `apps/api` for a browser application and Go HTTP API. Use responsibility-specific names for additional deployables.
   - Default to `api/openapi.yaml` as the cross-language source of truth.
   - Generate TypeScript artifacts inside `apps/web` when it is the only TypeScript consumer. Create `packages/api-client` only when two or more TypeScript applications or tools consume the same client.
   - Create a pnpm workspace only when multiple TypeScript packages, a root-owned JavaScript toolchain, or a deliberate root lockfile policy requires one.
   - Use Compose for local development by default. Add production Compose overrides only for an explicitly single-host Compose deployment; otherwise follow the selected deployment platform.
   - Retain the repository's CI provider. Use Woodpecker defaults only when Woodpecker is selected or already present.

3. Design the smallest useful tree.
   - Include a file or directory only when it has an immediate owner and role.
   - Omit optional `packages/`, `pkg/`, root JavaScript workspace files, database initialization, production deployment, and documentation branches until required.
   - Keep deployables in `apps/`, reusable TypeScript libraries in `packages/`, the shared API contract in `api/`, and deployment configuration in `deploy/`.

4. Implement from boundaries inward.
   - Establish the contract and pin code-generation tools before generating either language's artifacts.
   - Create the Go module, executable entry point, and only the internal packages required by current behavior.
   - Create the TypeScript application with feature-based business code and app-local generated API code.
   - Add stable root task commands after native Go and TypeScript commands work.
   - Put each primary Dockerfile beside its application, then select build context from the files that its `COPY` instructions require and add matching ignore rules.
   - Add CI last. Make it call local task commands and model every shared input that can affect each application.
   - Use ecosystem generators for canonical manifests and lockfiles. Never fabricate generated dependency state.

5. Verify the scaffold proportionally.
   - Inspect the final tree and confirm module, workspace, contract, generated-output, Compose, and Docker context paths agree.
   - Run formatters and configuration parsers before broader checks.
   - Run generation, lint, test, build, and the aggregate `task check` command when available.
   - Render each supported Compose combination with `docker compose config`.
   - Verify the chosen generated-code policy: either regenerate tracked artifacts and require a clean diff, or generate untracked artifacts before every consuming build.
   - Validate CI syntax and confirm path filters cover shared contracts, lockfiles, root tooling, Docker inputs, and workflow files.
   - Report skipped checks and missing prerequisites explicitly.

## Preserve these invariants

- Treat the repository as one polyglot monorepo with language-specific toolchain domains; do not make JavaScript tooling own Go modules.
- Name `apps/` entries by deployable responsibility or delivery channel, such as `web`, `api`, `admin`, `worker`, and `scheduler`.
- Keep `go.mod` in `apps/api` for a single Go module. Add `go.work` only when multiple local Go modules need workspace coordination.
- Keep server implementation private under `internal/` and executable entry points under `cmd/`. Preserve dependency boundaries, but choose layered, domain-based, or vertical-slice organization according to actual complexity; do not pre-create empty layers.
- Keep the API contract authoritative. Generate Go and TypeScript artifacts from the same revision, pin generator versions, and never edit generated files manually.
- Choose one generated-code lifecycle and enforce it consistently in local commands and CI.
- Put versioned production migrations in source control. Do not use ORM auto-migration as the production migration mechanism.
- Prefer `compose.yaml` naming. Treat local development and production deployment as separate concerns.
- Make Docker build context explicit and keep it minimal with `.dockerignore` or Dockerfile-specific ignore files.
- Make CI path filters dependency-aware rather than application-directory-only. Define behavior for push, pull request, tag, manual, and empty-change events.
- Keep independent Woodpecker workflows artifact-independent. Transfer cross-workflow outputs through a registry or artifact store and mark filtered dependencies optional where appropriate.
- Give developers and CI the same stable commands, including `task gen`, `task gen:check`, `task lint`, `task test`, `task build`, and `task check` as applicable.
- Keep secrets out of the repository. Give each `.env.example` a clear owner and commit only non-secret placeholders.

## Handle existing repositories safely

- Map current paths, import relationships, generated artifacts, Docker contexts, and CI affected inputs before moving anything.
- Migrate in small buildable steps and verify references after each boundary change.
- Preserve an established contract directory or workspace policy when renaming would add churn without improving ownership.
- Avoid unrelated formatting, framework migrations, dependency upgrades, or deployment-provider changes.

## Hand off the result

Summarize the minimal versus optional branches selected, generated-code lifecycle, build contexts, CI affected inputs, entry commands, and validation results. Identify only unresolved external values such as module path, registry, domains, or credentials.
