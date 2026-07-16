---
name: scaffold-go-ts-monorepo
description: Reproducibly scaffold, reorganize, or troubleshoot a polyglot monorepo with a ginx Go API and React/TypeScript web application, including official Vite and shadcn initialization, OpenAPI code generation, unified Go Task commands, portable Docker Compose Watch development, versioned runtime images, single-host production Compose, optional pnpm workspaces, and affected-path CI. Use when Codex needs to create a Go + React/Vite repository, reproduce the bundled full-stack baseline, simplify or scale an existing monorepo, establish a shared API contract, or debug its development and container conventions.
---

# Scaffold Go + TypeScript Monorepo

Build one polyglot monorepo with separate TypeScript and Go toolchain domains. Connect them through a versioned contract and stable root commands without forcing either ecosystem into the other's module system.

## Read the references

Read [references/architecture.md](references/architecture.md) before proposing a tree or changing files. Start from its minimal shape, then add only the scale-out branches required by the user or existing repository.

Read [references/containers.md](references/containers.md) before creating, changing, or debugging Dockerfiles, Compose configuration, source synchronization, or container build networking.

Read [references/scaffolding.md](references/scaffolding.md) before running or changing the bundled greenfield initializer, its parameters, version pins, or template assets.

## Scaffold a new repository

Prefer the bundled initializer for a new, absent target directory:

```bash
python scripts/scaffold.py --target /path/to/new-project --go-module github.com/acme/new-project/apps/api
```

Run `--dry-run` first when inputs or prerequisites are uncertain. Let the script invoke official Vite and shadcn CLIs, generate manifests and lockfiles, render the reusable backend and deployment assets, generate both OpenAPI consumers, and run `task check`. Do not replace those steps with copied frontend scaffolds or fabricated dependency state.

Use the manual workflow below for an existing repository, a non-default topology, or a partial reorganization.

## Follow the workflow

1. Inspect the repository before editing.
   - Read applicable `AGENTS.md` files and existing manifests, lockfiles, CI, container, contract, deployment, and task-runner configuration.
   - Determine whether the task is greenfield scaffolding or an in-place reorganization.
   - Inspect `git status`, including staged files, before replacing generated output or configuration.
   - Confirm executable identity as well as version for `go`, Node.js, pnpm, Docker Compose, and Go Task. Do not assume a command named `task` is Go Task; run a harmless Taskfile-aware command such as `task --list` once a Taskfile exists.
   - Inspect `docker context show` and rendered mount sources when container development is in scope. A local-looking CLI path does not prove that the Docker daemon can read it.
   - Preserve working tool choices and user changes unless they conflict with an explicit requirement.

2. Resolve choices that change ownership boundaries.
   - Default to `apps/web` plus `apps/api` for a browser application and Go HTTP API. Use responsibility-specific names for additional deployables.
   - Default to `api/openapi.yaml` as the cross-language source of truth.
   - Follow an available framework-specific skill before selecting or replacing the Go router, runtime, or generator. Make framework response envelopes, base paths, statuses, and error rendering agree with the shared wire contract.
   - Generate TypeScript artifacts inside `apps/web` when it is the only TypeScript consumer. Create `packages/api-client` only when two or more TypeScript applications or tools consume the same client.
   - Create a pnpm workspace only when multiple TypeScript packages, a root-owned JavaScript toolchain, or a deliberate root lockfile policy requires one.
   - Use Compose for local development by default. Add production Compose overrides only for an explicitly single-host Compose deployment; otherwise follow the selected deployment platform.
   - Choose a source-update model deliberately. Prefer image-copied source plus Compose Watch when the daemon may run remotely or in a different mount namespace; use bind mounts only after proving the daemon sees the same files.
   - Retain the repository's CI provider. Use Woodpecker defaults only when Woodpecker is selected or already present.
   - For the bundled full baseline, retain its optional PostgreSQL boundary and single-host production Compose unless the user requests a smaller profile. Keep business schemas, authentication, and business UI out of the scaffold.

3. Design the smallest useful tree.
   - Include a file or directory only when it has an immediate owner and role.
   - Omit optional `packages/`, `pkg/`, root JavaScript workspace files, database initialization, production deployment, and documentation branches until required.
   - Keep deployables in `apps/`, reusable TypeScript libraries in `packages/`, the shared API contract in `api/`, and deployment configuration in `deploy/`.

4. Implement from boundaries inward.
   - Establish the contract and pin code-generation tools before generating either language's artifacts.
   - Inspect generator peer requirements before accepting versions from ecosystem scaffolds. Resolve incompatible TypeScript or Node.js ranges and pin the selected package manager in `package.json`.
   - Create the Go module, executable entry point, and only the internal packages required by current behavior.
   - Pin Go generators with the module's supported tool mechanism, remove superseded tool declarations, and run `go mod tidy` after runtime imports and generated code have settled.
   - Create the TypeScript application with feature-based business code and app-local generated API code.
   - Create greenfield React code with the official Vite CLI, then initialize shadcn with its official CLI. Treat generated shadcn components as source, but do not bundle or copy a stale Vite/shadcn application skeleton into the skill.
   - Add stable root task commands after native Go and TypeScript commands work.
   - Make `gen:check` independent of an existing Git commit. In a new repository, snapshot tracked outputs before regeneration and compare every generated file afterward; plain `git diff` does not detect untracked output.
   - Put each primary Dockerfile beside its application, then select build context from the files that its `COPY` instructions require and add matching ignore rules.
   - Configure build networking at the invocation or Compose build layer when required; do not confuse build networking with runtime `network_mode`.
   - Add CI last. Make it call local task commands and model every shared input that can affect each application.
   - Use ecosystem generators for canonical manifests and lockfiles. Never fabricate generated dependency state.

5. Verify the scaffold proportionally.
   - Inspect the final tree and confirm module, workspace, contract, generated-output, Compose, and Docker context paths agree.
   - Run formatters and configuration parsers before broader checks.
   - Run generation, lint, test, build, and the aggregate `task check` command when available.
   - Render each supported Compose combination from every documented entry directory, including the repository root and the directory containing `compose.yaml` when both are supported.
   - Build every supported Docker target with its configured network policy. Distinguish dependency-download failures from Dockerfile or compiler failures before changing repository defaults.
   - Start the real Compose stack with the documented command, inspect container working directories and mounts, wait for health, and exercise the API both directly and through the web proxy. Configuration rendering alone is insufficient.
   - If source bind mounts are used, verify a sentinel file such as `go.mod` or `package.json` inside the running container. If the rendered source is correct but the target is empty, treat it as a daemon/CLI filesystem visibility problem and use the container reference diagnostics.
   - Exercise Compose Watch when it is the documented development loop; confirm watch mode starts and that dependency-file changes rebuild rather than merely sync.
   - Verify the chosen generated-code policy: either regenerate tracked artifacts and require a clean diff, or generate untracked artifacts before every consuming build.
   - Validate CI syntax and confirm path filters cover shared contracts, lockfiles, root tooling, Docker inputs, and workflow files.
   - Report skipped checks and missing prerequisites explicitly.

## Preserve these invariants

- Treat the repository as one polyglot monorepo with language-specific toolchain domains; do not make JavaScript tooling own Go modules.
- Name `apps/` entries by deployable responsibility or delivery channel, such as `web`, `api`, `admin`, `worker`, and `scheduler`.
- Keep `go.mod` in `apps/api` for a single Go module. Add `go.work` only when multiple local Go modules need workspace coordination.
- Keep server implementation private under `internal/` and executable entry points under `cmd/`. Preserve dependency boundaries, but choose layered, domain-based, or vertical-slice organization according to actual complexity; do not pre-create empty layers.
- Keep the API contract authoritative. Generate Go and TypeScript artifacts from the same revision, pin generator versions, and never edit generated files manually.
- Keep the OpenAPI wire contract authoritative after framework behavior is applied. Do not let automatic response envelopes, proxy rewrites, or success-status defaults make generated clients disagree with real HTTP responses.
- Choose one generated-code lifecycle and enforce it consistently in local commands and CI.
- Put versioned production migrations in source control. Do not use ORM auto-migration as the production migration mechanism.
- Prefer `compose.yaml` naming. Treat local development and production deployment as separate concerns.
- Make Docker build context explicit and keep it minimal with `.dockerignore` or Dockerfile-specific ignore files.
- Do not infer bind-mount correctness from a successful image build: the CLI sends build contexts, while the daemon resolves bind sources.
- Keep source synchronization portable. Use named volumes for dependency/build caches, not as substitutes for application source ownership.
- Use host build networking only when the environment requires or the user requests it, expose that choice in Compose and stable tasks, and avoid silently switching to an untrusted dependency proxy.
- Make CI path filters dependency-aware rather than application-directory-only. Define behavior for push, pull request, tag, manual, and empty-change events.
- Keep independent Woodpecker workflows artifact-independent. Transfer cross-workflow outputs through a registry or artifact store and mark filtered dependencies optional where appropriate.
- Give developers and CI the same stable commands, including `task gen`, `task gen:check`, `task lint`, `task test`, `task build`, and `task check` as applicable.
- Verify those commands with Go Task itself. Avoid shelling out recursively to an ambiguous `task` executable from multiline Taskfile commands when an internal Task dependency or native command is sufficient.
- Keep secrets out of the repository. Give each `.env.example` a clear owner and commit only non-secret placeholders.

## Handle existing repositories safely

- Map current paths, import relationships, generated artifacts, Docker contexts, and CI affected inputs before moving anything.
- Migrate in small buildable steps and verify references after each boundary change.
- Preserve an established contract directory or workspace policy when renaming would add churn without improving ownership.
- Avoid unrelated formatting, framework migrations, dependency upgrades, or deployment-provider changes.

## Hand off the result

Summarize whether the bundled initializer or manual workflow was used, the selected parameters and version overrides, generated-code lifecycle, source synchronization model, build contexts and networking, entry commands, and validation results. Identify only unresolved external values such as module path, registry, domains, credentials, or daemon path-sharing requirements.
