"""
compute_percentiles.py
======================
Calcule les percentiles pour tous les fichiers data/enriched/*.json
en comparant chaque joueur aux autres joueurs du même groupe de poste.

Groupes de postes :
  - Gardiens (GK)
  - Défenseurs (CB, LB, RB, LWB, RWB)
  - Milieux défensifs (CDM)
  - Milieux (CM, CAM, LM, RM)
  - Attaquants (ST, LW, RW)

Seuil minimum : 3 matchs analysés pour être inclus dans les percentiles.

Usage : python compute_percentiles.py
"""

import json, os
import numpy as np
from pathlib import Path

ENRICHED_DIR = Path("data/enriched")
MIN_MATCHES  = 3

# Stats utilisées pour les percentiles
KEY_STATS = [
    "xg_per90", "xA_per90", "key_passes_per90",
    "progressive_passes_per90", "progressive_carries_per90",
    "pressures_per90", "duel_win_pct",
    "interceptions_per90", "ball_recoveries_per90",
    "passes_final_third_per90", "carry_distance_per90",
    "pass_completion_pct", "shots_per90",
]

# Mapping poste → groupe
POS_GROUP = {
    "GK":  "GK",
    "CB":  "DEF", "LB": "DEF", "RB": "DEF", "LWB": "DEF", "RWB": "DEF",
    "CDM": "CDM",
    "CM":  "MID", "CAM": "MID", "LM": "MID", "RM": "MID",
    "LW":  "ATT", "RW": "ATT", "ST": "ATT",
    "MID": "MID",
}

def load_all() -> list[dict]:
    """Charge tous les fichiers enriched avec au moins MIN_MATCHES matchs."""
    all_data = []
    for f in ENRICHED_DIR.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                d = json.load(fp)
            if d.get("matches_analyzed", 0) >= MIN_MATCHES:
                d["_file"] = str(f)
                all_data.append(d)
        except Exception:
            continue
    return all_data


def get_pos_group(player_name: str, players_json: list) -> str:
    """Récupère le groupe de poste depuis players.json."""
    name_lower = player_name.lower()
    for p in players_json:
        if p.get("player", "").lower() == name_lower:
            pos = p.get("pos", "MID")
            return POS_GROUP.get(pos, "MID")
    return "MID"


def compute_percentile(value: float, all_values: list[float]) -> float:
    """Percentile d'une valeur dans une liste."""
    if not all_values or value is None:
        return 50.0
    arr = np.array([v for v in all_values if v is not None])
    if len(arr) == 0:
        return 50.0
    return float(round(np.sum(arr <= value) / len(arr) * 100, 1))


def run():
    print("=" * 60)
    print("  Calcul des percentiles — tous les joueurs enrichis")
    print("=" * 60)

    # Charger players.json pour les postes
    with open("data/players.json", encoding="utf-8") as f:
        players_json = json.load(f)

    print(f"\n[1/3] Chargement des fichiers enriched...")
    all_data = load_all()
    print(f"  {len(all_data)} joueurs avec ≥{MIN_MATCHES} matchs")

    # Associer chaque joueur à son groupe de poste
    for d in all_data:
        d["_group"] = get_pos_group(d.get("player_name", ""), players_json)

    # Grouper par poste
    groups = {}
    for d in all_data:
        g = d["_group"]
        if g not in groups:
            groups[g] = []
        groups[g].append(d)

    print(f"\n[2/3] Groupes de postes :")
    for g, members in groups.items():
        print(f"  {g:<5} : {len(members)} joueurs")

    print(f"\n[3/3] Calcul des percentiles...")
    updated = 0

    for group_name, members in groups.items():
        # Construire les distributions par stat
        distributions = {}
        for stat in KEY_STATS:
            distributions[stat] = [
                m.get(stat) for m in members
                if m.get(stat) is not None and isinstance(m.get(stat), (int, float))
            ]

        # Calculer le percentile de chaque joueur vs son groupe
        for d in members:
            percentiles = {}
            for stat in KEY_STATS:
                val = d.get(stat)
                if val is not None and isinstance(val, (int, float)):
                    pct = compute_percentile(val, distributions[stat])
                    percentiles[f"pct_{stat}"] = pct

            d["percentiles"] = percentiles
            d["percentile_group"] = group_name
            d["percentile_sample_size"] = len(members)

            # Sauvegarder
            try:
                filepath = d["_file"]
                save_data = {k: v for k, v in d.items() if not k.startswith("_")}
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                updated += 1
            except Exception as e:
                print(f"  ⚠️  {e}")

    print(f"\n  ✅ {updated} fichiers mis à jour avec percentiles")

    # Vérification sur Tchouaméni
    print("\n🔍 Vérification Tchouaméni :")
    path = ENRICHED_DIR / "aurelien_djani_tchouameni.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        pct = d.get("percentiles", {})
        group = d.get("percentile_group", "?")
        n = d.get("percentile_sample_size", 0)
        print(f"  Groupe : {group} ({n} joueurs)")
        print(f"  Matchs : {d.get('matches_analyzed')}")
        for k, v in list(pct.items())[:6]:
            label = k.replace("pct_","").replace("_per90","/90").replace("_pct"," %").replace("_"," ")
            bar = "█" * int(v/10) + "░" * (10 - int(v/10))
            print(f"  {label:<25} {bar} {v:.0f}e")

    print(f"\n{'='*60}")
    print(f"  Lance : streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    run()
