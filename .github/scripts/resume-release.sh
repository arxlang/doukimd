#!/usr/bin/env bash
set -euo pipefail

version="${1:-}"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo 'Expected an existing stable release tag, such as 1.4.8.' >&2
  exit 1
fi

tag="refs/tags/$version"
source_ref="$(git rev-parse --verify "$tag^{commit}")"
git merge-base --is-ancestor "$source_ref" refs/remotes/origin/main
source_directory="$(mktemp -d "$RUNNER_TEMP/doukimd-release.XXXXXX")"
trap 'rm -rf "$source_directory"' EXIT
git archive "$source_ref" | tar -x -C "$source_directory"
if [[ "$(cd "$source_directory" && poetry version --short)" != "$version" ]]; then
  echo 'The tagged package version does not match the requested release.' >&2
  exit 1
fi

# Finish notes before publishing packages. Fetch first so repeated recovery
# attempts keep existing notes history and never need a force push.
git fetch origin '+refs/notes/*:refs/notes/*'
notes_ref="refs/notes/semantic-release-$version"
if ! git notes --ref="$notes_ref" show "$tag" >/dev/null 2>&1; then
  git -c user.name='github-actions[bot]' \
    -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
    notes --ref="$notes_ref" add -m '{"channels":[null]}' "$tag"
fi
git push origin "$notes_ref"

cd "$source_directory"
awk -v version="$version" '
  index($0, "## [" version "](") == 1 { found = 1; print; next }
  found && /^## / { exit }
  found { print }
' docs/changelog.md > release-notes.md
test -s release-notes.md
poetry build
poetry publish --skip-existing --no-interaction

if ! gh release view "$version" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  gh release create "$version" --repo "$GITHUB_REPOSITORY" \
    --verify-tag --title "$version" --notes-file release-notes.md
fi
published_assets="$(gh release view "$version" --repo "$GITHUB_REPOSITORY" \
  --json assets --jq '.assets[].name')"
for artifact in dist/*.whl dist/*.tar.gz; do
  if ! printf '%s\n' "$published_assets" | grep -Fqx -- "${artifact##*/}"; then
    gh release upload "$version" "$artifact" --repo "$GITHUB_REPOSITORY"
  fi
done
printf 'source_ref=%s\n' "$source_ref" >> "$GITHUB_OUTPUT"
