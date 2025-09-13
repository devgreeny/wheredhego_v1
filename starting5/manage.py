import argparse
import json
import os

from app.main.routes import ensure_avatar_fields

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
PRELOADED_DIR = os.path.join(PROJECT_ROOT, "app", "static", "preloaded_quizzes")
CURRENT_DIR = os.path.join(PROJECT_ROOT, "app", "static", "current_quiz")


def find_quiz(game_id: str):
    for d in [CURRENT_DIR, PRELOADED_DIR]:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if not fname.lower().endswith(".json"):
                continue
            path = os.path.join(d, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if str(data.get("game_id")) == str(game_id):
                return path, data
    return None, None


def assign_avatars(game_id: str, mapping: dict):
    path, data = find_quiz(game_id)
    if not path:
        print(f"Quiz for game_id {game_id} not found.")
        return False

    changed = False
    for p in data.get("players", []):
        ensure_avatar_fields(p)
        pid = str(p.get("player_id"))
        if pid in mapping:
            p["avatar"] = str(mapping[pid]).zfill(2)
            changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated avatars in {path}")
    else:
        print("No matching player IDs found.")
    return changed


def main():
    parser = argparse.ArgumentParser(description="Assign avatar numbers for a quiz")
    parser.add_argument("--game_id", required=True, help="Game ID of the quiz")
    parser.add_argument("--mapping", required=True, help="JSON mapping of player_id to avatar number")
    args = parser.parse_args()

    try:
        mapping = json.loads(args.mapping)
    except json.JSONDecodeError as e:
        parser.error(f"Invalid mapping JSON: {e}")
        return

    assign_avatars(args.game_id, mapping)


if __name__ == "__main__":
    main()