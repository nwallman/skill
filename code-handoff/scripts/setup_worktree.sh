#!/usr/bin/env bash
# setup_worktree.sh
#
# Create a dedicated git worktree for a Cowork -> Claude Code handoff, write
# the plan file into it, and commit the plan on a new feature branch.
#
# Usage:
#   setup_worktree.sh <repo_path> <slug> <plan_source_file>
#
# Arguments:
#   repo_path         Absolute path to the source git repository.
#   slug              Short kebab-case identifier. Used for worktree dir name,
#                     branch name (feat/<slug>), and plan file name.
#   plan_source_file  Path to the already-filled-in plan markdown that should
#                     be written into the worktree at docs/plans/<slug>.md.
#
# Behavior:
#   - Auto-detects the repo's default branch (main or master).
#   - Creates a sibling directory <parent>/<repo>-worktrees/<slug>.
#   - Creates a new branch feat/<slug> based on the default branch.
#   - Copies the plan file to docs/plans/<slug>.md inside the worktree.
#   - Commits the plan with message "chore: add implementation plan for <slug>".
#   - Exits non-zero on any failure and prints a clear error.
#
# This script intentionally does NOT push, does NOT launch Claude Code, and
# does NOT modify the source branch. Its only job is to create a clean
# worktree the user can hand off.

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <repo_path> <slug> <plan_source_file>" >&2
  exit 2
fi

REPO_PATH="$1"
SLUG="$2"
PLAN_SRC="$3"

# --- Validate inputs ---------------------------------------------------------

if [[ ! -d "$REPO_PATH" ]]; then
  echo "ERROR: repo path does not exist: $REPO_PATH" >&2
  exit 1
fi

if [[ ! -d "$REPO_PATH/.git" ]]; then
  echo "ERROR: not a git repository: $REPO_PATH" >&2
  exit 1
fi

if [[ ! "$SLUG" =~ ^[a-z0-9][a-z0-9-]*[a-z0-9]$ ]]; then
  echo "ERROR: slug must be lowercase kebab-case (e.g. add-csv-export): $SLUG" >&2
  exit 1
fi

if [[ ! -f "$PLAN_SRC" ]]; then
  echo "ERROR: plan source file does not exist: $PLAN_SRC" >&2
  exit 1
fi

# --- Compute paths -----------------------------------------------------------

REPO_NAME="$(basename "$REPO_PATH")"
PARENT_DIR="$(dirname "$REPO_PATH")"
WORKTREES_DIR="$PARENT_DIR/${REPO_NAME}-worktrees"
WORKTREE_PATH="$WORKTREES_DIR/$SLUG"
BRANCH_NAME="feat/$SLUG"

if [[ -e "$WORKTREE_PATH" ]]; then
  echo "ERROR: worktree path already exists: $WORKTREE_PATH" >&2
  echo "       Choose a different slug, or remove/reuse the existing worktree." >&2
  exit 1
fi

# --- Detect default branch ---------------------------------------------------

cd "$REPO_PATH"

DEFAULT_BRANCH=""
if git show-ref --verify --quiet refs/heads/main; then
  DEFAULT_BRANCH="main"
elif git show-ref --verify --quiet refs/heads/master; then
  DEFAULT_BRANCH="master"
else
  # Fall back to remote HEAD if neither main nor master exists locally.
  REMOTE_HEAD="$(git symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [[ -n "$REMOTE_HEAD" ]]; then
    DEFAULT_BRANCH="${REMOTE_HEAD#refs/remotes/origin/}"
  fi
fi

if [[ -z "$DEFAULT_BRANCH" ]]; then
  echo "ERROR: could not detect default branch (no main, no master, no origin/HEAD)." >&2
  exit 1
fi

# --- Check branch name is free ----------------------------------------------

if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
  echo "ERROR: branch already exists: $BRANCH_NAME" >&2
  echo "       Choose a different slug, or delete the existing branch first." >&2
  exit 1
fi

# --- Create worktree ---------------------------------------------------------

mkdir -p "$WORKTREES_DIR"

echo "Creating worktree at $WORKTREE_PATH on branch $BRANCH_NAME (from $DEFAULT_BRANCH)..."
git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" "$DEFAULT_BRANCH"

# --- Write plan file ---------------------------------------------------------

PLAN_DEST_DIR="$WORKTREE_PATH/docs/plans"
PLAN_DEST="$PLAN_DEST_DIR/$SLUG.md"

mkdir -p "$PLAN_DEST_DIR"
cp "$PLAN_SRC" "$PLAN_DEST"

# --- Commit plan on the new branch ------------------------------------------

cd "$WORKTREE_PATH"
git add "docs/plans/$SLUG.md"
git commit -m "chore: add implementation plan for $SLUG" >/dev/null

# --- Report success ----------------------------------------------------------

echo ""
echo "Worktree ready."
echo "  Path:    $WORKTREE_PATH"
echo "  Branch:  $BRANCH_NAME"
echo "  Plan:    docs/plans/$SLUG.md"
