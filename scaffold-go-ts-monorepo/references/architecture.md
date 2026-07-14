# Go + TypeScript monorepo architecture

Use this reference to select boundaries and paths. Start minimal; add workspace packages, production deployment, or extra layers only when a current consumer requires them.

## Contents

- [Go + TypeScript monorepo architecture](#go--typescript-monorepo-architecture)
  - [Contents](#contents)
  - [Core model](#core-model)
  - [Minimal default tree](#minimal-default-tree)
  - [Scale-out branches](#scale-out-branches)
  - [Application naming](#application-naming)
  - [TypeScript boundary](#typescript-boundary)
  - [Go API boundary](#go-api-boundary)
  - [Contract and code generation](#contract-and-code-generation)
  - [Containers and deployment](#containers-and-deployment)
  - [CI affected paths](#ci-affected-paths)
  - [Environment ownership](#environment-ownership)
  - [Unified commands](#unified-commands)

## Core model

Treat the repository as one polyglot monorepo with two toolchain domains:

- Let pnpm own TypeScript packages when a workspace is useful.
- Let Go modules own Go compilation and `internal/` visibility.
- Join both domains with a versioned contract, root task runner, containers, and CI.

Do not assume that one TypeScript application is itself a pnpm monorepo. A pnpm workspace is useful for multiple packages, root-owned JavaScript tooling, or a deliberate root lockfile policy; otherwise keep pnpm state with `apps/web`.

## Minimal default tree

Use this shape for one web application and one Go API:

```text
myapp/
├── apps/
│   ├── web/
│   │   ├── src/api/generated/
│   │   ├── package.json
│   │   ├── pnpm-lock.yaml
│   │   └── Dockerfile
│   └── api/
│       ├── cmd/server/main.go
│       ├── internal/
│       ├── migrations/
│       ├── go.mod
│       └── Dockerfile
├── api/
│   └── openapi.yaml
├── deploy/
│   └── compose/
│       ├── compose.yaml
│       └── compose.dev.yaml
├── .woodpecker/
│   ├── web.yaml
│   └── api.yaml
├── Taskfile.yml
├── .dockerignore
├── .env.example
├── .editorconfig
├── .gitignore
└── README.md
```

Omit any empty optional branch.

## Scale-out branches

Add a root pnpm workspace when multiple TypeScript packages or root-owned JavaScript tools need coordinated installation:

```text
myapp/
├── apps/
│   ├── web/
│   └── admin/
├── packages/
│   └── api-client/
├── package.json
├── pnpm-workspace.yaml
└── pnpm-lock.yaml
```

Call the package `api-client` when it contains both generated types and request functions. Use `api-types` only for a genuinely type-only package. Avoid extracting a package for a single consumer.

Add `go.work` only when the repository contains multiple Go modules that must resolve together during local development. Keep a single module rooted at `apps/api` otherwise.

## Application naming

Name children of `apps/` by deployable responsibility or delivery channel:

- Use `web` for the browser-delivered application.
- Use `api` for a service whose primary responsibility is an HTTP API.
- Use `server` when the deployable has broader responsibilities than an API.
- Add names such as `admin`, `mobile`, `worker`, and `scheduler` as the repository grows.
- Reserve `frontend` plus `backend` for a deliberately fixed pair where directness matters more than extensibility.

Allow the Go executable to remain `apps/api/cmd/server/main.go`. The repository-level `api` name identifies a deployable; the Go-level `server` name identifies a binary.

## TypeScript boundary

Keep business-specific frontend code together under `features/<domain>` and reserve top-level folders for cross-feature code:

```text
apps/web/src/
├── api/
│   ├── generated/
│   └── client.ts
├── components/
│   ├── ui/
│   └── common/
├── features/<domain>/
├── hooks/
├── lib/
├── routes/
├── stores/
└── types/
```

Keep the generated transport schema/client in `api/generated` and authentication, base URL, retries, and error normalization in the handwritten `api/client.ts`. Treat generated shadcn components as repository source. Follow the installed framework versions instead of assuming historical Tailwind or shadcn configuration.

## Go API boundary

Start with the stable Go boundaries and add packages only as behavior requires them:

```text
apps/api/
├── cmd/server/main.go
├── internal/
├── migrations/
├── go.mod
├── go.sum
├── Dockerfile
├── .air.toml
└── .env.example
```

Keep server logic in `internal/` and commands in `cmd/`. Choose one internal organization based on the application:

- Use a small package or vertical slice for a small service.
- Use feature/domain packages when business capabilities are the main boundary.
- Use handler/service/repository layers when protocol, business, and persistence changes genuinely need independent seams.

Do not create all layers preemptively. Keep HTTP concerns out of persistence code and database concerns out of transport code regardless of folder style. Separate DTOs from persistence models when their lifecycles differ. Create a public Go module instead of a generic `pkg/` directory when code truly needs external consumers.

## Contract and code generation

Prefer `api/openapi.yaml` as the cross-language source of truth for a new repository:

- Generate Go interfaces and transport types into `apps/api/internal/api/generated`.
- Generate TypeScript types and a typed client into `apps/web/src/api/generated` for a single consumer.
- Generate into `packages/api-client` only when multiple TypeScript consumers import it.
- Pin generator versions in the owning Go or pnpm dependency configuration.
- Mark generated files and never edit them manually.

Choose exactly one generated-code lifecycle:

1. **Tracked outputs:** commit generated files and make `task gen:check` run generation followed by a clean-diff assertion.
2. **Untracked outputs:** ignore generated files and make every build, test, container build, and CI job generate them before consumption.

Prefer tracked outputs when consumers should build without installing generators. Prefer untracked outputs when generation is fast, hermetic, and guaranteed by every entry point.

If Go types are intentionally authoritative, generate TypeScript from Go instead. Do not hand-maintain equivalent schemas on both sides except in a deliberately tiny prototype.

## Containers and deployment

Use current Compose naming:

```text
deploy/compose/
├── compose.yaml
├── compose.dev.yaml
└── compose.prod.yaml   # only for an explicit single-host Compose deployment
```

Use Compose as the default local orchestration layer. Add `compose.prod.yaml` only when production actually runs through Compose; generate platform-specific deployment configuration for Kubernetes or a PaaS instead.

Keep primary Dockerfiles beside their applications, but choose build context independently. A web build that copies a root lockfile or workspace configuration needs the repository root as context:

```yaml
services:
  web:
    build:
      context: ../..
      dockerfile: apps/web/Dockerfile
  api:
    build:
      context: ../../apps/api
      dockerfile: Dockerfile
```

Use the smallest context that contains every required input. Add a root `.dockerignore` for root-context builds or a Dockerfile-specific ignore file for specialized contexts. Use multi-stage builds and render every supported file combination with `docker compose config`.

## CI affected paths

Filter workflows by their complete dependency surface, not only their application directory. For Woodpecker, model push/pull-request paths separately from tag and manual events:

```yaml
# .woodpecker/web.yaml
when:
  - event: [push, pull_request]
    path:
      include:
        - "apps/web/**"
        - "packages/api-client/**"
        - "api/**"
        - "package.json"
        - "pnpm-workspace.yaml"
        - "pnpm-lock.yaml"
        - "Taskfile.yml"
        - ".dockerignore"
        - ".woodpecker/web.yaml"
      on_empty: false
  - event: [tag, manual]
```

```yaml
# .woodpecker/api.yaml
when:
  - event: [push, pull_request]
    path:
      include:
        - "apps/api/**"
        - "api/**"
        - "Taskfile.yml"
        - ".dockerignore"
        - ".woodpecker/api.yaml"
      on_empty: false
  - event: [tag, manual]
```

Remove nonexistent optional paths from a minimal repository rather than creating files to satisfy the examples. Include every actually imported shared package plus deployment and shared tooling paths in whichever workflow consumes them.

Assume workflows run independently and do not share a filesystem. Transfer images or artifacts through external storage. Mark a filtered workflow dependency optional when a downstream workflow may run without it. Validate against the installed Woodpecker version and its linter.

## Environment ownership

Give each example file one scope:

- Use root `.env.example` for Compose wiring and cross-service values.
- Use `apps/web/.env.example` only for browser-build variables.
- Use `apps/api/.env.example` only for API variables used outside Compose or documented at the application boundary.
- Avoid defining the same variable with conflicting defaults in multiple files.

Commit placeholders and descriptions, never secrets.

## Unified commands

Expose stable root commands through Taskfile or the repository's chosen equivalent:

```text
task dev         Start the local web, API, and database environment
task gen         Regenerate contract-derived code
task gen:check   Verify generated outputs follow the selected lifecycle
task migrate     Apply versioned database migrations
task lint        Lint both toolchain domains
task test        Test both toolchain domains
task build       Build applications or images
task check       Run the complete local/CI quality gate
```

Make commands thin wrappers around native Go, pnpm, code-generation, and Compose commands. Make CI call the same entry points instead of maintaining a second command graph.
