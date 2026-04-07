#!/usr/bin/env bash
#
# bump-version.sh — Bump the tensorlake-skills SemVer version.
#
# Usage:
#   ./scripts/bump-version.sh <major|minor|patch> [--sdk <sdk_version>]
#
# What it does:
#   1. Reads the current version from SKILL.md frontmatter
#   2. Bumps major, minor, or patch
#   3. Updates version in SKILL.md and AGENTS.md
#   4. Stamps CHANGELOG.md [Unreleased] section with the new version and date
#   5. Creates a git tag vX.Y.Z
#
# Examples:
#   ./scripts/bump-version.sh minor                  # 2.0.0 -> 2.1.0
#   ./scripts/bump-version.sh patch --sdk 0.5.0      # 2.1.0 -> 2.1.1, notes SDK 0.5.0
#   ./scripts/bump-version.sh major                  # 2.1.1 -> 3.0.0

set -euo pipefail

# Portable in-place sed (macOS uses BSD sed, Linux uses GNU sed)
sedi() {
    if sed --version >/dev/null 2>&1; then
        sed -i "$@"        # GNU sed
    else
        sed -i '' "$@"     # BSD sed (macOS)
    fi
}

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_FILE="$REPO_ROOT/SKILL.md"
AGENTS_FILE="$REPO_ROOT/AGENTS.md"
CHANGELOG_FILE="$REPO_ROOT/CHANGELOG.md"
PLUGIN_FILE="$REPO_ROOT/.claude-plugin/plugin.json"

# ── Parse arguments ──────────────────────────────────────────────────────────

BUMP_TYPE="${1:-}"
SDK_VERSION=""

shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --sdk)
            if [[ $# -lt 2 ]]; then
                echo "Error: --sdk requires a version argument" >&2
                exit 1
            fi
            SDK_VERSION="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: $0 <major|minor|patch> [--sdk <sdk_version>]" >&2
    exit 1
fi

# ── Read current version from SKILL.md ───────────────────────────────────────

CURRENT_VERSION=$(sed -n 's/^[[:space:]]*version:[[:space:]]*\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' "$SKILL_FILE")

if [[ -z "$CURRENT_VERSION" ]]; then
    echo "Error: Could not find version in $SKILL_FILE" >&2
    exit 1
fi

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# ── Bump ─────────────────────────────────────────────────────────────────────

case "$BUMP_TYPE" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
TODAY=$(date +%Y-%m-%d)

echo "Bumping: $CURRENT_VERSION -> $NEW_VERSION ($BUMP_TYPE)"

# ── Update SKILL.md ──────────────────────────────────────────────────────────

sedi "s/version: ${CURRENT_VERSION}/version: ${NEW_VERSION}/" "$SKILL_FILE"
echo "  Updated $SKILL_FILE"

# ── Update AGENTS.md ─────────────────────────────────────────────────────────

if grep -q "<!-- version:" "$AGENTS_FILE" 2>/dev/null; then
    sedi "s/<!-- version: .* -->/<!-- version: ${NEW_VERSION} -->/" "$AGENTS_FILE"
else
    # Insert version comment after the first heading
    sedi "1 s/^# Tensorlake SDK$/# Tensorlake SDK\n<!-- version: ${NEW_VERSION} -->/" "$AGENTS_FILE"
fi
echo "  Updated $AGENTS_FILE"

# ── Update plugin.json ──────────────────────────────────────────────────────

if [[ -f "$PLUGIN_FILE" ]]; then
    sedi "s/\"version\": \"[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\"/\"version\": \"${NEW_VERSION}\"/" "$PLUGIN_FILE"
    echo "  Updated $PLUGIN_FILE"
fi

# ── Stamp CHANGELOG.md ──────────────────────────────────────────────────────

if grep -q '## \[Unreleased\]' "$CHANGELOG_FILE"; then
    # Build the replacement header
    if [[ -n "$SDK_VERSION" ]]; then
        HEADER="## [${NEW_VERSION}] — SDK ${SDK_VERSION} — ${TODAY}"
    else
        # Preserve existing SDK version from the [Unreleased] line if present
        EXISTING_SDK=$(grep '## \[Unreleased\]' "$CHANGELOG_FILE" | sed -n 's/.*SDK \([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/p')
        if [[ -n "$EXISTING_SDK" ]]; then
            HEADER="## [${NEW_VERSION}] — SDK ${EXISTING_SDK} — ${TODAY}"
        else
            HEADER="## [${NEW_VERSION}] — ${TODAY}"
        fi
    fi

    sedi "s/## \[Unreleased\].*/$(echo "$HEADER" | sed 's/[&/\]/\\&/g')/" "$CHANGELOG_FILE"
    echo "  Stamped $CHANGELOG_FILE"
else
    echo "  Warning: No [Unreleased] section found in $CHANGELOG_FILE"
fi

# ── Git tag ──────────────────────────────────────────────────────────────────

echo ""
echo "Version $NEW_VERSION is ready."
echo ""
echo "To complete the release:"
echo "  git add SKILL.md AGENTS.md CHANGELOG.md .claude-plugin/plugin.json"
echo "  git commit -m \"release: v${NEW_VERSION}\""
echo "  git tag v${NEW_VERSION}"
echo ""
echo "To push:"
echo "  git push origin HEAD && git push origin v${NEW_VERSION}"
