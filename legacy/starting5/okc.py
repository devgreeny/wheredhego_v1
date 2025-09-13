import json
import random
import time
import re
from pathlib import Path
import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import (
    leaguegamelog,
    boxscoretraditionalv2,
    boxscoresummaryv2,
    commonplayerinfo
)

# Load and clean NCAA D1 schools
DATA_PATH = Path(__file__).resolve().parent / "app" / "static" / "json" / "cbb25.csv"

df_d1 = pd.read_csv(DATA_PATH)
df_d1 = df_d1.rename(columns={"School": "Official", "Common name": "Common", "Primary": "Conference"})

def clean_name(name):
    if not isinstance(name, str):
        return ""
    cleaned = (
        name.lower()
        .replace("university of ", "")
        .replace("univ. of ", "")
        .replace("state university", "state")
        .replace("university", "")
        .replace(" at ", " ")
        .replace("the ", "")
        .replace("st.", "state")
        .replace("st ", "state ")
        .replace("state.", "state")
        .replace("-", " ")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

df_d1["Cleaned_Official"] = df_d1["Official"].apply(clean_name)
df_d1["Cleaned_Common"] = df_d1["Common"].apply(clean_name)

_cleaned_map = {}
for _, row in df_d1.iterrows():
    _cleaned_map[row["Cleaned_Common"]] = (row["Common"], row["Conference"])
    _cleaned_map[row["Cleaned_Official"]] = (row["Common"], row["Conference"])

def match_college_to_conf(school_raw: str):
    if not school_raw or school_raw.lower().strip() in {"unknown", "none"}:
        return "Unknown", "Other", "Other", 0

    cleaned = clean_name(school_raw)
    if cleaned in {"southern california", "university of southern california"}:
        school, conf = _cleaned_map.get("usc", ("USC", "Other"))
        return school, "College", conf, 100

    if cleaned in _cleaned_map:
        school, conf = _cleaned_map[cleaned]
        return school, "College", conf, 100

    if any(w in cleaned for w in ["high", "prep", "academy", "charter", "school"]):
        return school_raw, "High School", "Other", 0
    if any(w in cleaned for w in ["paris", "vasco", "canada", "real madrid", "bahamas", "belgrade", "france", "europe", "australia", "london", "international", "club"]):
        return school_raw, "International", "Other", 0
    return school_raw, "Other", "Other", 0

def get_college_info(player_name: str):
    match = [p for p in players.get_players() if p["full_name"].lower() == player_name.lower()]
    if not match:
        return "Unknown", "Other", "Other", None, "Unknown", "Unknown", 0
    player_id = match[0]["id"]
    time.sleep(0.6)
    info_df = commonplayerinfo.CommonPlayerInfo(player_id=player_id).get_data_frames()[0]
    school_raw = info_df.iloc[0].get("SCHOOL", "Unknown")
    position = info_df.iloc[0].get("POSITION", "Unknown")
    country = info_df.iloc[0].get("COUNTRY", "Unknown")
    school, school_type, conf, score = match_college_to_conf(school_raw)
    return school, school_type, conf, player_id, position, country, score

def get_all_game_ids(season: str):
    time.sleep(0.6)
    gl = leaguegamelog.LeagueGameLog(season=season, season_type_all_star="Regular Season")
    return gl.get_data_frames()[0]["GAME_ID"].unique().tolist()

def _prompt_avatar(player_name, default):
    try:
        raw = input(f"Avatar for {player_name} [1-14] (enter for {default}): ").strip()
    except EOFError:
        return default
    if not raw:
        return default
    if raw.isdigit() and 1 <= int(raw) <= 14:
        return int(raw)
    print("Invalid input, using", default)
    return default

def generate_quiz_from_season(season, save_dir, manual_avatars=False, avatar_map=None, specific_game_id=None):
    # If specific_game_id is provided, only attempt that game
    if specific_game_id:
        game_ids = [specific_game_id]
    else:
        game_ids = get_all_game_ids(season)
        random.shuffle(game_ids)

    for game_id in game_ids:
        try:
            time.sleep(0.6)
            box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
            df = box.get_data_frames()[0]
            starters = df[df["START_POSITION"].notna() & (df["START_POSITION"] != "")]
            if len(starters["TEAM_ID"].unique()) < 2:
                continue

            summary = boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id)
            header = summary.get_data_frames()[0].iloc[0]
            home_id, away_id = header["HOME_TEAM_ID"], header["VISITOR_TEAM_ID"]
            home_abbr = df[df["TEAM_ID"] == home_id]["TEAM_ABBREVIATION"].iloc[0]
            away_abbr = df[df["TEAM_ID"] == away_id]["TEAM_ABBREVIATION"].iloc[0]

            matchup_str = f"{home_abbr} vs {away_abbr}"
            game_date = header.get("GAME_DATE", None)
            if isinstance(game_date, pd.Timestamp):
                game_date = game_date.strftime("%Y-%m-%d")
            else:
                game_date = str(game_date)

            team_lineups = []
            for team_id in [home_id, away_id]:
                team_starters = starters[starters["TEAM_ID"] == team_id].head(5)
                if len(team_starters) < 5:
                    continue

                team_abbr = team_starters["TEAM_ABBREVIATION"].iloc[0]
                opp_abbr = away_abbr if team_id == home_id else home_abbr
                t_pts = team_starters["PTS"].sum()
                t_ast = team_starters["AST"].sum()
                t_reb = team_starters["REB"].sum()
                t_def = team_starters["STL"].sum() + team_starters["BLK"].sum()

                player_rows = []
                lineup_valid = True
                for _, row in team_starters.iterrows():
                    name = row["PLAYER_NAME"]
                    school, typ, conf, pid, pos, country, m_score = get_college_info(name)
                    if typ != "College" or m_score < 100:
                        lineup_valid = False
                        break
                    player_rows.append({
                        "row": row,
                        "name": name,
                        "school": school,
                        "typ": typ,
                        "conf": conf,
                        "pid": pid,
                        "pos": pos,
                        "country": country
                    })

                if not lineup_valid or len(player_rows) < 5:
                    continue

                quiz = {
                    "season": season,
                    "game_id": game_id,
                    "team_abbr": team_abbr,
                    "opponent_abbr": opp_abbr,
                    "matchup": matchup_str,
                    "game_date": game_date,
                    "players": []
                }

                for pr in player_rows:
                    row = pr["row"]
                    name = pr["name"]
                    school = pr["school"]
                    typ = pr["typ"]
                    conf = pr["conf"]
                    pid = pr["pid"]
                    pos = pr["pos"]
                    country = pr["country"]

                    sprite = random.randint(1, 14)
                    if avatar_map:
                        val = avatar_map.get(str(pid)) or avatar_map.get(pid)
                        if isinstance(val, (int, str)) and str(val).isdigit():
                            num = int(val)
                            if 1 <= num <= 14:
                                sprite = num

                    if manual_avatars:
                        sprite = _prompt_avatar(name, sprite)

                    pts = row["PTS"]
                    ast = row["AST"]
                    reb = row["REB"]
                    stl = row["STL"]
                    blk = row["BLK"]
                    defense = stl + blk

                    quiz["players"].append({
                        "name": name,
                        "school": school,
                        "school_type": typ,
                        "spriteIndex": sprite,
                        "team_abbrev": team_abbr,
                        "avatar": f"{sprite:02d}",
                        "conference": conf,
                        "player_id": pid,
                        "position": pos,
                        "country": country,
                        "game_stats": {
                            "pts": pts,
                            "ast": ast,
                            "reb": reb,
                            "stl": stl,
                            "blk": blk,
                        },
                        "game_contribution_pct": {
                            "points_pct": round(pts / t_pts, 3) if t_pts else 0,
                            "assists_pct": round(ast / t_ast, 3) if t_ast else 0,
                            "rebounds_pct": round(reb / t_reb, 3) if t_reb else 0,
                            "defense_pct": round(defense / t_def, 3) if t_def else 0,
                        },
                    })

                team_lineups.append(quiz)

            if team_lineups:
                selected = team_lineups[0] if specific_game_id else random.choice(team_lineups)
                out_path = Path(save_dir) / f"{selected['season']}_{selected['game_id']}_{selected['team_abbr']}.json"
                with out_path.open("w", encoding="utf-8") as f:
                    json.dump(selected, f, indent=2, ensure_ascii=False)
                print(f"Saved: {out_path}")
                return True

        except Exception as e:
            print(f"Skipping {game_id} due to: {e}")
            continue

    return False

def generate_quizzes_all_seasons(count=30, manual_avatars=False, avatar_map=None):
    save_dir = Path("app/static/ preloaded_quizzes")
    save_dir.mkdir(parents=True, exist_ok=True)
    seasons = [f"{year}-{str(year+1)[-2:]}" for year in range(2012, 2024)]
    saved = 0
    while saved < count:
        season = random.choice(seasons)
        if generate_quiz_from_season(season, save_dir, manual_avatars, avatar_map):
            saved += 1

if __name__ == "__main__":
    specific_id = "0042400402"
    season = "2023-24"
    save_dir = Path("app/static/preloaded_quizzes")
    save_dir.mkdir(parents=True, exist_ok=True)

    ok = generate_quiz_from_season(
        season,
        save_dir,
        manual_avatars=False,
        avatar_map=None,
        specific_game_id=specific_id
    )
    if not ok:
        print(f"Failed to generate quiz for game {specific_id}")
