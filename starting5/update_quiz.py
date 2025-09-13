#!/usr/bin/env python3
import os
import random
import shutil
import sys

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
# Change these if your folder layout differs
PROJECT_ROOT   = os.path.abspath(os.path.dirname(__file__))  # /home/devgreeny/starting5_v3
PRELOADED_DIR  = os.path.join(PROJECT_ROOT, "app", "static", "preloaded_quizzes")
CURRENT_DIR    = os.path.join(PROJECT_ROOT, "app", "static", "current_quiz")
ARCHIVE_DIR    = os.path.join(PROJECT_ROOT, "app", "static", "archive_quizzes")
BONUS_DIR      = os.path.join(PROJECT_ROOT, "app", "static", "bonus_quiz")
# ────────────────────────────────────────────────────────────────────────────────

def archive_yesterdays_quiz():
    """Move any JSON in ``CURRENT_DIR`` to ``ARCHIVE_DIR``."""
    os.makedirs(CURRENT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    existing = [f for f in os.listdir(CURRENT_DIR) if f.lower().endswith(".json")]
    for old_file in existing:
        old_path = os.path.join(CURRENT_DIR, old_file)
        archive_path = os.path.join(ARCHIVE_DIR, old_file)
        try:
            shutil.move(old_path, archive_path)
            print(f"📦 Archived old quiz: {old_file}")
        except Exception as e:
            print(f"⚠️ Could not archive '{old_file}': {e}", file=sys.stderr)


def update_current_quiz():
    """Select a random quiz from ``PRELOADED_DIR`` and move it into ``CURRENT_DIR``."""
    os.makedirs(CURRENT_DIR, exist_ok=True)
    os.makedirs(PRELOADED_DIR, exist_ok=True)

    all_quizzes = [f for f in os.listdir(PRELOADED_DIR) if f.lower().endswith(".json")]
    if not all_quizzes:
        print("❌ No quizzes found in preloaded_quizzes. Nothing to do.", file=sys.stderr)
        sys.exit(1)

    chosen = random.choice(all_quizzes)
    src_path = os.path.join(PRELOADED_DIR, chosen)
    dest_path = os.path.join(CURRENT_DIR, chosen)

    try:
        shutil.move(src_path, dest_path)
        print(f"✅ Moved '{chosen}' → current_quiz")
        return chosen
    except Exception as e:
        print(f"❌ Failed to move '{chosen}': {e}", file=sys.stderr)
        sys.exit(1)


def prepare_bonus_quiz(exclude=None):
    """Ensure ``BONUS_DIR`` contains at least one quiz."""
    os.makedirs(BONUS_DIR, exist_ok=True)
    existing = [f for f in os.listdir(BONUS_DIR) if f.lower().endswith(".json")]
    if existing:
        return

    pool = [f for f in os.listdir(PRELOADED_DIR) if f.lower().endswith(".json")]
    if exclude and exclude in pool:
        pool.remove(exclude)
    if not pool:
        print("⚠️ No quizzes available for bonus quiz.", file=sys.stderr)
        return

    chosen = random.choice(pool)
    src = os.path.join(PRELOADED_DIR, chosen)
    dst = os.path.join(BONUS_DIR, chosen)
    try:
        shutil.copy(src, dst)
        print(f"✅ Prepared bonus quiz: {chosen}")
    except Exception as e:
        print(f"⚠️ Failed to prepare bonus quiz '{chosen}': {e}", file=sys.stderr)


def main():
    archive_yesterdays_quiz()
    chosen = update_current_quiz()
    prepare_bonus_quiz(exclude=chosen)

if __name__ == "__main__":
    main()
