# Containers and Compose development

Use this reference to choose a portable development loop, configure build networking, diagnose empty mounts, and validate the running stack.

## Contents

- [Separate build and runtime concerns](#separate-build-and-runtime-concerns)
- [Choose a source-update model](#choose-a-source-update-model)
- [Use Compose Watch portably](#use-compose-watch-portably)
- [Configure build networking](#configure-build-networking)
- [Diagnose an empty source mount](#diagnose-an-empty-source-mount)
- [Diagnose stale dependency volumes](#diagnose-stale-dependency-volumes)
- [Verify the actual stack](#verify-the-actual-stack)

## Separate build and runtime concerns

Keep each Dockerfile beside its application and use the smallest build context containing every `COPY` input. Remember that Docker uses different data paths:

- The Docker CLI packages and sends a build context to the daemon.
- The Docker daemon resolves runtime bind-mount source paths itself.
- A successful `docker build` therefore does not prove that a later bind mount from the same displayed path contains files.

Use multi-stage Dockerfiles with an explicit development target and runtime target. Build and test both; a Compose file targeting `development` does not validate the production `runtime` stage.

## Choose a source-update model

Choose one model instead of combining them accidentally:

| Model | Use when | Tradeoff |
| --- | --- | --- |
| Image-copied source plus rebuild | Simplicity matters more than live updates | Portable but slower feedback |
| Bind-mounted source | The daemon is local and proven to share the CLI filesystem | Fast, but fails with remote daemons, sandboxes, VMs, and mount namespaces |
| Image-copied source plus Compose Watch | Compose 2.22+ is available or daemon path visibility is uncertain | Portable live updates with explicit sync/rebuild rules |

Keep dependency and compiler caches in named volumes. Do not mount a named volume over the whole application directory, because it hides source copied into the image.

## Use Compose Watch portably

Copy source into the development image first, then let the Compose CLI synchronize changes:

```yaml
services:
  api:
    build:
      context: ../../apps/api
      dockerfile: Dockerfile
      target: development
    volumes:
      - go-mod-cache:/go/pkg/mod
      - go-build-cache:/root/.cache/go-build
    develop:
      watch:
        - action: sync+restart
          path: ../../apps/api
          target: /app
          initial_sync: true
          ignore:
            - bin/
            - go.mod
            - go.sum
        - action: rebuild
          path: ../../apps/api/go.mod
        - action: rebuild
          path: ../../apps/api/go.sum

  web:
    build:
      context: ../../apps/web
      dockerfile: Dockerfile
      target: development
    volumes:
      - web-node-modules:/app/node_modules
    develop:
      watch:
        - action: sync
          path: ../../apps/web
          target: /app
          initial_sync: true
          ignore:
            - dist/
            - node_modules/
            - package.json
            - pnpm-lock.yaml
        - action: rebuild
          path: ../../apps/web/package.json
        - action: rebuild
          path: ../../apps/web/pnpm-lock.yaml
```

Use `sync+restart` for a Go process without an in-process reloader and `sync` for a Vite development server. Rebuild when dependency manifests change. Confirm the image contains `stat`, `mkdir`, and `rmdir`, and ensure the container user can write to the sync target.

Use `COMPOSE_MENU=false` for non-interactive Watch verification. Do not combine `up --watch` with `--no-build`; supported Compose releases reject that option pair. Judge a synchronized restart by the new container start time and a subsequent health check rather than by the old process's exit code.

Expose the watch loop through a stable command such as:

```yaml
tasks:
  dev:
    cmds:
      - docker compose -f deploy/compose/compose.yaml up --build --watch
```

Keep ordinary `docker compose up` functional without watch; it should run the source already copied into the image.

Generate `task verify:containers` for the bundled baseline. Let it allocate host ports dynamically, verify direct and proxied health, exercise Watch with temporary source probes, build both runtime targets, start production Compose, and clean containers in a trap without deleting named dependency caches.

## Configure build networking

Treat build networking as an environmental input. Use the default network unless the user or environment requires host access. When host build networking is required, express it consistently:

```yaml
services:
  api:
    build:
      context: ../../apps/api
      network: host
```

```bash
docker build --network=host --target runtime -t my-api:local apps/api
```

Do not replace build networking with runtime `network_mode: host`. Do not bake environment-specific third-party proxies into the repository merely to make one validation pass. Retry a suspected transient failure, identify the exact failing download layer, then either use the approved build network or report the external prerequisite.

For the bundled baseline, expose one root `.env` value named `BUILD_NETWORK`. Apply it to Compose development builds, runtime `docker build` commands, and `task verify:containers`. Keep the scaffold parameter's selected value as the generated default while allowing an explicit local override after diagnosing the failing dependency layer.

## Diagnose an empty source mount

When a process reports that `go.mod`, `package.json`, or another expected file is missing:

1. Render from the same directory the developer uses:

   ```bash
   docker compose config
   ```

2. Inspect the failed container rather than trusting the rendered YAML:

   ```bash
   docker inspect <container> --format '{{json .Config.WorkingDir}} {{json .Config.Cmd}} {{json .Mounts}}'
   ```

3. Inspect the target through a one-off container:

   ```bash
   docker compose run --rm --no-deps --entrypoint /bin/sh api -c 'pwd; ls -la /app; find /app -maxdepth 2 -name go.mod -print'
   ```

4. If needed, bind the same source into an already available local image. Avoid introducing an unrelated image pull while diagnosing path visibility.

If Compose renders the intended absolute source and `docker inspect` reports that source, but the target is empty, the daemon and CLI do not share the same filesystem view. Common causes include remote Docker contexts, development sandboxes, Docker Desktop/VM sharing, and separate mount namespaces. Fix daemon path sharing or remove the source bind and use image-copied source plus Compose Watch.

## Diagnose stale dependency volumes

Treat a named dependency cache separately from source and image contents. A previously created Compose project can retain a volume whose Go modules or pnpm links no longer match the current `go.sum` or lockfile. Typical symptoms are runtime dependency downloads, old module versions, or a package missing only after the cache volume is mounted.

1. Inspect the development image without Compose volumes and assert that current dependencies exist. If the image is wrong, rebuild it and diagnose its dependency layer; do not clear a volume to hide an incorrect image.
2. Inspect the failed container's mounts and the named volumes' creation timestamps with `docker volume inspect`.
3. Inspect cache contents using an already available project image when possible. Avoid pulling an unrelated diagnostic image.
4. Compare the cached versions with the current `go.sum` or `pnpm-lock.yaml`. Do not infer staleness from age alone.
5. After confirming that the volumes belong only to the disposable development project, run `task dev:reset` or the equivalent project-scoped `docker compose down --volumes --remove-orphans` command.
6. Rebuild and start again, then assert both manifest sentinels and representative current dependencies inside the running containers.

Never delete shared or production volumes as a generic dependency fix. Do not change Dockerfiles, runtime networking, or dependency proxies until image-versus-volume inspection identifies the faulty layer.

## Verify the actual stack

Validate more than syntax:

1. Run `docker compose config` from every documented entry directory.
2. Build development and production targets using the documented network policy.
3. Start from a clean project state with the exact documented command.
4. Wait for API health before evaluating dependent services.
5. Inspect `WorkingDir`, `Cmd`, and `Mounts`; assert that `go.mod` and `package.json` exist inside their containers.
6. Assert representative current dependencies inside the image and the mounted cache; diagnose and reset only stale project-scoped volumes when they differ.
7. Call the API directly and through the web development or production proxy.
8. Start watch mode and confirm it reports that watching is enabled.
9. Change a harmless source file when practical and confirm sync or restart behavior; confirm manifest changes select rebuild.
10. Build runtime images and smoke-test them. Publish to a dynamically assigned host port when fixed ports may already be occupied.

Prefer the generated `task verify:containers` implementation for this matrix instead of recreating an ad hoc sequence. Keep `task dev` as the interactive developer loop and do not add verification-only flags to it.

If `--force-recreate` reports an old container identifier while newly created containers become healthy, inspect `docker compose ps --all` and logs before changing code. Clean the project with `docker compose down --remove-orphans`, then reproduce from a clean state to separate a Compose lifecycle race from an application failure.
