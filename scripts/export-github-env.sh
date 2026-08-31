#!/usr/bin/env bash
# Export local .env configuration to GitHub Actions secrets/variables.
#
# Usage:
#   scripts/export-github-env.sh        # dry-run: print commands
#   scripts/export-github-env.sh --apply # actually run gh commands
#
# Requires the GitHub CLI (gh) and write access to the repository.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found. Copy .env.example to .env and fill in your values first." >&2
    exit 1
fi

APPLY=false
if [[ "${1:-}" == "--apply" ]]; then
    APPLY=true
fi

# Secrets are sensitive values that should be encrypted by GitHub.
SECRETS=(
    DATABASE_URL
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
    DISCORD_WEBHOOK_URL
    HEALTHCHECKS_URL
)

# Variables are non-sensitive config values used by the scheduled scanner.
VARS=(
    PROPERTY24_ENABLED
    PROPERTY24_SEARCH_URL
    PRIVATE_PROPERTY_ENABLED
    PRIVATE_PROPERTY_SEARCH_URL
    PAM_GOLDING_ENABLED
    PAM_GOLDING_SEARCH_URL
    SEEFF_ENABLED
    SEEFF_SEARCH_URL
    SOTHEBYS_ENABLED
    SOTHEBYS_SEARCH_URL
    JUST_PROPERTY_ENABLED
    JUST_PROPERTY_SEARCH_URL
    HARCOURTS_ENABLED
    HARCOURTS_SEARCH_URL
    RAWSON_ENABLED
    RAWSON_SEARCH_URL
    MIN_PRICE
    MAX_PRICE
    BEDROOMS_MIN
    BEDROOMS_MAX
    BATHROOMS_MIN
    BATHROOMS_MAX
    GARAGE_MIN
    PET_FRIENDLY
    OWN_YARD
    FIBRE_INTERNET
    PROPERTY_TYPES
    PAGINATION_MAX_PAGES
    SLEEP_BETWEEN_REQUESTS
    PLAYWRIGHT_HEADLESS
    PLAYWRIGHT_TIMEOUT
    MAX_RETRIES
    WESTERN_CAPE_ONLY
)

is_secret() {
    local key="$1"
    for s in "${SECRETS[@]}"; do
        [[ "$s" == "$key" ]] && return 0
    done
    return 1
}

# Helper to read a value from .env, ignoring comments and empty lines.
get_value() {
    local key="$1"
    grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | sed "s/^${key}=//" | tail -n1 || true
}

run_cmd() {
    if $APPLY; then
        "$@"
    else
        printf '  %s\n' "$*"
    fi
}

echo "Reading configuration from $ENV_FILE"
if $APPLY; then
    echo "Pushing to GitHub..."
else
    echo "Dry-run. These commands would run:"
fi

for key in "${SECRETS[@]}"; do
    value="$(get_value "$key")"
    if [[ -z "$value" ]]; then
        continue
    fi
    if $APPLY; then
        printf '%s' "$value" | run_cmd gh secret set "$key" --body=-
    else
        echo "gh secret set $key --body=\"$value\""
    fi
done

for key in "${VARS[@]}"; do
    value="$(get_value "$key")"
    if [[ -z "$value" ]]; then
        continue
    fi
    if $APPLY; then
        run_cmd gh variable set "$key" --body="$value"
    else
        echo "gh variable set $key --body=\"$value\""
    fi
done

if ! $APPLY; then
    echo ""
    echo "To apply these settings, run:"
    echo "  scripts/export-github-env.sh --apply"
fi
