#!/usr/bin/env bash
# Local runner for the reels bot — for cron on your own server, or manual runs.
# Credentials come from automation/.env (never committed) or the environment.
#
#   automation/run.sh                     # normal run (respects state)
#   automation/run.sh --dry-run           # plan only
#   automation/run.sh --slot 1 --force    # force morning slot now
set -euo pipefail
cd "$(dirname "$0")"
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
exec python3 reels_bot.py "$@"
