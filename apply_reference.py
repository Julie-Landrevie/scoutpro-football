"""
apply_reference.py
==================
Applique players_reference.json sur players.json.
Les joueurs du fichier de référence ont priorité absolue
sur les valeurs calculées automatiquement.

Usage : python apply_reference.py
"""
import json, unicodedata
from pathlib import Path

def normalize(s):
    s = unicodedata.normalize("NFD", s.lower().strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def match_score(a, b):
    wa = set(normalize(a).split())
    wb = set(normalize(b).split())
    if not wa or not wb: return 0
    common = len(wa & wb)
    last_match = 2 if normalize(a).split()[-1] == normalize(b).split()[-1] else 0
    return (common + last_match) / (max(len(wa), len(wb)) + 2)

# Charger les fichiers
with open("data/players.json", encoding="utf-8") as f:
    players = json.load(f)

with open("data/players_reference.json", encoding="utf-8") as f:
    ref_data = json.load(f)

ref_players = ref_data["players"]

# Indexer la référence
ref_index = {normalize(p["name"]): p for p in ref_players}

updated = 0
for player in players:
    name = player.get("player", "")
    norm_name = normalize(name)

    # Chercher la meilleure correspondance
    best_ref = None
    best_score = 0.55  # seuil strict

    for ref_name, ref in ref_index.items():
        score = match_score(norm_name, ref_name)
        if score > best_score:
            best_score = score
            best_ref = ref

    if best_ref:
        player["overall"]      = best_ref["overall"]
        player["market_value"] = best_ref["market_value"]
        player["nationality"]  = best_ref["nationality"]
        player["ref_matched"]  = True
        player["ref_name"]     = best_ref["name"]
        updated += 1

# Sauvegarder
with open("data/players.json", "w", encoding="utf-8") as f:
    json.dump(players, f, ensure_ascii=False, indent=2)

print(f"✅ {updated} joueurs mis à jour depuis la référence")
print()

# Vérification
stars = ["Mbappé","Ronaldo","Messi","Griezmann","Lenglet",
         "Busquets","Tchouaméni","Bellingham","Haaland","Kanté"]
print("🔍 Vérification stars :")
for p in players:
    if any(s in str(p.get("player","")) for s in stars):
        ref = "✅" if p.get("ref_matched") else "—"
        print(f"  {ref} {p['player']:<30} | {p['pos']:<5} | {p['overall']:>3} | {p['nationality']:<3} | {p['market_value']}")

print()
print("🔝 Top 10 overall :")
top = sorted(players, key=lambda x: x.get("overall",0), reverse=True)[:10]
for p in top:
    ref = "✅" if p.get("ref_matched") else "—"
    print(f"  {ref} {p['overall']:>3} | {p['player']:<30} | {p['pos']:<5} | {p['nationality']}")
