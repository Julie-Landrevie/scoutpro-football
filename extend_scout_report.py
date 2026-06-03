"""
extend_scout_report.py
======================
Étend l'enrichissement StatsBomb à tous les joueurs disponibles
dans les compétitions open data (pas seulement les Bleus).

Compétitions ciblées :
- La Liga 2020/21 (35 matchs complets)
- Premier League 2015/16 (380 matchs)
- Ligue 1 2022/23 (32 matchs)
- Bundesliga 2023/24 (tous matchs)
- Champions League (plusieurs saisons)
- Copa America 2024

Usage : python extend_scout_report.py
"""

import json, warnings, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
from statsbombpy import sb

warnings.filterwarnings("ignore")

OUTPUT_DIR = Path("data/enriched")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Compétitions à enrichir — toutes celles disponibles en open data
COMPETITIONS = [
    (43, 106, "FIFA World Cup 2022"),
    (55, 282, "UEFA Euro 2024"),
    (223, 282, "Copa America 2024"),
    (11,  90, "La Liga 2020/21"),
    (7,  235, "Ligue 1 2022/23"),
    (9,  281, "Bundesliga 2023/24"),
    (2,   27, "Premier League 2015/16"),
    (16,   1, "Champions League 2017/18"),
]

MAX_MATCHES = 50  # par compétition

GOAL = (120, 40)

def dist_to_goal(loc):
    if not isinstance(loc, list) or len(loc) < 2:
        return None
    return float(np.sqrt((GOAL[0]-loc[0])**2 + (GOAL[1]-loc[1])**2))

def prog_passes(passes):
    count = 0
    for _, r in passes.iterrows():
        d0 = dist_to_goal(r.get("location"))
        d1 = dist_to_goal(r.get("pass_end_location"))
        if d0 and d1 and (d0 - d1) >= 10:
            count += 1
    return count

def prog_carries(carries):
    count = 0
    for _, r in carries.iterrows():
        d0 = dist_to_goal(r.get("location"))
        d1 = dist_to_goal(r.get("carry_end_location"))
        if d0 and d1 and (d0 - d1) >= 5:
            count += 1
    return count

def carry_dist(carries):
    total = 0.0
    for _, r in carries.iterrows():
        s, e = r.get("location"), r.get("carry_end_location")
        if isinstance(s, list) and isinstance(e, list) and len(s) >= 2 and len(e) >= 2:
            total += float(np.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2))
    return total

def slugify(name):
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ","_").replace("'","").replace("-","_").replace(".","")

def extract_stats(events, player_name, n_matches):
    pev = events[events["player"] == player_name].copy()
    if pev.empty:
        return None

    per90 = 1.0 / max(n_matches, 1)

    passes   = pev[pev["type"] == "Pass"]
    shots    = pev[pev["type"] == "Shot"]
    carries  = pev[pev["type"] == "Carry"]
    pressures= pev[pev["type"] == "Pressure"]
    duels    = pev[pev["type"] == "Duel"]
    intercepts=pev[pev["type"] == "Interception"]
    recoveries=pev[pev["type"] == "Ball Recovery"]

    passes_comp = passes[passes["pass_outcome"].isna()] if "pass_outcome" in passes.columns else passes
    xg = float(shots["shot_statsbomb_xg"].fillna(0).sum()) if "shot_statsbomb_xg" in shots.columns else 0
    try:
        goals = int(shots["shot_outcome"].apply(lambda x: 1 if isinstance(x,dict) and x.get("name")=="Goal" else 0).sum()) if "shot_outcome" in shots.columns else 0
    except (ValueError, TypeError):
        goals = 0
    key_passes = len(passes[passes["pass_shot_assist"].notna()]) if "pass_shot_assist" in passes.columns else 0
    xA = float(passes["pass_goal_assist"].fillna(0).sum()) if "pass_goal_assist" in passes.columns else 0
    passes_ft = len(passes[passes["location"].apply(lambda x: x[0]>=80 if isinstance(x,list) and len(x)>=2 else False)]) if "location" in passes.columns else 0
    pp = prog_passes(passes)
    pc = prog_carries(carries)
    cd = carry_dist(carries)
    try:
        duels_won = int(duels["duel_outcome"].apply(lambda x: 1 if isinstance(x,dict) and x.get("name","") in ["Won","Success In Play","Success Out"] else 0).sum()) if "duel_outcome" in duels.columns else 0
    except (ValueError, TypeError):
        duels_won = 0

    return {
        "player_name": player_name,
        "matches_analyzed": n_matches,
        "goals": goals,
        "xg_total": round(xg, 2),
        "xg_per90": round(xg * per90, 2),
        "shots_total": len(shots),
        "shots_per90": round(len(shots) * per90, 1),
        "key_passes": key_passes,
        "key_passes_per90": round(key_passes * per90, 1),
        "xA": round(xA, 2),
        "xA_per90": round(xA * per90, 2),
        "passes_total": len(passes),
        "passes_completed": len(passes_comp),
        "pass_completion_pct": round(100*len(passes_comp)/max(len(passes),1), 1),
        "progressive_passes": pp,
        "progressive_passes_per90": round(pp * per90, 1),
        "passes_final_third": passes_ft,
        "passes_final_third_per90": round(passes_ft * per90, 1),
        "progressive_carries": pc,
        "progressive_carries_per90": round(pc * per90, 1),
        "carry_distance_total": round(cd, 1),
        "carry_distance_per90": round(cd * per90, 1),
        "pressures": len(pressures),
        "pressures_per90": round(len(pressures) * per90, 1),
        "duels_total": len(duels),
        "duels_won": duels_won,
        "duel_win_pct": round(100*duels_won/max(len(duels),1), 1),
        "interceptions": len(intercepts),
        "interceptions_per90": round(len(intercepts) * per90, 1),
        "ball_recoveries": len(recoveries),
        "ball_recoveries_per90": round(len(recoveries) * per90, 1),
    }

def run():
    print("="*60)
    print("  Enrichissement étendu — toutes compétitions StatsBomb")
    print("="*60)

    # Charger players.json pour savoir quels joueurs on a
    with open("data/players.json", encoding="utf-8") as f:
        players_json = json.load(f)
    known_players = {p.get("player","").lower() for p in players_json}

    total_enriched = 0

    for comp_id, season_id, label in COMPETITIONS:
        print(f"\n→ {label}")
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
            match_ids = matches["match_id"].tolist()[:MAX_MATCHES]
            print(f"  {len(match_ids)} matchs")
        except Exception as e:
            print(f"  ⚠️ {e}")
            continue

        # Charger les events
        frames = []
        for mid in match_ids:
            try:
                ev = sb.events(match_id=mid)
                ev["match_id"] = mid
                frames.append(ev)
            except Exception:
                pass

        if not frames:
            continue

        events = pd.concat(frames, ignore_index=True)

        # Joueurs uniques dans cette compétition
        players_in_comp = events["player"].dropna().unique()
        print(f"  {len(players_in_comp)} joueurs dans les events")

        comp_enriched = 0
        for player_name in players_in_comp:
            slug = slugify(player_name)
            out_path = OUTPUT_DIR / f"{slug}.json"

            # Calculer le nb de matchs pour ce joueur
            n_matches = events[events["player"]==player_name]["match_id"].nunique()

            # Ignorer si moins de 2 matchs
            if n_matches < 2:
                continue

            # Si fichier existe déjà, merger les données
            existing = {}
            if out_path.exists():
                try:
                    with open(out_path) as f:
                        existing = json.load(f)
                except Exception:
                    pass

            stats = extract_stats(events, player_name, n_matches)
            if not stats:
                continue

            # Fusionner avec existant si même joueur
            if existing.get("player_name") == player_name:
                # Additionner les totaux
                for key in ["matches_analyzed","goals","xg_total","shots_total",
                           "key_passes","passes_total","passes_completed",
                           "progressive_passes","passes_final_third",
                           "progressive_carries","pressures","duels_total",
                           "duels_won","interceptions","ball_recoveries"]:
                    stats[key] = stats.get(key,0) + existing.get(key,0)
                # Recalculer les per90
                total_m = stats["matches_analyzed"]
                per90 = 1.0 / max(total_m, 1)
                for k in list(stats.keys()):
                    if k.endswith("_per90") and not k.startswith("xg") and not k.startswith("xA"):
                        base = k.replace("_per90","")
                        if base in stats:
                            stats[k] = round(stats[base] * per90, 2)

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)

            comp_enriched += 1
            total_enriched += 1

        print(f"  ✅ {comp_enriched} joueurs enrichis")

    print(f"\n{'='*60}")
    print(f"  ✅ Total : {total_enriched} fichiers dans data/enriched/")
    print(f"  Lance : streamlit run app.py")
    print("="*60)

if __name__ == "__main__":
    run()
