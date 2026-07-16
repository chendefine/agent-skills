#!/bin/sh

set -eu

repo=${1:-.}
timestamp=$(date '+%Y%m%d%H%M%S')

if commit_id=$(git -C "$repo" rev-parse --short=8 HEAD 2>/dev/null); then
  if test -z "$(git -C "$repo" status --porcelain)"; then
    git_tag=$(git -C "$repo" describe --tags --exact-match HEAD 2>/dev/null || true)
    if test -n "$git_tag"; then
      image_tag=$git_tag
    else
      image_tag=$commit_id
    fi
  else
    image_tag="${commit_id}_${timestamp}"
  fi
else
  image_tag="uncommitted_${timestamp}"
fi

if ! printf '%s\n' "$image_tag" | LC_ALL=C grep -Eq '^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$'; then
  printf 'Git-derived tag is not a valid Docker image tag: %s\n' "$image_tag" >&2
  exit 1
fi

printf '%s\n' "$image_tag"
