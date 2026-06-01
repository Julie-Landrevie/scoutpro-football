"""
scout_report_pipeline.py
========================
Enrichissement ScoutPro pour le projet Scout Report — Coupe du Monde 2026
Julie Landrevie — Football Data & Video Analyst

Enrichit players.json avec stats défensives, pressing et progression.
Sources : StatsBomb Open Data (CdM 2022 + Euro 2024)

Usage:
  python scout_report_pipeline.py --player "Tchouaméni"
  python scout_report_pipeline.py --all_france
  python scout_report_pipeline.py  # démo sur Tchouaméni
"""

import argparse
import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsbombpy import sb

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────
# CONFIG — compétitions disponibles StatsBomb open data
# ─────────────────────────────────────────────────────────

COMPETITIONS = [
    {"competition_id": 43, "season_id": 106, "label": "FIFA World Cup 2022"},
    {"competition_id": 55, "season_id": 282, "label": "UEFA Euro 2024"},
]

# Noms StatsBomb exacts des Bleus présents dans les données open data
# Clé = mot-clé de recherche, valeur = nom exact StatsBomb
FRANCE_STATSBOMB_NAMES = {
    "Tchouaméni":     "Aurélien Djani Tchouaméni",
    "Rabiot":         "Adrien Rabiot",
    "Kanté":          "N'Golo Kanté",
    "Mbappé":         "Kylian Mbappé Lottin",
    "Dembélé":        "Ousmane Dembélé",
    "Thuram":         "Marcus Thuram",
    "Barcola":        "Bradley Barcola",
    "Konaté":         "Ibrahima Konaté",
    "Koundé":         "Jules Koundé",
    "Saliba":         "William Saliba",
    "Upamecano":      "Dayotchanculle Upamecano",
    "Maignan":        "Mike Maignan",
}

# Positions pour les percentiles
POSITIONS = {
    "Aurélien Djani Tchouaméni": "Defensive Midfield",
    "Adrien Rabiot":             "Central Midfield",
    "N'Golo Kanté":              "Defensive Midfield",
    "Kylian Mbappé Lottin":      "Center Forward",
    "Ousmane Dembélé":           "Right Wing",
    "Marcus Thuram":             "Center Forward",
    "Bradley Barcola":           "Left Wing",
    "Ibrahima Konaté":           "Center Back",
    "Jules Koundé":              "Right Back",
    "William Saliba":            "Center Back",
    "Dayotchanculle Upamecano":  "Center Back",
    "Mike Maignan":              "Goalkeeper",
}

OUTPUT_DIR = Path("data/enriched")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────
# 1. CHARGEMENT DES DONNÉES
# ─────────────────────────────────────────────────────────

def get_france_match_ids() -> list:
    all_ids = []
    for comp in COMPETITIONS:
        matches = sb.matches(
            competition_id=comp["competition_id"],
            season_id=comp["season_id"]
        )
        france = matches[
            matches["home_team"].str.contains("France", na=False) |
            matches["away_team"].str.contains("France", na=False)
        ]
        ids = france["match_id"].tolist()
        all_ids.extend(ids)
        print(f"  {comp['label']} — {len(ids)} matchs France")
    return all_ids


def load_all_events(match_ids: list) -> pd.DataFrame:
    frames = []
    for mid in match_ids:
        try:
            ev = sb.events(match_id=mid)
            ev["match_id"] = mid
            frames.append(ev)
        except Exception as e:
            print(f"  [WARN] Match {mid} : {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ─────────────────────────────────────────────────────────
# 2. CALCUL DES STATS
# ─────────────────────────────────────────────────────────

def extract_player_stats(events: pd.DataFrame, sb_name: str) -> dict:
    pev = events[events["player"] == sb_name].copy()
    if pev.empty:
        print(f"  [WARN] Aucun event pour '{sb_name}'")
        return {}

    n_matches = int(pev["match_id"].nunique())
    minutes   = float(n_matches * 90)  # estimation conservatrice
    per90     = 1.0 / max(n_matches, 1)  # normalisation par match (= par 90 min)

    # — Tirs & xG
    shots = pev[pev["type"] == "Shot"]
    goals = 0
    xg    = 0.0
    if not shots.empty:
        if "shot_outcome" in shots.columns:
            goals = int(shots["shot_outcome"].apply(
                lambda x: 1 if isinstance(x, dict) and x.get("name") == "Goal" else 0
            ).sum())
        if "shot_statsbomb_xg" in shots.columns:
            xg = float(shots["shot_statsbomb_xg"].fillna(0).sum())

    # — Passes
    passes = pev[pev["type"] == "Pass"]
    passes_comp = passes
    if "pass_outcome" in passes.columns:
        passes_comp = passes[passes["pass_outcome"].isna()]

    key_passes = pd.DataFrame()
    if "pass_shot_assist" in passes.columns:
        key_passes = passes[passes["pass_shot_assist"].notna()]

    xA = 0.0
    if "pass_goal_assist" in passes.columns:
        xA = float(passes["pass_goal_assist"].fillna(0).sum())

    passes_ft = passes[
        passes["location"].apply(
            lambda x: x[0] >= 80 if isinstance(x, list) and len(x) >= 2 else False
        )
    ] if "location" in passes.columns else pd.DataFrame()

    prog_passes = _progressive_passes(passes)

    # — Carries
    carries = pev[pev["type"] == "Carry"]
    prog_carries  = _progressive_carries(carries)
    carry_dist    = _carry_distance(carries)

    # — Pressing
    pressures = pev[pev["type"] == "Pressure"]

    # — Duels
    duels = pev[pev["type"] == "Duel"]
    duels_won = 0
    if not duels.empty and "duel_outcome" in duels.columns:
        duels_won = int(duels["duel_outcome"].apply(
            lambda x: 1 if isinstance(x, dict) and
                      x.get("name", "") in ["Won", "Success In Play", "Success Out"] else 0
        ).sum())

    # — Interceptions
    intercepts = pev[pev["type"] == "Interception"]
    intercepts_won = 0
    if not intercepts.empty and "interception_outcome" in intercepts.columns:
        intercepts_won = int(intercepts["interception_outcome"].apply(
            lambda x: 1 if isinstance(x, dict) and
                      x.get("name", "") in ["Won", "Success In Play", "Success Out"] else 0
        ).sum())

    # — Tacles
    tackles = pd.DataFrame()
    if "duel_type" in pev.columns:
        tackles = pev[
            (pev["type"] == "Duel") &
            pev["duel_type"].apply(
                lambda x: isinstance(x, dict) and x.get("name") == "Tackle"
            )
        ]

    # — Récupérations
    recoveries = pev[pev["type"] == "Ball Recovery"]

    return {
        "player_name":                  sb_name,
        "matches_analyzed":             n_matches,
        "minutes_estimated":            int(minutes),

        # Offensif
        "goals":                        goals,
        "xg_total":                     round(xg, 2),
        "xg_per90":                     round(xg * per90, 2),
        "shots_total":                  len(shots),
        "shots_per90":                  round(len(shots) * per90, 1),
        "key_passes":                   len(key_passes),
        "key_passes_per90":             round(len(key_passes) * per90, 1),
        "xA":                           round(xA, 2),
        "xA_per90":                     round(xA * per90, 2),

        # Passes & Progression
        "passes_total":                 len(passes),
        "passes_completed":             len(passes_comp),
        "pass_completion_pct":          round(100 * len(passes_comp) / max(len(passes), 1), 1),
        "progressive_passes":           prog_passes,
        "progressive_passes_per90":     round(prog_passes * per90, 1),
        "passes_final_third":           len(passes_ft),
        "passes_final_third_per90":     round(len(passes_ft) * per90, 1),

        # Carries
        "progressive_carries":          prog_carries,
        "progressive_carries_per90":    round(prog_carries * per90, 1),
        "carry_distance_total":         round(carry_dist, 1),
        "carry_distance_per90":         round(carry_dist * per90, 1),

        # Défensif
        "pressures":                    len(pressures),
        "pressures_per90":              round(len(pressures) * per90, 1),
        "duels_total":                  len(duels),
        "duels_won":                    duels_won,
        "duel_win_pct":                 round(100 * duels_won / max(len(duels), 1), 1),
        "interceptions":                len(intercepts),
        "interceptions_per90":          round(len(intercepts) * per90, 1),
        "interceptions_won":            intercepts_won,
        "tackles":                      len(tackles),
        "tackles_per90":                round(len(tackles) * per90, 1),
        "ball_recoveries":              len(recoveries),
        "ball_recoveries_per90":        round(len(recoveries) * per90, 1),
    }


# ─────────────────────────────────────────────────────────
# 3. HELPERS GÉOMÉTRIQUES
# ─────────────────────────────────────────────────────────

GOAL = (120, 40)

def _dist_to_goal(loc):
    if not isinstance(loc, list) or len(loc) < 2:
        return None
    return float(np.sqrt((GOAL[0] - loc[0])**2 + (GOAL[1] - loc[1])**2))


def _progressive_passes(passes: pd.DataFrame) -> int:
    if passes.empty:
        return 0
    if "location" not in passes.columns or "pass_end_location" not in passes.columns:
        return 0
    count = 0
    for _, r in passes.iterrows():
        d0 = _dist_to_goal(r.get("location"))
        d1 = _dist_to_goal(r.get("pass_end_location"))
        if d0 and d1 and (d0 - d1) >= 10:
            count += 1
    return count


def _progressive_carries(carries: pd.DataFrame) -> int:
    if carries.empty:
        return 0
    if "location" not in carries.columns or "carry_end_location" not in carries.columns:
        return 0
    count = 0
    for _, r in carries.iterrows():
        d0 = _dist_to_goal(r.get("location"))
        d1 = _dist_to_goal(r.get("carry_end_location"))
        if d0 and d1 and (d0 - d1) >= 5:
            count += 1
    return count


def _carry_distance(carries: pd.DataFrame) -> float:
    if carries.empty:
        return 0.0
    if "location" not in carries.columns or "carry_end_location" not in carries.columns:
        return 0.0
    total = 0.0
    for _, r in carries.iterrows():
        s, e = r.get("location"), r.get("carry_end_location")
        if isinstance(s, list) and isinstance(e, list) and len(s) >= 2 and len(e) >= 2:
            total += float(np.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2))
    return total


# ─────────────────────────────────────────────────────────
# 4. PERCENTILES
# ─────────────────────────────────────────────────────────

KEY_STATS = [
    "xg_per90", "xA_per90", "key_passes_per90",
    "progressive_passes_per90", "progressive_carries_per90",
    "pressures_per90", "duel_win_pct",
    "interceptions_per90", "ball_recoveries_per90",
    "passes_final_third_per90", "carry_distance_per90",
    "pass_completion_pct",
]


def compute_percentiles(all_stats: list, player_stats: dict) -> dict:
    percentiles = {}
    for stat in KEY_STATS:
        values = [s.get(stat, 0) for s in all_stats if s.get(stat) is not None]
        val    = player_stats.get(stat, 0)
        if values:
            pct = float(np.sum(np.array(values) <= val) / len(values) * 100)
            percentiles[f"pct_{stat}"] = round(pct, 1)
    return percentiles


# ─────────────────────────────────────────────────────────
# 5. MERGE DANS players.json
# ─────────────────────────────────────────────────────────

def merge_into_players_json(stats: dict, path: str = "data/players.json") -> bool:
    json_path = Path(path)
    if not json_path.exists():
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        players = json.load(f)

    sb_name  = stats["player_name"]
    lastname = sb_name.split()[-1].lower()
    matched  = False

    for player in players:
        stored = player.get("player", player.get("name", player.get("player_name", "")))
        if not stored or not stored.strip():
            continue
        parts = stored.lower().split()
        if not parts:
            continue
        if parts[-1] == lastname or lastname in stored.lower():
            player["enriched_stats"] = stats
            player["has_scout_report"] = True
            matched = True
            print(f"  ✅ Merge → '{stored}'")
            break

    if not matched:
        players.append({"name": sb_name, "enriched_stats": stats, "has_scout_report": True})
        print(f"  ➕ Nouveau joueur ajouté : '{sb_name}'")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    return matched


# ─────────────────────────────────────────────────────────
# 6. EXPORT JSON ENRICHI
# ─────────────────────────────────────────────────────────

def export(stats: dict, percentiles: dict) -> None:
    full = {**stats, "percentiles": percentiles}
    slug = (stats["player_name"]
            .lower()
            .replace(" ", "_")
            .replace("'", "")
            .replace("-", "_")
            .replace("é", "e")
            .replace("è", "e")
            .replace("ï", "i")
            .replace("â", "a"))
    path = OUTPUT_DIR / f"{slug}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=2)
    print(f"  💾 → {path}")


# ─────────────────────────────────────────────────────────
# 7. AFFICHAGE RÉSUMÉ
# ─────────────────────────────────────────────────────────

def print_summary(stats: dict) -> None:
    name    = stats["player_name"]
    matches = stats["matches_analyzed"]
    mins    = stats["minutes_estimated"]
    print(f"\n{'─'*56}")
    print(f"  {name}  |  {matches} matchs  |  ~{mins} min")
    print(f"{'─'*56}")

    groups = {
        "Offensif":    ["goals","xg_total","xg_per90","xA_per90","key_passes_per90","shots_per90"],
        "Progression": ["progressive_passes_per90","progressive_carries_per90",
                        "carry_distance_per90","passes_final_third_per90","pass_completion_pct"],
        "Défensif":    ["pressures_per90","duel_win_pct","interceptions_per90",
                        "tackles_per90","ball_recoveries_per90"],
    }
    for grp, keys in groups.items():
        print(f"\n  {grp.upper()}")
        for k in keys:
            v = stats.get(k, "—")
            label = k.replace("_per90","/90").replace("_pct"," %").replace("_"," ")
            print(f"    {label:<35} {v}")

    if stats.get("percentiles"):
        print(f"\n  PERCENTILES (vs tous les joueurs analysés)")
        for k, v in list(stats["percentiles"].items())[:8]:
            label = k.replace("pct_","").replace("_per90","/90").replace("_pct"," %").replace("_"," ")
            bar   = "█" * int(v/10) + "░" * (10 - int(v/10))
            print(f"    {label:<30} {bar}  {v:.0f}e perc.")
    print()


# ─────────────────────────────────────────────────────────
# 8. RÉSOLUTION DU NOM RECHERCHÉ → NOM STATSBOMB
# ─────────────────────────────────────────────────────────

def resolve_name(query: str) -> str | None:
    """Trouve le nom StatsBomb exact à partir d'un nom partiel."""
    q = query.lower()
    for keyword, sb_name in FRANCE_STATSBOMB_NAMES.items():
        if keyword.lower() in q or q in sb_name.lower():
            return sb_name
    # Recherche directe si le nom complet est fourni
    for sb_name in FRANCE_STATSBOMB_NAMES.values():
        if q in sb_name.lower():
            return sb_name
    return None


# ─────────────────────────────────────────────────────────
# 9. PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────

def run(targets_sb: list) -> None:
    print("\n" + "="*56)
    print("  Scout Report — Enrichissement StatsBomb")
    print("  Julie Landrevie · Football Data & Video Analyst")
    print("="*56)

    print("\n[1/4] Matchs France...")
    match_ids = get_france_match_ids()
    print(f"  Total : {len(match_ids)} matchs")

    print("\n[2/4] Chargement des events...")
    events = load_all_events(match_ids)
    print(f"  {len(events):,} events chargés")

    print(f"\n[3/4] Extraction stats ({len(targets_sb)} joueur(s))...")
    all_stats = []
    for sb_name in targets_sb:
        print(f"\n  → {sb_name}")
        stats = extract_player_stats(events, sb_name)
        if stats:
            all_stats.append(stats)

    if not all_stats:
        print("\n  [ERREUR] Aucun joueur trouvé dans les données.")
        print("  Joueurs disponibles :", list(FRANCE_STATSBOMB_NAMES.values()))
        return

    print(f"\n[4/4] Percentiles & exports...")
    for stats in all_stats:
        percentiles = compute_percentiles(all_stats, stats)
        stats["percentiles"] = percentiles
        export(stats, percentiles)
        merge_into_players_json(stats)

    print("\n" + "="*56)
    print(f"  ✅ {len(all_stats)} joueur(s) enrichi(s)")
    print(f"  📁 Fichiers JSON : data/enriched/")
    print("="*56)

    for stats in all_stats:
        print_summary(stats)


# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scout Report — Pipeline StatsBomb")
    parser.add_argument("--player", "-p", type=str, default=None,
                        help="Nom (partiel) du joueur ex: 'Tchouaméni'")
    parser.add_argument("--all_france", action="store_true",
                        help="Tous les Bleus disponibles dans StatsBomb")
    args = parser.parse_args()

    if args.all_france:
        targets = list(FRANCE_STATSBOMB_NAMES.values())
    elif args.player:
        sb_name = resolve_name(args.player)
        if not sb_name:
            print(f"Joueur '{args.player}' non trouvé.")
            print("Disponibles :", list(FRANCE_STATSBOMB_NAMES.keys()))
            exit(1)
        targets = [sb_name]
    else:
        print("[INFO] Démo — Aurélien Tchouaméni")
        targets = ["Aurélien Djani Tchouaméni"]

    run(targets)
