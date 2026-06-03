"""
enrich_from_fbref.py
====================
Enrichit players.json avec les vraies données FBref + Transfermarkt :
  - Nationalités réelles
  - Noms officiels grand public
  - Valeurs de marché Transfermarkt
  - Stats réelles (xG, passes prog., pressing...)
  - Notes recalculées sur vraies stats

Usage : python enrich_from_fbref.py
Durée : 10-20 min (respecte les délais anti-ban)
"""

import json
import time
import unicodedata
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np

# ── VÉRIFICATION DES DÉPENDANCES ─────────────────────────────────────────────

try:
    import soccerdata as sd
    print("✅ soccerdata disponible")
except ImportError:
    print("❌ soccerdata non installé — lance : pip3 install soccerdata")
    exit(1)

# ── CONFIG ────────────────────────────────────────────────────────────────────

OUTPUT_PATH = Path("data/players.json")
BACKUP_PATH = Path("data/players_backup.json")

# Ligues FBref — Big 5 + compétitions internationales
FBREF_LEAGUES = "Big 5 European Leagues Combined"
FBREF_SEASON  = "2023-2024"

# Mapping nationalité FBref → code pays ScoutPro
NATION_MAP = {
    "France": "FR", "Spain": "ES", "Germany": "DE", "Portugal": "PT",
    "Brazil": "BR", "Argentina": "AR", "England": "EN", "Italy": "IT",
    "Netherlands": "NL", "Belgium": "BE", "Croatia": "HR", "Morocco": "MA",
    "Senegal": "SN", "Nigeria": "NG", "Serbia": "RS", "Denmark": "DK",
    "Switzerland": "CH", "Austria": "AT", "Turkey": "TR", "Ukraine": "UA",
    "Poland": "PL", "Georgia": "GE", "Scotland": "SC", "Hungary": "HU",
    "Albania": "AL", "Romania": "RO", "Slovenia": "SI", "Uruguay": "UY",
    "Colombia": "CO", "Ecuador": "EC", "Chile": "CL", "Mexico": "MX",
    "United States": "US", "Canada": "CA", "Japan": "JP", "South Korea": "KR",
    "Australia": "AU", "Cameroon": "CM", "Ghana": "GH", "Tunisia": "TN",
    "Saudi Arabia": "SA", "Iran": "IR", "Costa Rica": "CR", "Wales": "WL",
    "Czech Republic": "CZ", "Slovakia": "SK", "Sweden": "SE", "Norway": "NO",
    "Russia": "RU", "Paraguay": "PY", "Peru": "PE", "Bolivia": "BO",
    "Venezuela": "VE", "Jamaica": "JM", "Mali": "ML", "Ivory Coast": "CI",
    "Côte d'Ivoire": "CI", "Guinea": "GN", "Algeria": "DZ", "Egypt": "EG",
    "South Africa": "ZA", "Zimbabwe": "ZW", "Zambia": "ZM",
    "Congo DR": "CD", "Burkina Faso": "BF", "Gabon": "GA",
    "Finland": "FI", "Greece": "GR", "Israel": "IL", "Ireland": "IE",
    "Northern Ireland": "GB-NIR", "Kosovo": "XK", "Montenegro": "ME",
    "Bosnia and Herzegovina": "BA", "North Macedonia": "MK",
    "Bulgaria": "BG", "Estonia": "EE", "Latvia": "LV", "Lithuania": "LT",
    "Luxembourg": "LU", "Malta": "MT", "Iceland": "IS", "Faroe Islands": "FO",
    "Armenia": "AM", "Azerbaijan": "AZ", "Georgia": "GE", "Kazakhstan": "KZ",
    "Uzbekistan": "UZ", "China": "CN", "India": "IN", "Ghana": "GH",
}

# Notes FIFA max réalistes par poste (évite les aberrations)
MAX_OVERALL_BY_POS = {
    "GK": 90, "CB": 88, "LB": 87, "RB": 87,
    "LWB": 85, "RWB": 85, "CDM": 90, "CM": 89,
    "CAM": 90, "LM": 86, "RM": 86,
    "LW": 92, "RW": 92, "ST": 93, "MID": 87,
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ", "_").replace("'", "").replace("-", "_").replace(".", "")


def normalize_name(s: str) -> str:
    """Normalise un nom pour la comparaison : minuscules, sans accents."""
    s = unicodedata.normalize("NFD", s.lower().strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def name_match_score(name_a: str, name_b: str) -> float:
    """
    Score de correspondance entre deux noms (0-1).
    Compare les mots du nom : si le nom de famille + prénom matchent → fort score.
    """
    a = normalize_name(name_a).split()
    b = normalize_name(name_b).split()
    if not a or not b:
        return 0.0
    # Nombre de mots en commun
    common = len(set(a) & set(b))
    # Bonus si le dernier mot (nom de famille) est identique
    last_match = 2.0 if a[-1] == b[-1] else 0.0
    return (common + last_match) / (max(len(a), len(b)) + 2)


def fmt_market_value(v_euros: float) -> str:
    """Formate une valeur en euros → string lisible."""
    if pd.isna(v_euros) or v_euros <= 0:
        return "N/A"
    m = v_euros / 1_000_000
    if m >= 1:
        lo = max(1, round(m * 0.8))
        hi = round(m * 1.2)
        return f"{lo}M€ – {hi}M€"
    k = v_euros / 1_000
    return f"{int(k * 0.8)}K€ – {int(k * 1.2)}K€"


def compute_overall_from_fbref(row: pd.Series, pos: str) -> int:
    """
    Recalcule une note overall réaliste à partir des vraies stats FBref.
    Normalisée sur 90 minutes, pondérée par poste.
    """
    def safe(col, default=0):
        v = row.get(col, default)
        return float(v) if pd.notna(v) else default

    # Stats per 90
    xg90    = safe("xg_per90", safe("npxg_per90"))
    xa90    = safe("xa_per90", safe("xg_assist_per90"))
    prog_p  = safe("progressive_passes_per90", safe("prog_p"))
    prog_c  = safe("progressive_carries_per90", safe("prog_c"))
    press90 = safe("pressures_per90", safe("press"))
    inter90 = safe("interceptions_per90", safe("int"))
    shots90 = safe("shots_per90", safe("sh_per90"))
    pass_pct= safe("pass_completion_pct", safe("cmp_pct", 75)) / 100

    OFF_POS = ["ST", "LW", "RW", "CAM", "LM", "RM"]
    MID_POS = ["CM", "CDM"]
    DEF_POS = ["CB", "LB", "RB", "LWB", "RWB", "GK"]

    # Normalisation simple 0-100 sur des plages réalistes
    def norm(v, lo, hi):
        return max(0, min(100, (v - lo) / (hi - lo + 1e-9) * 100))

    if pos in OFF_POS:
        score = (
            norm(xg90,    0, 0.8) * 0.35 +
            norm(xa90,    0, 0.4) * 0.15 +
            norm(prog_c,  0, 8)   * 0.20 +
            norm(shots90, 0, 4)   * 0.20 +
            norm(pass_pct,0.6,1)  * 0.10
        )
    elif pos in MID_POS:
        score = (
            norm(prog_p,  0, 12)  * 0.25 +
            norm(prog_c,  0, 6)   * 0.15 +
            norm(press90, 0, 20)  * 0.20 +
            norm(inter90, 0, 3)   * 0.20 +
            norm(pass_pct,0.6,1)  * 0.20
        )
    elif pos == "GK":
        score = norm(pass_pct, 0.5, 1) * 0.5 + norm(inter90, 0, 2) * 0.5
    else:  # DEF
        score = (
            norm(inter90, 0, 3)   * 0.35 +
            norm(press90, 0, 15)  * 0.25 +
            norm(prog_p,  0, 10)  * 0.20 +
            norm(pass_pct,0.6,1)  * 0.20
        )

    # Convertir en note 55-93
    overall = int(55 + score * 38)
    max_ov  = MAX_OVERALL_BY_POS.get(pos, 88)
    return min(overall, max_ov)


# ── 1. CHARGEMENT FBREF ───────────────────────────────────────────────────────

def load_fbref_data() -> pd.DataFrame:
    print("\n[1/4] Chargement des données FBref...")
    print("  → Big 5 European Leagues 2023/24 (peut prendre 2-5 min)")

    fbref = sd.FBref(leagues=FBREF_LEAGUES, seasons=FBREF_SEASON)

    # Types valides : standard, keeper, shooting, playing_time, misc
    print("  → Stats standard (buts, xG, nationalité)...")
    std = fbref.read_player_season_stats(stat_type="standard")
    time.sleep(4)

    print("  → Stats tirs (xG détaillé)...")
    try:
        sht = fbref.read_player_season_stats(stat_type="shooting")
        time.sleep(4)
    except Exception:
        sht = pd.DataFrame()

    print("  → Stats misc (pressing, duels)...")
    try:
        misc = fbref.read_player_season_stats(stat_type="misc")
        time.sleep(4)
    except Exception:
        misc = pd.DataFrame()

    # Base = stats standard
    df = std.reset_index()

    # Aplatir les colonnes MultiIndex si nécessaire
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join([str(c) for c in col if c]).strip('_') for col in df.columns]

    # Afficher les colonnes disponibles pour debug
    print(f"  Colonnes standard : {list(df.columns[:25])}")

    # Renommer colonnes clés
    rename_map = {}
    for col in df.columns:
        col_lower = str(col).lower()
        if "nation" in col_lower and "nationality_raw" not in df.columns:
            rename_map[col] = "nationality_raw"
        elif "player" in col_lower and col_lower != "player":
            rename_map[col] = "player"

    df = df.rename(columns=rename_map)

    # Fusionner shooting si disponible
    if not sht.empty:
        sht = sht.reset_index()
        if isinstance(sht.columns, pd.MultiIndex):
            sht.columns = ['_'.join([str(c) for c in col if c]).strip('_') for col in sht.columns]
        # Chercher colonne joueur
        player_col = next((c for c in sht.columns if 'player' in str(c).lower()), None)
        if player_col:
            sht = sht.rename(columns={player_col: 'player'})
            merge_cols = [c for c in sht.columns if c not in df.columns or c == 'player']
            df = df.merge(sht[merge_cols], on='player', how='left', suffixes=('', '_sht'))

    print(f"  ✅ FBref : {len(df)} entrées joueurs")
    return df


# ── 2. CHARGEMENT TRANSFERMARKT ───────────────────────────────────────────────

def load_transfermarkt_data() -> pd.DataFrame:
    print("\n[2/4] Chargement des valeurs Transfermarkt...")
    try:
        tm = sd.Transfermarkt(leagues=FBREF_LEAGUES, seasons=FBREF_SEASON)
        print("  → Valeurs de marché...")
        players_tm = tm.read_player_market_values()
        time.sleep(3)
        players_tm = players_tm.reset_index()
        print(f"  ✅ Transfermarkt : {len(players_tm)} joueurs")
        print(f"  Colonnes : {list(players_tm.columns[:15])}")
        return players_tm
    except Exception as e:
        print(f"  ⚠️  Transfermarkt non disponible : {e}")
        print("  → Continuer sans valeurs de marché")
        return pd.DataFrame()


# ── 3. CROISEMENT AVEC players.json ──────────────────────────────────────────

def enrich_players_json(fbref_df: pd.DataFrame, tm_df: pd.DataFrame) -> None:
    print("\n[3/4] Croisement avec players.json...")

    # Backup
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        players = json.load(f)

    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    print(f"  💾 Backup → {BACKUP_PATH}")

    # Préparer le index FBref par nom normalisé
    fbref_index = {}
    if not fbref_df.empty:
        name_col = None
        for col in ["player", "Player", "name"]:
            if col in fbref_df.columns:
                name_col = col
                break

        if name_col:
            for _, row in fbref_df.iterrows():
                raw = str(row.get(name_col, ""))
                fbref_index[normalize_name(raw)] = row

    # Préparer index Transfermarkt
    tm_index = {}
    if not tm_df.empty:
        name_col_tm = None
        for col in ["player", "Player", "name"]:
            if col in tm_df.columns:
                name_col_tm = col
                break

        val_col = None
        for col in tm_df.columns:
            if "market" in str(col).lower() or "value" in str(col).lower():
                val_col = col
                break

        if name_col_tm and val_col:
            for _, row in tm_df.iterrows():
                raw = str(row.get(name_col_tm, ""))
                tm_index[normalize_name(raw)] = row.get(val_col)

    # Enrichir chaque joueur
    enriched_count = 0
    nat_updated    = 0
    val_updated    = 0
    note_updated   = 0

    for p in players:
        player_name = p.get("player", "")
        norm_name   = normalize_name(player_name)
        pos         = p.get("pos", "MID")

        # Trouver le meilleur match FBref
        best_row   = None
        best_score = 0.4  # seuil minimum

        for fbref_name, row in fbref_index.items():
            score = name_match_score(norm_name, fbref_name)
            if score > best_score:
                best_score = score
                best_row   = row

        if best_row is not None:
            enriched_count += 1

            # Nationalité réelle
            nat_raw = str(best_row.get("nationality_raw", ""))
            # FBref format : "fr FRA" ou "France" ou "FRA"
            nat_clean = nat_raw.split()[-1] if nat_raw else ""
            # Chercher dans NATION_MAP
            nat_found = None
            for country, code in NATION_MAP.items():
                if nat_clean.upper()[:3] == code[:3] or country.lower() in nat_raw.lower():
                    nat_found = code
                    break
            if not nat_found and len(nat_clean) == 2:
                nat_found = nat_clean.upper()
            if nat_found and nat_found != p.get("nationality", "EU"):
                p["nationality"] = nat_found
                nat_updated += 1

            # Note recalculée
            new_overall = compute_overall_from_fbref(best_row, pos)
            if new_overall != p.get("overall", 0):
                p["overall"] = new_overall
                note_updated += 1

            # Marquer comme enrichi FBref
            p["fbref_matched"] = True
            p["fbref_match_score"] = round(best_score, 2)

        # Valeur Transfermarkt
        best_val   = None
        best_vscore = 0.5

        for tm_name, val in tm_index.items():
            score = name_match_score(norm_name, tm_name)
            if score > best_vscore and val is not None:
                best_vscore = score
                best_val    = val

        if best_val is not None:
            try:
                p["market_value"] = fmt_market_value(float(best_val))
                val_updated += 1
            except (ValueError, TypeError):
                pass

    # Sauvegarder
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ Enrichissement terminé")
    print(f"     Joueurs matchés FBref  : {enriched_count}/{len(players)}")
    print(f"     Nationalités mises à jour : {nat_updated}")
    print(f"     Valeurs Transfermarkt  : {val_updated}")
    print(f"     Notes recalculées      : {note_updated}")


# ── 4. VÉRIFICATION FINALE ────────────────────────────────────────────────────

def print_verification() -> None:
    print("\n[4/4] Vérification...")

    with open(OUTPUT_PATH, encoding="utf-8") as f:
        players = json.load(f)

    stars = ["Mbappé", "Messi", "Dembélé", "Griezmann", "Lenglet",
             "Ronaldo", "Busquets", "Tchouaméni", "Pedri", "Bellingham"]

    print("\n🔍 Stars :")
    for p in players:
        if any(s in str(p.get("player", "")) for s in stars):
            tm = "✅" if p.get("fbref_matched") else "—"
            print(f"  {tm} {p['player']:<30} | {p['pos']:<5} | {p['overall']:>3} | {p['nationality']:<3} | {p['market_value']}")

    print("\n🔝 Top 10 overall :")
    top = sorted(players, key=lambda x: x.get("overall", 0), reverse=True)[:10]
    for p in top:
        print(f"  {p['overall']:>3} | {p['player']:<30} | {p['pos']:<5} | {p.get('nationality','?')}")

    matched = sum(1 for p in players if p.get("fbref_matched"))
    print(f"\n📊 Total : {len(players)} joueurs, {matched} enrichis FBref")


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  ScoutPro — Enrichissement FBref + Transfermarkt")
    print("  Julie Landrevie · Football Data & Video Analyst")
    print("=" * 60)

    if not OUTPUT_PATH.exists():
        print(f"❌ {OUTPUT_PATH} introuvable — lance d'abord : python data_pipeline.py")
        exit(1)

    try:
        fbref_df = load_fbref_data()
    except Exception as e:
        print(f"❌ Erreur FBref : {e}")
        print("  Vérifie que soccerdata est bien installé : pip3 install soccerdata")
        exit(1)

    tm_df = load_transfermarkt_data()

    enrich_players_json(fbref_df, tm_df)
    print_verification()

    print("\n" + "=" * 60)
    print("  Lance maintenant : streamlit run app.py")
    print("=" * 60)
