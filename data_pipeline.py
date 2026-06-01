"""
ScoutPro — Data Pipeline
Collecte et agrège les données joueurs depuis StatsBomb Open Data.
Usage : python data_pipeline.py
Produit : data/players.json et data/players.csv
"""

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import json
from pathlib import Path
from statsbombpy import sb

# ── Compétitions disponibles en open data ──────────────────────────────────
COMPETITIONS = [
    (55, 282, "UEFA Euro 2024"),
    (43, 106, "FIFA World Cup 2022"),
    (223, 282, "Copa America 2024"),
    (11, 90,  "La Liga 2020/21"),
    (7,  235, "Ligue 1 2022/23"),
    (9,  281, "Bundesliga 2023/24"),
]

MAX_MATCHES_PER_COMP = 10   # augmenter pour plus de data (plus lent)
MIN_ACTIONS = 30             # filtre joueurs trop peu actifs


# ── Collecte des événements ────────────────────────────────────────────────
def collect_all_events(competitions=COMPETITIONS, max_per_comp=MAX_MATCHES_PER_COMP):
    frames = []
    for comp_id, season_id, name in competitions:
        print(f"  → {name}…")
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
            ids = matches['match_id'].tolist()[:max_per_comp]
            for mid in ids:
                try:
                    ev = sb.events(match_id=mid)
                    ev['competition'] = name
                    frames.append(ev)
                except Exception:
                    pass
        except Exception as e:
            print(f"    ⚠ Erreur {name}: {e}")
    if not frames:
        raise RuntimeError("Aucun événement collecté.")
    return pd.concat(frames, ignore_index=True)


# ── Normalisation des positions ────────────────────────────────────────────
POS_MAP = {
    'Goalkeeper': 'GK',
    'Center Back': 'CB', 'Left Center Back': 'CB', 'Right Center Back': 'CB',
    'Left Back': 'LB', 'Right Back': 'RB',
    'Left Wing Back': 'LWB', 'Right Wing Back': 'RWB',
    'Left Center Midfield': 'CM', 'Right Center Midfield': 'CM', 'Center Midfield': 'CM',
    'Left Defensive Midfield': 'CDM', 'Right Defensive Midfield': 'CDM', 'Center Defensive Midfield': 'CDM',
    'Left Attacking Midfield': 'CAM', 'Right Attacking Midfield': 'CAM', 'Center Attacking Midfield': 'CAM',
    'Left Midfield': 'LM', 'Right Midfield': 'RM',
    'Left Wing': 'LW', 'Right Wing': 'RW',
    'Left Center Forward': 'ST', 'Right Center Forward': 'ST', 'Center Forward': 'ST', 'Secondary Striker': 'ST',
}

# Mapping équipes NATIONALES StatsBomb → code pays
# Ne contient QUE les équipes nationales, pas les clubs
NATIONAL_TEAM_NAT = {
    'France': 'FR', 'Spain': 'ES', 'Germany': 'DE', 'Portugal': 'PT',
    'Brazil': 'BR', 'Argentina': 'AR', 'England': 'EN', 'Italy': 'IT',
    'Netherlands': 'NL', 'Belgium': 'BE', 'Croatia': 'HR', 'Morocco': 'MA',
    'Senegal': 'SN', 'Nigeria': 'NG', 'Serbia': 'RS', 'Denmark': 'DK',
    'Switzerland': 'CH', 'Austria': 'AT', 'Turkey': 'TR', 'Ukraine': 'UA',
    'Poland': 'PL', 'Georgia': 'GE', 'Scotland': 'SC', 'Hungary': 'HU',
    'Albania': 'AL', 'Romania': 'RO', 'Slovenia': 'SI', 'Uruguay': 'UY',
    'Colombia': 'CO', 'Ecuador': 'EC', 'Chile': 'CL', 'Mexico': 'MX',
    'United States': 'US', 'Canada': 'CA', 'Japan': 'JP', 'South Korea': 'KR',
    'Australia': 'AU', 'Cameroon': 'CM', 'Ghana': 'GH', 'Tunisia': 'TN',
    'Saudi Arabia': 'SA', 'Iran': 'IR', 'Costa Rica': 'CR', 'Wales': 'WL',
    'Czech Republic': 'CZ', 'Slovakia': 'SK',
}

# Noms grand public — corrige les noms complets StatsBomb vers noms connus
PLAYER_NAME_CLEAN = {
    # France
    'Kylian Mbappé Lottin':                    'Kylian Mbappé',
    'Aurélien Djani Tchouaméni':               'Aurélien Tchouaméni',
    'Dayotchanculle Upamecano':                'Dayot Upamecano',
    'Theo Bernard François Hernández':         'Theo Hernandez',
    'Mike Maignan':                            'Mike Maignan',
    'William Saliba':                          'William Saliba',
    'Jules Koundé':                            'Jules Koundé',
    'Ibrahima Konaté':                         'Ibrahima Konaté',
    'Adrien Rabiot':                           'Adrien Rabiot',
    'Antoine Griezmann':                       'Antoine Griezmann',
    'Ousmane Dembélé':                         'Ousmane Dembélé',
    'Marcus Thuram':                           'Marcus Thuram',
    'Olivier Giroud':                          'Olivier Giroud',
    'Kingsley Coman':                          'Kingsley Coman',
    'Bradley Barcola':                         'Bradley Barcola',
    'Eduardo Camavinga':                       'Eduardo Camavinga',
    'Youssouf Fofana':                         'Youssouf Fofana',
    'Randal Kolo Muani':                       'Randal Kolo Muani',
    "N'Golo Kanté":                            "N'Golo Kanté",
    # Espagne
    'Jordi Alba Ramos':                        'Jordi Alba',
    'Sergio Ramos García':                     'Sergio Ramos',
    'Álvaro Borja Morata Martín':              'Álvaro Morata',
    'Dani Olmo Carvajal':                      'Dani Olmo',
    'Lamine Yamal Nasraoui Ebana':             'Lamine Yamal',
    'Mikel Merino Zazón':                      'Mikel Merino',
    'Fabián Ruiz Peña':                        'Fabián Ruiz',
    'Marc Cucurella Saseta':                   'Marc Cucurella',
    'Nacho Fernández Iglesias':                'Nacho',
    # Allemagne
    'Edmond Fayçal Tapsoba':                   'Edmond Tapsoba',
    'Piero Martín Hincapié Reyna':             'Piero Hincapié',
    'Ilkay Gündogan':                          'İlkay Gündoğan',
    'Thomas Müller':                           'Thomas Müller',
    # Portugal
    'Cristiano Ronaldo dos Santos Aveiro':     'Cristiano Ronaldo',
    'Bruno Miguel Borges Fernandes':           'Bruno Fernandes',
    'João Félix Sequeira':                     'João Félix',
    'Bernardo Mota Veiga de Carvalho e Silva': 'Bernardo Silva',
    'Rúben Santos Gato Alves Dias':            'Rúben Dias',
    'Vitor Machado Ferreira':                  'Vitinha',
    'Marcos Aoás Corrêa':                      'Marquinhos',
    # Argentine
    'Lionel Andrés Messi Cuccittini':          'Lionel Messi',
    'Ángel Fabián Di María Hernández':         'Ángel Di María',
    # Maroc
    'Achraf Hakimi Mouh':                      'Achraf Hakimi',
    # Espagne — noms complets → noms grand public
    'Sergio Busquets i Burgos':                'Sergio Busquets',
    'Pedro González López':                    'Pedri',
    'Anssumane Fati':                          'Ansu Fati',
    'Ferran Torres García':                    'Ferran Torres',
    'Alejandro Baldé Martínez':               'Alejandro Balde',
    'Rodrigo Hernández Cascante':              'Rodri',
    'Daniel Carvajal Ramos':                  'Dani Carvajal',
    'Jesús Navas González':                   'Jesús Navas',
    'José Luis Gayà Peña':                    'José Gayà',
    # Angleterre
    'Jude Victor William Bellingham':         'Jude Bellingham',
    'Harry Edward Kane':                      'Harry Kane',
    # Italie
    'Nicolo Barella':                         'Nicolò Barella',
    'Federico Bernardeschi':                  'Federico Bernardeschi',
    # Pays-Bas
    'Memphis Depay':                          'Memphis Depay',
    'Virgil van Dijk':                        'Virgil van Dijk',
    'Cody Gakpo':                             'Cody Gakpo',
}


def scale(series, lo=None, hi=None, tlo=40, thi=99):
    lo = lo if lo is not None else series.quantile(0.02)
    hi = hi if hi is not None else series.quantile(0.98)
    s = (series - lo) / (hi - lo + 1e-9) * (thi - tlo) + tlo
    return s.clip(tlo, thi)


# ── Agrégation stats par joueur ────────────────────────────────────────────
def aggregate_player_stats(events):
    ev = events.dropna(subset=['player'])
    passes   = ev[ev['type'] == 'Pass']
    shots    = ev[ev['type'] == 'Shot']
    dribbles = ev[ev['type'] == 'Dribble']
    pressure = ev[ev['type'] == 'Pressure']

    # Capturer les équipes nationales jouées par chaque joueur
    # On garde la team nationale si elle apparaît dans NATIONAL_TEAM_NAT
    def get_nat_team(teams):
        for t in teams:
            if t in NATIONAL_TEAM_NAT:
                return t
        return None

    # Séparer équipes nationales et clubs
    national_teams = set(NATIONAL_TEAM_NAT.keys())

    # Pour le groupby principal : garder le club (la team la plus fréquente hors équipe nationale)
    def get_club_team(teams_series):
        clubs = [t for t in teams_series if t not in national_teams]
        if clubs:
            return pd.Series(clubs).mode()[0]
        return teams_series.mode()[0]

    base = ev.groupby(['player', 'player_id']).agg(
        team=('team', get_club_team),
        competitions=('competition', lambda x: list(x.unique())),
        position=('position', lambda x: x.mode()[0] if len(x.mode()) > 0 else 'Unknown'),
        total_actions=('id', 'count'),
    ).reset_index()

    # Récupérer la nationalité depuis les équipes nationales
    all_teams = ev.groupby('player')['team'].apply(lambda x: list(x.unique())).reset_index()
    all_teams.columns = ['player', 'all_teams']
    all_teams['nat_team'] = all_teams['all_teams'].apply(get_nat_team)
    base = base.merge(all_teams[['player','nat_team']], on='player', how='left')

    p_stats = passes.groupby('player').agg(
        passes_total=('id', 'count'),
        pass_completion=('pass_outcome', lambda x: x.isna().sum() / len(x) if len(x) > 0 else 0),
        key_passes=('pass_shot_assist', lambda x: x.sum() if hasattr(x, 'sum') else 0),
        assists=('pass_goal_assist', lambda x: x.sum() if hasattr(x, 'sum') else 0),
        progressive_passes=('pass_length', lambda x: (x > 20).sum()),
    ).reset_index()

    s_stats = shots.groupby('player').agg(
        shots_total=('id', 'count'),
        goals=('shot_outcome', lambda x: (x == 'Goal').sum()),
        xg_total=('shot_statsbomb_xg', 'sum'),
        shots_on_target=('shot_outcome', lambda x: x.isin(['Goal', 'Saved']).sum()),
    ).reset_index()

    d_stats = dribbles.groupby('player').agg(
        dribbles_total=('id', 'count'),
        dribbles_won=('dribble_outcome', lambda x: (x == 'Complete').sum()),
    ).reset_index()

    pr_stats = pressure.groupby('player').agg(
        pressures=('id', 'count'),
    ).reset_index()

    merged = (base
        .merge(p_stats,  on='player', how='left')
        .merge(s_stats,  on='player', how='left')
        .merge(d_stats,  on='player', how='left')
        .merge(pr_stats, on='player', how='left')
        .fillna(0)
    )
    return merged


# ── Calcul des ratings FIFA-like ──────────────────────────────────────────
FORM_BY_POS = {
    'GK':  ['4-3-3','4-4-2','3-5-2'],
    'CB':  ['4-3-3','3-5-2','5-3-2'],
    'LB':  ['4-3-3','4-2-3-1','3-4-3'],
    'RB':  ['4-3-3','4-2-3-1','3-4-3'],
    'LWB': ['3-4-3','3-5-2','5-3-2'],
    'RWB': ['3-4-3','3-5-2','5-3-2'],
    'CDM': ['4-2-3-1','4-3-3','3-5-2'],
    'CM':  ['4-3-3','4-2-3-1','3-5-2'],
    'CAM': ['4-2-3-1','4-3-3','3-4-3'],
    'LM':  ['4-4-2','4-2-3-1'],
    'RM':  ['4-4-2','4-2-3-1'],
    'LW':  ['4-3-3','4-2-3-1','3-4-3'],
    'RW':  ['4-3-3','4-2-3-1','3-4-3'],
    'ST':  ['4-3-3','4-4-2','4-2-3-1'],
    'MID': ['4-3-3','4-2-3-1'],
}
SYS_BY_POS = {
    'GK':  ["Relance au pied","Distribution longue"],
    'CB':  ["Ligne haute","Sortie balle au sol","Couverture de zone"],
    'LB':  ["Piston offensif","Débordement","Centres"],
    'RB':  ["Piston offensif","Débordement","Centres"],
    'LWB': ["Piston gauche","3 derrière","Transitions"],
    'RWB': ["Piston droit","3 derrière","Transitions"],
    'CDM': ["Double pivot","Récupération","Bloc bas"],
    'CM':  ["Box-to-box","Pressing collectif","Transitions"],
    'CAM': ["Jeu de possession","Milieu créatif","Entre les lignes"],
    'LM':  ["Ailier rentrant","Contre-attaque"],
    'RM':  ["Ailier rentrant","Contre-attaque"],
    'LW':  ["Haute pression","Ailier haut","Contre-pressing"],
    'RW':  ["Haute pression","Ailier haut","Contre-pressing"],
    'ST':  ["Attaque directe","Pressing avant","Profondeur"],
    'MID': ["Milieu relayeur","Transitions"],
}

OFF_POS  = ['ST','LW','RW','CAM','LM','RM']
MID_POS  = ['CM','CDM']
DEF_POS  = ['CB','LB','RB','LWB','RWB']
BIG_CLUBS = ['Paris Saint-Germain','FC Barcelona','Real Madrid','Bayern München',
             'Manchester City','Arsenal','Liverpool','Juventus','Inter']


def build_profiles(df):
    df = df[df['total_actions'] >= MIN_ACTIONS].copy()
    df['pos'] = df['position'].map(POS_MAP).fillna('MID')
    # Nationalité depuis l'équipe nationale (pas le club)
    df['nationality'] = df['nat_team'].map(NATIONAL_TEAM_NAT).fillna('EU')

    # Nettoyage des noms vers noms grand public
    df['player'] = df['player'].map(PLAYER_NAME_CLEAN).fillna(df['player'])

    # ── Normalisation par match pour éviter le biais volume
    # (les joueurs de grandes équipes accumulent plus d'actions)
    n_matches = df['competitions'].apply(len).clip(1, None)

    pass_per_match    = df['passes_total'] / n_matches
    prog_per_match    = df['progressive_passes'] / n_matches
    drib_per_match    = df['dribbles_total'] / n_matches
    press_per_match   = df['pressures'] / n_matches
    actions_per_match = df['total_actions'] / n_matches
    xg_per_match      = df['xg_total'] / n_matches
    goals_per_match   = df['goals'] / n_matches

    # Scores basés sur ratios et efficacité, pas le volume brut
    df['pass_score'] = (
        scale(pass_per_match) * 0.3 +
        scale(df['pass_completion'], 0.5, 1.0) * 0.5 +
        scale(prog_per_match) * 0.2
    ).clip(40, 99).round().astype(int)

    df['shoot_score'] = (
        scale(df['goals'] / df['shots_total'].clip(1, None)) * 0.4 +
        scale(xg_per_match) * 0.4 +
        scale(df['shots_on_target'] / df['shots_total'].clip(1, None)) * 0.2
    ).clip(40, 99).round().astype(int)

    df['dribble_score'] = (
        scale(drib_per_match) * 0.4 +
        scale(df['dribbles_won'] / df['dribbles_total'].clip(1, None), 0, 1) * 0.6
    ).clip(40, 99).round().astype(int)

    df['defense_score'] = scale(press_per_match).clip(40, 99).round().astype(int)
    df['physic_score']  = scale(actions_per_match).clip(40, 99).round().astype(int)
    df['pace_score']    = (
        scale(drib_per_match) * 0.5 +
        scale(prog_per_match) * 0.5
    ).clip(40, 99).round().astype(int)

    # Boost défense pour positions défensives
    def_mask = df['pos'].isin(['GK','CB','LB','RB','LWB','RWB','CDM'])
    boosted = (df.loc[def_mask, 'defense_score'].astype(float) * 1.1).clip(40, 99).round().astype(int)
    df['defense_score'] = df['defense_score'].astype(object)
    df.loc[def_mask, 'defense_score'] = boosted
    df['defense_score'] = pd.to_numeric(df['defense_score']).clip(40, 99).round().astype(int)

    # Overall
    def overall(row):
        if row['pos'] == 'GK':
            return int(row['defense_score']*0.5 + row['physic_score']*0.3 + row['pass_score']*0.2)
        elif row['pos'] in OFF_POS:
            return int(row['shoot_score']*0.35 + row['dribble_score']*0.25 + row['pace_score']*0.2 + row['pass_score']*0.15 + row['physic_score']*0.05)
        elif row['pos'] in MID_POS:
            return int(row['pass_score']*0.3 + row['defense_score']*0.25 + row['physic_score']*0.2 + row['dribble_score']*0.15 + row['shoot_score']*0.1)
        else:
            return int(row['defense_score']*0.4 + row['physic_score']*0.25 + row['pass_score']*0.2 + row['pace_score']*0.15)

    df['overall'] = df.apply(overall, axis=1).clip(55, 97)

    # Valeur marchande — fourchettes réalistes inspirées de Transfermarkt
    # Plafond absolu : 200M€ (record historique Neymar PSG 2017)
    # Source des fourchettes : valeurs médianes Transfermarkt par niveau
    def market_val(row):
        ov = row['overall']
        pos = row['pos']

        # Gardiens valent structurellement moins
        gk_factor = 0.6 if pos == 'GK' else 1.0

        # Fourchette de base selon la note overall
        if ov >= 93:   lo, hi = 150, 200   # Mbappé, Haaland, Vinicius
        elif ov >= 90: lo, hi = 100, 150   # top mondial
        elif ov >= 87: lo, hi =  60, 100   # très haut niveau
        elif ov >= 84: lo, hi =  30,  60   # international confirmé
        elif ov >= 81: lo, hi =  15,  30   # bon niveau L1/PL
        elif ov >= 78: lo, hi =   8,  15   # milieu de tableau L1
        elif ov >= 75: lo, hi =   3,   8   # rotation / remplaçant
        elif ov >= 70: lo, hi =   1,   3   # ligue 2 / mercato libre
        else:          lo, hi = 0.1, 0.8   # joueurs peu actifs

        lo = round(lo * gk_factor, 1)
        hi = round(hi * gk_factor, 1)

        # Formatage lisible
        def fmt(v):
            if v >= 1:
                return f"{int(round(v))}M€"
            else:
                return f"{int(v*1000)}K€"

        return f"{fmt(lo)} – {fmt(hi)}"

    df['market_value'] = df.apply(market_val, axis=1)

    # Ouverture transfert
    np.random.seed(42)
    df['transfer_open'] = np.random.randint(10, 95, size=len(df)).astype(float)
    df.loc[df['team'].isin(BIG_CLUBS), 'transfer_open'] *= 0.5
    df['transfer_open'] = df['transfer_open'].clip(5, 95).round().astype(int)

    # Formations & systèmes
    df['formations']     = df['pos'].map(FORM_BY_POS).apply(lambda x: x if isinstance(x,list) else ['4-3-3'])
    df['best_formation'] = df['formations'].apply(lambda x: x[0])
    df['systems']        = df['pos'].map(SYS_BY_POS).apply(lambda x: x if isinstance(x,list) else ["Polyvalence"])

    # Points forts / faibles
    def strengths(row):
        s = []
        if row['pass_score']    >= 80: s.append("Passe de qualité")
        if row['dribble_score'] >= 80: s.append("Dribble efficace")
        if row['shoot_score']   >= 80: s.append("Finition")
        if row['defense_score'] >= 80: s.append("Pressing intense")
        if row['pace_score']    >= 80: s.append("Vitesse")
        if row['pass_completion'] >= 0.88: s.append("Précision passe")
        if row['progressive_passes'] >= 20: s.append("Passes progressives")
        if row['goals'] >= 3: s.append("Efficacité but")
        if row['key_passes'] >= 3: s.append("Passes clés")
        if row['dribbles_won']/(row['dribbles_total']+1) >= 0.65: s.append("Dribble réussi")
        return s[:5] if s else ["Polyvalence","Discipline tactique"]

    def weaknesses(row):
        w = []
        if row['pass_score']    < 65: w.append("Jeu de passe")
        if row['defense_score'] < 60: w.append("Travail défensif")
        if row['shoot_score']   < 60: w.append("Finition")
        if row['dribble_score'] < 60: w.append("Dribble")
        if row['pressures']     <  5: w.append("Pressing")
        return w[:3] if w else ["Régularité","Expérience top niveau"]

    df['strengths'] = df.apply(strengths, axis=1)
    df['weaknesses'] = df.apply(weaknesses, axis=1)

    return df[[
        'player','player_id','team','nationality','pos','overall','market_value','transfer_open',
        'pace_score','shoot_score','pass_score','dribble_score','defense_score','physic_score',
        'goals','xg_total','assists','key_passes','passes_total','pass_completion',
        'dribbles_total','dribbles_won','pressures','progressive_passes',
        'formations','best_formation','strengths','weaknesses','systems','competitions',
    ]].sort_values('overall', ascending=False).reset_index(drop=True)


# ── Point d'entrée ─────────────────────────────────────────────────────────
def run():
    Path("data").mkdir(exist_ok=True)
    print("🔍 Collecte des données StatsBomb Open Data…")
    events = collect_all_events()
    print(f"   {len(events):,} événements, {events['player'].nunique()} joueurs bruts")

    print("⚙️  Agrégation des stats…")
    raw = aggregate_player_stats(events)

    print("🧮 Calcul des profils & ratings…")
    players = build_profiles(raw)

    players.to_json("data/players.json", orient='records', indent=2, force_ascii=False)
    players.to_csv("data/players.csv", index=False)

    print(f"\n✅ {len(players)} joueurs exportés → data/players.json & data/players.csv")
    print(players[['player','team','pos','overall','goals','xg_total']].head(10).to_string())


if __name__ == "__main__":
    run()
