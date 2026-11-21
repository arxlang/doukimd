#!/usr/bin/env bash
set -euo pipefail

version="${1:-}"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo 'Expected an existing stable release tag, such as 1.4.8.' >&2
  exit 1
fi

allow_missing_notes=false
notes_only=false
for option in "${@:2}"; do
  case "$option" in
    --allow-missing-notes) allow_missing_notes=true ;;
    --notes-only) notes_only=true ;;
    *) echo "Unsupported recovery option: $option" >&2; exit 1 ;;
  esac
done
if [[ "$allow_missing_notes" == true && "$notes_only" == true ]]; then
  echo 'Notes-only repair cannot defer missing notes.' >&2
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

# Fetch first so repeated recovery attempts preserve existing notes history.
# Only the final push may be deferred by an explicit stable-release override.
git fetch origin '+refs/notes/*:refs/notes/*'
notes_ref="refs/notes/semantic-release-$version"
if ! git notes --ref="$notes_ref" show "$tag" >/dev/null 2>&1; then
  git -c user.name='github-actions[bot]' \
    -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
    notes --ref="$notes_ref" add -m '{"channels":[null]}' "$tag"
fi
if [[ "$allow_missing_notes" == true ]]; then
  # Missing notes mean the default channel to semantic-release. Refuse to
  # defer any other metadata, including unrecognized fields or channels.
  git notes --ref="$notes_ref" show "$tag" | python -c '
import json, sys
if json.load(sys.stdin) != {"channels": [None]}:
    sys.exit("Only default-channel metadata may be deferred.")
'
fi
# Markdown backticks in summaries below are literal formatting.
# shellcheck disable=SC2016
if git push origin "$notes_ref"; then
  if [[ "$notes_only" == true ]]; then
    printf 'Repaired Git notes for %s (%s).\n' "$version" "$source_ref"
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
      printf 'Repaired Git notes `%s` for commit `%s`.\n' \
        "$notes_ref" "$source_ref" >> "$GITHUB_STEP_SUMMARY"
    fi
    exit 0
  fi
else
  status=$?
  if [[ "$allow_missing_notes" != true ]]; then
    echo 'Git-notes push failed; package publication remains blocked.' >&2
    exit "$status"
  fi
  # Retain the expected metadata even if package publication later fails.
  # The workflow uploads this record and exposes the outstanding repair.
  python -c '
import json, sys
json.dump({
    "schema_version": 1,
    "status": "pending",
    "tag": sys.argv[1],
    "commit": sys.argv[2],
    "notes_ref": sys.argv[3],
    "metadata": {"channels": [None]},
}, sys.stdout, indent=2)
print()
' "$version" "$source_ref" "$notes_ref" \
    > "$RUNNER_TEMP/doukimd-release-notes.json"
  {
    printf '### Pending Git-notes repair\n\n'
    printf 'Publication explicitly permits deferred default-channel metadata.\n\n'
    printf -- '- Tag: `%s`\n- Commit: `%s`\n- Ref: `%s`\n\n' \
      "$version" "$source_ref" "$notes_ref"
    printf 'Expected metadata: `{"channels":[null]}`.\n\n'
    printf 'Run **Release** with `resume_tag: %s` and `repair_notes_only: true` to repair it.\n' \
      "$version"
  } >> "$GITHUB_STEP_SUMMARY"
  printf 'notes_pending=true\n' >> "$GITHUB_OUTPUT"
  printf '::warning::Git notes for %s remain pending; explicit recovery permits publication.\n' \
    "$version" >&2
fi

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
