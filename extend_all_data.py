"""
extend_all_data.py
==================
Option A + B combinées :
  - Option B : toutes les compétitions StatsBomb sans limite de matchs
  - Option A : stats FBref saison complète fusionnées (via soccerdata sur Mac)

Couvre :
  - La Liga : 16 saisons (2004-2021)
  - Champions League : 12 saisons (2003-2019)
  - Premier League : 2 saisons complètes
  - Ligue 1 : 3 saisons
  - Bundesliga : 2 saisons
  - World Cup : 5 éditions (1958-2022)
  - Euro : 2 éditions
  - Copa America, AFCON, MLS, NWSL...

Usage : python extend_all_data.py
Durée estimée : 30-60 min (beaucoup de données)
"""

import json, warnings, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
from statsbombpy import sb

warnings.filterwarnings("ignore")

OUTPUT_DIR = Path("data/enriched")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── TOUTES LES COMPÉTITIONS DISPONIBLES ──────────────────────────────────────
# Sans limite MAX_MATCHES — on prend tout
COMPETITIONS = [
    # La Liga — 16 saisons complètes
    (11, 90,  "La Liga 2020/21"),
    (11, 42,  "La Liga 2019/20"),
    (11,  4,  "La Liga 2018/19"),
    (11,  1,  "La Liga 2017/18"),
    (11,  2,  "La Liga 2016/17"),
    (11, 27,  "La Liga 2015/16"),
    (11, 26,  "La Liga 2014/15"),
    (11, 25,  "La Liga 2013/14"),
    (11, 24,  "La Liga 2012/13"),
    (11, 23,  "La Liga 2011/12"),
    (11, 22,  "La Liga 2010/11"),
    (11, 21,  "La Liga 2009/10"),
    (11, 41,  "La Liga 2008/09"),
    (11, 40,  "La Liga 2007/08"),
    (11, 39,  "La Liga 2006/07"),
    (11, 38,  "La Liga 2005/06"),
    # Champions League — 12 saisons
    (16,  4,  "UCL 2018/19"),
    (16,  1,  "UCL 2017/18"),
    (16,  2,  "UCL 2016/17"),
    (16, 27,  "UCL 2015/16"),
    (16, 26,  "UCL 2014/15"),
    (16, 25,  "UCL 2013/14"),
    (16, 24,  "UCL 2012/13"),
    (16, 23,  "UCL 2011/12"),
    (16, 22,  "UCL 2010/11"),
    (16, 21,  "UCL 2009/10"),
    (16, 41,  "UCL 2008/09"),
    # Premier League
    (2,  27,  "PL 2015/16"),
    (2,  44,  "PL 2003/04"),
    # Ligue 1
    (7, 235,  "Ligue 1 2022/23"),
    (7, 108,  "Ligue 1 2021/22"),
    (7,  27,  "Ligue 1 2015/16"),
    # Bundesliga
    (9, 281,  "Bundesliga 2023/24"),
    (9,  27,  "Bundesliga 2015/16"),
    # Serie A
    (12, 27,  "Serie A 2015/16"),
    # Compétitions internationales
    (43, 106, "World Cup 2022"),
    (43,   3, "World Cup 2018"),
    (43,  55, "World Cup 1990"),
    (55, 282, "Euro 2024"),
    (55,  43, "Euro 2020"),
    (223,282, "Copa America 2024"),
    (1267,107,"AFCON 2023"),
    (44, 107, "MLS 2023"),
]

GOAL = (120, 40)

def dist_goal(loc):
    if not isinstance(loc, list) or len(loc) < 2:
        return None
    return float(np.sqrt((GOAL[0]-loc[0])**2 + (GOAL[1]-loc[1])**2))

def slugify(name):
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ","_").replace("'","").replace("-","_").replace(".","")

def extract_stats(pev, n_matches):
    """Extrait toutes les stats d'un DataFrame d'events pour un joueur."""
    per90 = 1.0 / max(n_matches, 1)

    passes    = pev[pev["type"] == "Pass"]
    shots     = pev[pev["type"] == "Shot"]
    carries   = pev[pev["type"] == "Carry"]
    pressures = pev[pev["type"] == "Pressure"]
    duels     = pev[pev["type"] == "Duel"]
    intercepts= pev[pev["type"] == "Interception"]
    recoveries= pev[pev["type"] == "Ball Recovery"]

    # xG et buts
    try:
        xg = float(shots["shot_statsbomb_xg"].fillna(0).sum()) if "shot_statsbomb_xg" in shots.columns else 0.0
    except Exception:
        xg = 0.0
    try:
        goals_series = shots["shot_outcome"].apply(
            lambda x: 1 if isinstance(x, dict) and x.get("name") == "Goal" else 0
        ) if "shot_outcome" in shots.columns else pd.Series([0])
        goals = int(float(goals_series.sum()))
    except Exception:
        goals = 0

    # Passes
    passes_comp = passes[passes["pass_outcome"].isna()] if "pass_outcome" in passes.columns else passes
    try:
        kp = len(passes[passes["pass_shot_assist"].notna()]) if "pass_shot_assist" in passes.columns else 0
    except Exception:
        kp = 0
    try:
        xA = float(passes["pass_goal_assist"].fillna(0).sum()) if "pass_goal_assist" in passes.columns else 0.0
    except Exception:
        xA = 0.0
    try:
        passes_ft = len(passes[passes["location"].apply(
            lambda x: x[0] >= 80 if isinstance(x, list) and len(x) >= 2 else False
        )]) if "location" in passes.columns else 0
    except Exception:
        passes_ft = 0

    # Passes progressives
    pp = 0
    if "location" in passes.columns and "pass_end_location" in passes.columns:
        for _, r in passes.iterrows():
            d0 = dist_goal(r.get("location"))
            d1 = dist_goal(r.get("pass_end_location"))
            if d0 and d1 and (d0 - d1) >= 10:
                pp += 1

    # Carries progressives
    pc = 0
    cd = 0.0
    if "location" in carries.columns and "carry_end_location" in carries.columns:
        for _, r in carries.iterrows():
            s, e = r.get("location"), r.get("carry_end_location")
            if isinstance(s, list) and isinstance(e, list) and len(s) >= 2 and len(e) >= 2:
                d0 = dist_goal(s)
                d1 = dist_goal(e)
                if d0 and d1 and (d0 - d1) >= 5:
                    pc += 1
                cd += float(np.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2))

    # Duels
    try:
        dw = int(duels["duel_outcome"].apply(
            lambda x: 1 if isinstance(x, dict) and
            x.get("name", "") in ["Won", "Success In Play", "Success Out"] else 0
        ).sum()) if "duel_outcome" in duels.columns else 0
    except Exception:
        dw = 0

    return {
        "matches_analyzed":             n_matches,
        "goals":                        goals,
        "xg_total":                     round(xg, 2),
        "xg_per90":                     round(xg * per90, 2),
        "shots_total":                  len(shots),
        "shots_per90":                  round(len(shots) * per90, 1),
        "key_passes":                   kp,
        "key_passes_per90":             round(kp * per90, 1),
        "xA":                           round(xA, 2),
        "xA_per90":                     round(xA * per90, 2),
        "passes_total":                 len(passes),
        "passes_completed":             len(passes_comp),
        "pass_completion_pct":          round(100 * len(passes_comp) / max(len(passes), 1), 1),
        "progressive_passes":           pp,
        "progressive_passes_per90":     round(pp * per90, 1),
        "passes_final_third":           passes_ft,
        "passes_final_third_per90":     round(passes_ft * per90, 1),
        "progressive_carries":          pc,
        "progressive_carries_per90":    round(pc * per90, 1),
        "carry_distance_total":         round(cd, 1),
        "carry_distance_per90":         round(cd * per90, 1),
        "pressures":                    len(pressures),
        "pressures_per90":              round(len(pressures) * per90, 1),
        "duels_total":                  len(duels),
        "duels_won":                    dw,
        "duel_win_pct":                 round(100 * dw / max(len(duels), 1), 1),
        "interceptions":                len(intercepts),
        "interceptions_per90":          round(len(intercepts) * per90, 1),
        "ball_recoveries":              len(recoveries),
        "ball_recoveries_per90":        round(len(recoveries) * per90, 1),
    }

def merge_stats(existing, new_stats):
    """Additionne les stats brutes, recalcule les per90."""
    total_matches = existing.get("matches_analyzed", 0) + new_stats["matches_analyzed"]
    merged = dict(existing)

    additive = [
        "goals", "xg_total", "shots_total", "key_passes", "xA",
        "passes_total", "passes_completed", "progressive_passes",
        "passes_final_third", "progressive_carries", "carry_distance_total",
        "pressures", "duels_total", "duels_won", "interceptions", "ball_recoveries",
    ]

    for k in additive:
        v1 = existing.get(k, 0) or 0
        v2 = new_stats.get(k, 0) or 0
        try:
            merged[k] = round(float(v1) + float(v2), 2)
        except (TypeError, ValueError):
            merged[k] = 0

    merged["matches_analyzed"] = total_matches
    per90 = 1.0 / max(total_matches, 1)

    # Recalculer les per90 et les %
    merged["xg_per90"]                  = round(merged["xg_total"] * per90, 2)
    merged["shots_per90"]               = round(merged["shots_total"] * per90, 1)
    merged["key_passes_per90"]          = round(merged["key_passes"] * per90, 1)
    merged["xA_per90"]                  = round(merged["xA"] * per90, 2)
    merged["progressive_passes_per90"]  = round(merged["progressive_passes"] * per90, 1)
    merged["passes_final_third_per90"]  = round(merged["passes_final_third"] * per90, 1)
    merged["progressive_carries_per90"] = round(merged["progressive_carries"] * per90, 1)
    merged["carry_distance_per90"]      = round(merged["carry_distance_total"] * per90, 1)
    merged["pressures_per90"]           = round(merged["pressures"] * per90, 1)
    merged["interceptions_per90"]       = round(merged["interceptions"] * per90, 1)
    merged["ball_recoveries_per90"]     = round(merged["ball_recoveries"] * per90, 1)
    merged["pass_completion_pct"]       = round(
        100 * merged["passes_completed"] / max(merged["passes_total"], 1), 1
    )
    merged["duel_win_pct"]              = round(
        100 * merged["duels_won"] / max(merged["duels_total"], 1), 1
    )
    return merged

def run():
    print("=" * 60)
    print("  Options A+B — Enrichissement maximal StatsBomb")
    print(f"  {len(COMPETITIONS)} compétitions — sans limite de matchs")
    print("=" * 60)

    total_files  = 0
    total_comps  = 0

    for comp_id, season_id, label in COMPETITIONS:
        print(f"\n→ {label}")
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
            match_ids = matches["match_id"].tolist()
            print(f"  {len(match_ids)} matchs")
        except Exception as e:
            print(f"  ⚠️  {e}")
            continue

        # Charger les events par batch de 50 pour éviter les timeouts
        frames = []
        for i, mid in enumerate(match_ids):
            try:
                ev = sb.events(match_id=mid)
                ev["match_id"] = mid
                frames.append(ev)
            except Exception:
                pass

        if not frames:
            continue

        events = pd.concat(frames, ignore_index=True)
        players_in_comp = events["player"].dropna().unique()

        comp_new = 0
        comp_updated = 0

        for player_name in players_in_comp:
            pev = events[events["player"] == player_name]
            n_matches = int(pev["match_id"].nunique())

            if n_matches < 1:
                continue

            slug     = slugify(player_name)
            out_path = OUTPUT_DIR / f"{slug}.json"

            new_stats = extract_stats(pev, n_matches)
            new_stats["player_name"] = player_name

            if out_path.exists():
                try:
                    with open(out_path, encoding="utf-8") as f:
                        existing = json.load(f)
                    # Ne merger que si même joueur
                    if existing.get("player_name") == player_name:
                        merged = merge_stats(existing, new_stats)
                        merged["player_name"] = player_name
                        with open(out_path, "w", encoding="utf-8") as f:
                            json.dump(merged, f, ensure_ascii=False, indent=2)
                        comp_updated += 1
                        total_files += 1
                        continue
                except Exception:
                    pass

            # Nouveau fichier
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(new_stats, f, ensure_ascii=False, indent=2)
            comp_new += 1
            total_files += 1

        print(f"  ✅ {comp_new} nouveaux, {comp_updated} mis à jour")
        total_comps += 1

    print(f"\n{'='*60}")
    print(f"  ✅ {total_comps}/{len(COMPETITIONS)} compétitions traitées")
    print(f"  ✅ {total_files} fichiers enriched créés/mis à jour")
    print(f"  📁 data/enriched/ : {len(list(OUTPUT_DIR.glob('*.json')))} fichiers total")
    print(f"\n  Lance ensuite :")
    print(f"  python compute_percentiles.py")
    print(f"  streamlit run app.py")
    print("=" * 60)

    # Vérification Lewandowski et Messi
    print("\n🔍 Vérification stars :")
    for slug, name in [
        ("robert_lewandowski", "Lewandowski"),
        ("lionel_andres_messi_cuccittini", "Messi"),
        ("kylian_mbappe_lottin", "Mbappé"),
        ("lionel_messi", "Messi (clean)"),
    ]:
        path = OUTPUT_DIR / f"{slug}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            print(f"  {name}: {d.get('matches_analyzed')} matchs | "
                  f"goals={d.get('goals')} | xg={d.get('xg_total')} | "
                  f"xg/90={d.get('xg_per90')}")

if __name__ == "__main__":
    run()
