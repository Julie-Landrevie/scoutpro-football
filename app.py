"""
ScoutPro — recrutement et profilage (français / anglais, clair / sombre)
Données : StatsBomb Open Data. Charte commune : jl_ui.py et .streamlit/config.toml.
Lancement : streamlit run app.py
"""

import ast
import json
import unicodedata
from pathlib import Path

import streamlit as st

from jl_ui import C, footer, fr_num, header, kpi, note, plotly_style, setup, t

setup("ScoutPro — Julie Landrevie", "ScoutPro — Julie Landrevie", icon="⚽")

import numpy as np  # noqa: E402,F401
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402

# Vocabulaire des fiches (les données sont en français)
TAGS_EN = {
    'Discipline tactique': 'Tactical discipline', 'Dribble efficace': 'Effective dribbling',
    'Dribble réussi': 'Successful dribbling', 'Efficacité but': 'Clinical in front of goal', 'Finition': 'Finishing',
    'Passe de qualité': 'Quality passing', 'Passes clés': 'Key passes', 'Passes progressives': 'Progressive passes',
    'Polyvalence': 'Versatility', 'Pressing intense': 'Intense pressing', 'Précision passe': 'Passing accuracy',
    'Vitesse': 'Pace', 'Dribble': 'Dribbling', 'Expérience top niveau': 'Top-level experience',
    'Jeu de passe': 'Passing game', 'Pressing': 'Pressing', 'Régularité': 'Consistency',
    'Travail défensif': 'Defensive work', '3 derrière': 'Back three', 'Ailier haut': 'High winger',
    'Ailier rentrant': 'Inverted winger', 'Attaque directe': 'Direct attack', 'Bloc bas': 'Low block',
    'Box-to-box': 'Box-to-box', 'Centres': 'Crosses', 'Contre-attaque': 'Counter-attack',
    'Contre-pressing': 'Counter-pressing', 'Couverture de zone': 'Zonal cover', 'Distribution longue': 'Long distribution',
    'Double pivot': 'Double pivot', 'Débordement': 'Overlapping runs', 'Entre les lignes': 'Between the lines',
    'Haute pression': 'High press', 'Jeu de possession': 'Possession play', 'Ligne haute': 'High line',
    'Milieu créatif': 'Creative midfielder', 'Piston droit': 'Right wing-back', 'Piston gauche': 'Left wing-back',
    'Piston offensif': 'Attacking wing-back', 'Pressing avant': 'Front pressing', 'Pressing collectif': 'Collective pressing',
    'Profondeur': 'Runs in behind', 'Relance au pied': 'Playing out from the back', 'Récupération': 'Ball recovery',
    'Sortie balle au sol': 'Build-up on the ground', 'Transitions': 'Transitions',
}


def tag(s):
    return t(s, TAGS_EN.get(s, s))


ATTR = [('pace_score', 'Vitesse', 'Pace'), ('shoot_score', 'Tir', 'Shooting'), ('pass_score', 'Passe', 'Passing'),
        ('dribble_score', 'Dribble', 'Dribbling'), ('defense_score', 'Défense', 'Defending'),
        ('physic_score', 'Physique', 'Physical')]
STYLES = {
    "possession": (("Possession / jeu court", "Possession / short passing"),
                   {'pass_score': 0.35, 'physic_score': 0.2, 'defense_score': 0.2, 'dribble_score': 0.15, 'shoot_score': 0.1}),
    "counter": (("Contre-attaque", "Counter-attack"),
                {'pace_score': 0.35, 'shoot_score': 0.3, 'dribble_score': 0.2, 'pass_score': 0.1, 'physic_score': 0.05}),
    "press": (("Pressing haut", "High press"),
              {'physic_score': 0.3, 'defense_score': 0.3, 'pace_score': 0.2, 'pass_score': 0.1, 'shoot_score': 0.1}),
    "direct": (("Jeu direct / long", "Direct / long ball"),
               {'physic_score': 0.35, 'shoot_score': 0.3, 'defense_score': 0.2, 'pace_score': 0.1, 'pass_score': 0.05}),
    "transitions": (("Transitions rapides", "Fast transitions"),
                    {'pace_score': 0.35, 'dribble_score': 0.25, 'shoot_score': 0.2, 'pass_score': 0.15, 'physic_score': 0.05}),
    "lowblock": (("Bloc bas défensif", "Defensive low block"),
                 {'defense_score': 0.4, 'physic_score': 0.3, 'pass_score': 0.15, 'pace_score': 0.1, 'shoot_score': 0.05}),
}
NONE = "__none__"
ALL = "__all__"


# ── CHARGEMENT DES DONNÉES ───────────────────────────────────────────────────

@st.cache_data
def load_players():
    path = Path("data/players.json")
    if not path.exists():
        st.error(t("data/players.json introuvable. Lancez : python data_pipeline.py",
                   "data/players.json not found. Run: python data_pipeline.py"))
        st.stop()
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)

    def safe_parse(x):
        if isinstance(x, list):
            return x
        if not x or (isinstance(x, float) and pd.isna(x)):
            return []
        try:
            result = ast.literal_eval(str(x))
            return result if isinstance(result, list) else []
        except Exception:
            return []

    for col in ['formations', 'strengths', 'weaknesses', 'systems', 'competitions']:
        if col in df.columns:
            df[col] = df[col].apply(safe_parse)
    return df


# Mapping noms grand public → noms StatsBomb pour retrouver le bon fichier enrichi
CLEAN_TO_SB = {
    "Kylian Mbappé":        "kylian_mbappe_lottin",
    "Aurélien Tchouaméni":  "aurelien_djani_tchouameni",
    "Dayot Upamecano":      "dayotchanculle_upamecano",
    "Theo Hernandez":       "theo_bernard_francois_hernandez",
    "N'Golo Kanté":        "ngolo_kante",
    "Adrien Rabiot":        "adrien_rabiot",
    "Ousmane Dembélé":      "ousmane_dembele",
    "Marcus Thuram":        "marcus_thuram",
    "Bradley Barcola":      "bradley_barcola",
    "Ibrahima Konaté":      "ibrahima_konate",
    "Jules Koundé":         "jules_kounde",
    "William Saliba":       "william_saliba",
    "Mike Maignan":         "mike_maignan",
    "Vinícius Jr.":         "vinicius_jose_paixao_de_oliveira_junior",
    "Neymar":               "neymar_da_silva_santos_junior",
    "Marcelo":              "marcelo_vieira_da_silva_junior",
    "Rodrygo":              "rodrygo_goes",
    "Lionel Messi":         "lionel_andres_messi_cuccittini",
    "Cristiano Ronaldo":    "cristiano_ronaldo_dos_santos_aveiro",
    "Luka Modrić":          "luka_modric",
    "Sergio Ramos":         "sergio_ramos_garcia",
    "Jordi Alba":           "jordi_alba_ramos",
    "Sergio Busquets":      "sergio_busquets_i_burgos",
    "Pedri":                "pedro_gonzalez_lopez",
    "Gavi":                 "gavi",
    "Bernardo Silva":       "bernardo_mota_veiga_de_carvalho_e_silva",
    "Vitinha":              "vitor_machado_ferreira",
    "Marquinhos":           "marcos_aoas_correa",
}

def _slugify(name: str) -> str:
    """Convertit un nom en slug de fichier."""
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace(" ", "_").replace("'", "").replace("-", "_").replace(".", "")
    return s

def _try_load(path):
    try:
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return None

# Pas de cache sur load_enriched — doit relire le disque à chaque fois
def load_enriched(player_name: str) -> dict | None:
    """
    Charge les stats enrichies depuis data/enriched/.
    Stratégie 4 couches pour trouver le bon fichier.
    """
    enriched_dir = Path("data/enriched")
    if not enriched_dir.exists():
        return None

    # 1. Mapping direct nom affiché → slug StatsBomb
    slug = CLEAN_TO_SB.get(player_name)
    if slug:
        path = enriched_dir / f"{slug}.json"
        if path.exists():
            return _try_load(path)

    # 2. Slug direct du nom affiché
    slug2 = _slugify(player_name)
    path2 = enriched_dir / f"{slug2}.json"
    if path2.exists():
        return _try_load(path2)

    # 3. Nom de famille slugifié dans le stem du fichier
    parts = player_name.split()
    for part in reversed(parts):  # cherche d'abord le nom de famille
        slug_part = _slugify(part)
        if len(slug_part) > 3:  # éviter les particules courtes
            for f in enriched_dir.glob("*.json"):
                if slug_part in f.stem:
                    data = _try_load(f)
                    if data:
                        return data

    # 4. Chercher par player_name dans le contenu JSON
    for f in enriched_dir.glob("*.json"):
        data = _try_load(f)
        if data:
            sb_name = data.get("player_name", "")
            # Comparer le dernier mot du nom affiché avec le nom StatsBomb
            if parts and _slugify(parts[-1]) in _slugify(sb_name):
                return data

    return None

df_all = load_players()
df = df_all.sort_values('overall', ascending=False).drop_duplicates('player').reset_index(drop=True)
# L'âge n'est pas dans les données actuelles : on ne l'affiche que s'il est renseigné (pas de valeur inventée).
HAS_AGE = 'age' in df.columns and df['age'].notna().any()


def radar(series, height=300, rng=(40, 99)):
    """series : liste de (nom, valeurs, couleur). Le radar suit le thème clair / sombre."""
    fig = go.Figure()
    for name, (labels, vals), color in series:
        fig.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=labels + [labels[0]], fill='toself', name=name,
                                      line=dict(color=color, width=2.5), opacity=0.9))
    fig.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, range=list(rng))),
                      showlegend=len(series) > 1, legend=dict(orientation='h', y=-0.12))
    return plotly_style(fig, height=height)


def bar_rows(items, maxv=100, suffix=""):
    """Barres horizontales en HTML (suivent le thème grâce aux variables CSS de jl_ui)."""
    html = ""
    for label, val in items:
        w = max(0, min(100, val / maxv * 100))
        html += (f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
                 f'<div style="width:150px;font-size:0.85rem;color:var(--jl-ink2)">{label}</div>'
                 f'<div style="flex:1;background:var(--jl-grid);border-radius:3px;height:8px">'
                 f'<div style="width:{w:.0f}%;background:var(--jl-teal);height:8px;border-radius:3px"></div></div>'
                 f'<div style="width:44px;font-size:0.9rem;font-weight:700;color:var(--jl-ink);text-align:right">{val:.0f}{suffix}</div>'
                 f'</div>')
    st.markdown(html, unsafe_allow_html=True)


def kv_rows(d):
    st.markdown("".join(
        f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--jl-grid);'
        f'font-size:0.9rem"><span style="color:var(--jl-ink2)">{k}</span><span style="color:var(--jl-ink);font-weight:700">{v}</span></div>'
        for k, v in d.items()), unsafe_allow_html=True)


def tags(items, mark=""):
    st.markdown("".join(f'<span class="jl-tag">{mark}{tag(s)}</span>' for s in items) or "—", unsafe_allow_html=True)


def num(v, dec=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if isinstance(v, (int, np.integer)) or dec == 0:
        return fr_num(float(v), 0)
    return fr_num(float(v), dec)


# ── BARRE LATÉRALE ───────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ScoutPro")
    st.caption(t("Recrutement et profilage · StatsBomb Open Data", "Recruitment and profiling · StatsBomb Open Data"))

    search = st.text_input(t("Recherche", "Search"), placeholder=t("Nom…", "Name…"))
    pos_sel = st.selectbox(t("Poste", "Position"), [ALL] + sorted(str(x) for x in df['pos'].dropna().unique()),
                           format_func=lambda v: t("Tous", "All") if v == ALL else v)
    nat_sel = st.selectbox(t("Nationalité", "Nationality"), [ALL] + sorted(str(x) for x in df['nationality'].dropna().unique()),
                           format_func=lambda v: t("Toutes", "All") if v == ALL else v)
    NATIONAL_NAMES = {
        'France', 'Spain', 'Germany', 'Portugal', 'Brazil', 'Argentina', 'England',
        'Italy', 'Netherlands', 'Belgium', 'Croatia', 'Morocco', 'Senegal', 'Nigeria',
        'Serbia', 'Denmark', 'Switzerland', 'Austria', 'Turkey', 'Ukraine', 'Poland',
        'Georgia', 'Scotland', 'Hungary', 'Albania', 'Romania', 'Slovenia', 'Uruguay',
        'Colombia', 'Ecuador', 'Chile', 'Mexico', 'United States', 'Canada', 'Japan',
        'South Korea', 'Australia', 'Cameroon', 'Ghana', 'Tunisia', 'Saudi Arabia',
        'Iran', 'Costa Rica', 'Wales', 'Czech Republic', 'Slovakia', 'Bolivia',
        'Peru', 'Paraguay', 'Jamaica',
    }
    club_list = sorted(x for x in df['team'].dropna().unique() if x not in NATIONAL_NAMES)
    club_sel = st.selectbox(t("Club", "Club"), [ALL] + club_list, format_func=lambda v: t("Tous", "All") if v == ALL else v)
    rating_min = st.slider(t("Note minimale", "Minimum rating"), 55, 97, 65)
    age_range = st.slider(t("Tranche d’âge", "Age range"), 17, 40, (17, 35)) if HAS_AGE else None
    all_forms = ['4-3-3', '4-4-2', '4-2-3-1', '3-5-2', '3-4-3', '5-3-2']
    form_sel = st.multiselect(t("Dispositif tactique", "Formation"), all_forms)
    T_OPTS = {ALL: ("Toutes", "Any"), "high": ("Probable (> 70 %)", "Likely (>70%)"),
              "med": ("Incertaine (40 à 70 %)", "Uncertain (40-70%)"), "low": ("Peu probable (< 40 %)", "Unlikely (<40%)")}
    transfer_sel = st.selectbox(t("Ouverture au transfert", "Transfer openness"), list(T_OPTS),
                                format_func=lambda k: t(*T_OPTS[k]))
    min_goals = st.slider(t("Buts minimum", "Minimum goals"), 0, 20, 0)
    min_xg = st.slider(t("xG minimum", "Minimum xG"), 0.0, 10.0, 0.0, 0.5)

    st.markdown("---")
    st.markdown(f"#### {t('Matching tactique', 'Tactical matching')}")
    st.caption(t("Décris ton style de jeu pour trouver les profils les plus compatibles.",
                 "Describe your playing style to find the most compatible profiles."))
    style_jeu = st.selectbox(t("Style de jeu", "Playing style"), [NONE] + list(STYLES),
                             format_func=lambda k: t("Choisir…", "Choose…") if k == NONE else t(*STYLES[k][0]))
    formation_eq = st.selectbox(t("Formation de ton équipe", "Your team’s formation"), [NONE] + all_forms,
                                format_func=lambda k: t("Choisir…", "Choose…") if k == NONE else k)
    poste_besoin = st.selectbox(t("Poste recherché en priorité", "Priority position"),
                                [NONE, "GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"],
                                format_func=lambda k: t("Choisir…", "Choose…") if k == NONE else k)
    st.caption(t("Score de compatibilité pondéré selon les attributs clés du style (vitesse, passe, défense…), ramené entre 0 et 100 %.",
                 "Compatibility score weighted by the style’s key attributes (pace, passing, defending…), scaled from 0 to 100%."))
    match_btn = st.button(t("Trouver les meilleurs profils", "Find the best profiles"), width="stretch")


# ── FILTRAGE ─────────────────────────────────────────────────────────────────

mask = pd.Series([True] * len(df))
if search:
    mask &= df['player'].str.lower().str.contains(search.lower(), na=False)
if pos_sel != ALL:
    mask &= df['pos'] == pos_sel
if nat_sel != ALL:
    mask &= df['nationality'] == nat_sel
if club_sel != ALL:
    mask &= df['team'] == club_sel
mask &= df['overall'] >= rating_min
if HAS_AGE:
    mask &= df['age'].between(age_range[0], age_range[1])
mask &= df['goals'] >= min_goals
mask &= df['xg_total'] >= min_xg
if form_sel:
    mask &= df['formations'].apply(lambda x: any(f in x for f in form_sel))
if transfer_sel == "high":
    mask &= df['transfer_open'] >= 70
elif transfer_sel == "med":
    mask &= (df['transfer_open'] >= 40) & (df['transfer_open'] < 70)
elif transfer_sel == "low":
    mask &= df['transfer_open'] < 40
filtered = df[mask].reset_index(drop=True)


header("ScoutPro", t("Fiches de scouting par poste à partir des données ouvertes StatsBomb : attributs, profil tactique, "
                     "comparaison et rapport détaillé.",
                     "Scouting cards by position from StatsBomb open data: attributes, tactical profile, comparison and "
                     "detailed report."))


# ── MATCHING ──────────────────────────────────────────────────────────────────

if match_btn and style_jeu != NONE and poste_besoin != NONE:
    st.subheader(t("Matching tactique", "Tactical matching"))
    weights = STYLES[style_jeu][1]
    candidates = df[df['pos'] == poste_besoin].copy()
    if formation_eq != NONE:
        candidates = candidates[candidates['formations'].apply(lambda x: formation_eq in x)]
    candidates['match_score'] = sum(candidates[col] * w for col, w in weights.items() if col in candidates.columns)
    candidates['match_score'] = ((candidates['match_score'] - candidates['match_score'].min())
                                 / (candidates['match_score'].max() - candidates['match_score'].min() + 1e-9) * 100)
    top = candidates.nlargest(5, 'match_score')
    if top.empty:
        st.warning(t("Aucun profil pour cette combinaison. Essaie un autre poste ou une autre formation.",
                     "No profile for this combination. Try another position or formation."))
    else:
        cols = st.columns(min(5, len(top)))
        for i, (_, pl) in enumerate(top.iterrows()):
            kpi(cols[i], fr_num(pl['match_score'], 0, pct=True),
                f"<b>{pl['player']}</b><br>{pl['team']}<br>{pl['pos']} · {pl['overall']} · {pl['market_value']}",
                accent=(i == 0))
    st.markdown("---")
elif match_btn:
    st.info(t("Choisis un style de jeu et un poste pour lancer le matching.",
              "Choose a playing style and a position to run the matching."))


# ── MISE EN PAGE ─────────────────────────────────────────────────────────────

col_list, col_detail = st.columns([1, 2], gap="large")

with col_list:
    st.markdown(f"**{len(filtered)}** {t('profils', 'profiles')}")
    if filtered.empty:
        st.info(t("Aucun profil ne correspond.", "No matching profile."))
    else:
        selected_name = st.selectbox(
            t("Sélectionner", "Select"), filtered['player'].tolist(),
            format_func=lambda n: f"{n} ({filtered[filtered['player'] == n]['pos'].values[0]}) · "
                                  f"{filtered[filtered['player'] == n]['overall'].values[0]}")
        selected = filtered[filtered['player'] == selected_name].iloc[0]
        cols_tbl = ['player', 'pos', 'team'] + (['age'] if HAS_AGE else []) + ['overall', 'goals', 'xg_total', 'transfer_open']
        tbl = filtered[cols_tbl].copy()
        names = {'player': t('Nom', 'Name'), 'pos': t('Poste', 'Pos'), 'team': 'Club', 'age': t('Âge', 'Age'),
                 'overall': t('Note', 'Rating'), 'goals': t('Buts', 'Goals'), 'xg_total': 'xG',
                 'transfer_open': t('Transfert', 'Transfer')}
        tbl.columns = [names[c] for c in cols_tbl]
        st.dataframe(tbl, hide_index=True, width="stretch", height=420, column_config={
            names['overall']: st.column_config.ProgressColumn(names['overall'], min_value=55, max_value=97, format="%d"),
            names['transfer_open']: st.column_config.ProgressColumn(names['transfer_open'], min_value=0, max_value=100, format="%d%%"),
            names['player']: st.column_config.TextColumn(names['player'], width="medium"),
            'xG': st.column_config.NumberColumn('xG', width="small", format="%.2f"),
            names['goals']: st.column_config.NumberColumn(names['goals'], width="small"),
            names['pos']: st.column_config.TextColumn(names['pos'], width="small"),
        })
        note(t("Le <b>rapport détaillé</b> (stats réelles StatsBomb par 90 minutes et percentiles par poste) est disponible "
               "pour de nombreux profils : sélectionne un nom, puis ouvre l’onglet « Rapport ».",
               "The <b>detailed report</b> (real StatsBomb per-90 stats and percentiles by position) is available for many "
               "profiles: select a name, then open the “Report” tab."))


with col_detail:
    if filtered.empty:
        st.info(t("Utilise les filtres pour trouver des profils.", "Use the filters to find profiles."))
        footer("Données : StatsBomb (Open Data)", "Data: StatsBomb (Open Data)")
        st.stop()

    p = selected
    comps = p['competitions'] if isinstance(p.get('competitions'), list) else []

    # ── CARTE DU PROFIL ──────────────────────────────────────────────────
    sub = f"{p['team']} · {p['nationality']}" + (f" · {int(p['age'])} {t('ans', 'yrs')}" if HAS_AGE and pd.notna(p.get('age')) else "")
    attrs_html = "".join(
        f'<div style="text-align:center;min-width:58px"><div style="font-family:\'DM Serif Display\',Georgia,serif;'
        f'font-size:1.6rem;color:var(--jl-ink)">{fr_num(float(p[k]), 0)}</div><div style="font-size:0.75rem;color:var(--jl-ink2)">{t(fr, en)}</div></div>'
        for k, fr, en in ATTR)
    st.markdown(f"""
<div class="jl-kpi" style="display:flex;gap:1.4rem;align-items:center;flex-wrap:wrap;margin-bottom:0.8rem">
  <div style="text-align:center;min-width:90px">
    <div class="v accent" style="font-size:3.2rem">{p['overall']}</div>
    <div class="l">{t('Note', 'Rating')}</div>
  </div>
  <div style="flex:1;min-width:220px">
    <div style="font-family:'DM Serif Display',Georgia,serif;font-size:1.7rem;color:var(--jl-ink);line-height:1.1">{p['player']}</div>
    <div style="color:var(--jl-ink2);margin:0.2rem 0 0.4rem 0">{sub}</div>
    <span class="jl-tag">{p['pos']}</span><span class="jl-tag">{p['market_value']}</span>
  </div>
  <div style="display:flex;gap:0.8rem;flex-wrap:wrap">{attrs_html}</div>
</div>""", unsafe_allow_html=True)

    note(t("<b>Données modélisées</b> : les notes et scores sont calculés à partir des actions StatsBomb Open Data. Ils reflètent "
           "l’activité dans les compétitions couvertes, pas le niveau réel du joueur. L’onglet « Rapport » contient les "
           "statistiques avancées réelles quand elles existent.",
           "<b>Modelled data</b>: ratings and scores are computed from StatsBomb Open Data actions. They reflect activity in the "
           "covered competitions, not the player’s true level. The “Report” tab holds real advanced stats when available."),
         warn=True)
    st.caption(t("Compétitions couvertes : La Liga 2005-2021, Ligue des champions 2008-2019, Premier League 2015/16, Ligue 1 2022/23, "
                 "Bundesliga 2023/24, Coupes du monde 2018 et 2022, Euro 2024. Le club affiché est celui de la période couverte.",
                 "Covered competitions: La Liga 2005-2021, Champions League 2008-2019, Premier League 2015/16, Ligue 1 2022/23, "
                 "Bundesliga 2023/24, World Cups 2018 and 2022, Euro 2024. The club shown is the one during the covered period."))

    m = st.columns(4)
    kpi(m[0], str(int(p['goals'])), t("Buts", "Goals"))
    kpi(m[1], fr_num(p['xg_total'], 2), "xG")
    kpi(m[2], str(int(p['key_passes'])), t("Passes clés", "Key passes"))
    kpi(m[3], fr_num(p['transfer_open'], 0, pct=True), t("Ouverture au transfert", "Transfer openness"))
    st.write("")

    enriched = load_enriched(p['player'])
    has_report = enriched is not None
    tab_labels = [t("Attributs", "Attributes"), t("Tactique", "Tactics"), t("Marché", "Market"), t("Comparaison", "Comparison")]
    if has_report:
        tab_labels.append(t("Rapport", "Report"))
    tabs = st.tabs(tab_labels)

    # ── ATTRIBUTS ──────────────────────────────────────────────────────
    with tabs[0]:
        labels = [t(fr, en) for _, fr, en in ATTR]
        vals = [float(p[k]) for k, _, _ in ATTR]
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(radar([(p['player'], (labels, vals), C["teal"])], height=300), width="stretch", theme="streamlit")
        with c2:
            st.markdown(f"**{t('Attributs', 'Attributes')}**")
            bar_rows(list(zip(labels, vals)))
        s = st.columns(4)
        kpi(s[0], str(int(p['passes_total'])), t("Passes", "Passes"))
        kpi(s[1], fr_num(p['pass_completion'] * 100, 0, pct=True), t("Passes réussies", "Pass completion"))
        kpi(s[2], str(int(p['progressive_passes'])), t("Passes progressives", "Progressive passes"))
        kpi(s[3], str(int(p['assists'])), t("Passes décisives", "Assists"))
        st.write("")
        s = st.columns(4)
        kpi(s[0], str(int(p['dribbles_total'])), t("Dribbles tentés", "Dribbles attempted"))
        kpi(s[1], str(int(p['dribbles_won'])), t("Dribbles réussis", "Successful dribbles"))
        kpi(s[2], str(int(p['pressures'])), t("Pressions", "Pressures"))
        kpi(s[3], str(int(p['key_passes'])), t("Passes clés", "Key passes"))

    # ── TACTIQUE ───────────────────────────────────────────────────────
    with tabs[1]:
        ca, cb = st.columns(2)
        with ca:
            st.markdown(f"**{t('Points forts', 'Strengths')}**")
            tags(p['strengths'], "✓ ")
            st.markdown(f"**{t('Points à travailler', 'Areas to improve')}**")
            tags(p['weaknesses'], "✗ ")
        with cb:
            st.markdown(f"**{t('Systèmes de jeu', 'Playing systems')}**")
            tags(p['systems'])
            st.markdown(f"**{t('Dispositifs', 'Formations')}**")
            st.markdown("".join(
                f'<span class="jl-tag" style="{"border-color:var(--jl-teal);color:var(--jl-teal);font-weight:700" if f == p["best_formation"] else ""}">'
                f'{"★ " if f == p["best_formation"] else ""}{f}</span>' for f in p['formations']) or "—", unsafe_allow_html=True)
            if comps:
                st.caption(f"{t('Compétitions :', 'Competitions:')} {' · '.join(comps[:4])}")
        st.caption(t("★ : dispositif le plus adapté.", "★: best-suited formation."))

    # ── MARCHÉ ─────────────────────────────────────────────────────────
    with tabs[2]:
        to = p['transfer_open']
        tl = t("Probable", "Likely") if to >= 65 else t("Incertain", "Uncertain") if to >= 35 else t("Peu probable", "Unlikely")
        c = st.columns(3)
        kpi(c[0], str(p['market_value']), t("Valeur estimée", "Estimated value"))
        kpi(c[1], fr_num(to, 0, pct=True), t("Ouverture au transfert", "Transfer openness"))
        kpi(c[2], tl, t("Statut", "Status"), accent=to >= 65)
        st.write("")
        bar_rows([(t("Probabilité de transaction", "Transaction likelihood"), to)], suffix=t(" %", "%"))
        st.caption(t("Échelle : 0 = bloqué, 50 = neutre, 100 = ouvert.", "Scale: 0 = blocked, 50 = neutral, 100 = open."))
        blockers = []
        if to < 30:
            blockers.append(t("Club peu enclin à céder", "Club reluctant to sell"))
        if p['overall'] >= 85:
            blockers.append(t("Prix élevé, négociation complexe", "High price, complex negotiation"))
        if len(p['weaknesses']) >= 3:
            blockers.append(t("Axes d’amélioration à surveiller", "Areas to improve worth monitoring"))
        if to >= 65:
            blockers.append(t("Fenêtre de transfert favorable", "Favourable transfer window"))
        for b in blockers:
            st.markdown(f"- {b}")

    # ── COMPARAISON ────────────────────────────────────────────────────
    with tabs[3]:
        opts = [pl for pl in df[df['pos'] == p['pos']]['player'].tolist() if pl != p['player']]
        if opts:
            p2_name = st.selectbox(t("Comparer avec", "Compare with"), opts)
            p2 = df[df['player'] == p2_name].iloc[0]
            labels = [t(fr, en) for _, fr, en in ATTR]
            st.plotly_chart(radar([(p['player'], (labels, [float(p[k]) for k, _, _ in ATTR]), C["teal"]),
                                   (p2_name, (labels, [float(p2[k]) for k, _, _ in ATTR]), C["rust"])], height=360),
                            width="stretch", theme="streamlit")
            rows = labels + [t("Note", "Rating"), t("Buts", "Goals"), "xG", t("Transfert (%)", "Transfer (%)")]

            def col_vals(x):
                return [fr_num(float(x[k]), 0) for k, _, _ in ATTR] + [str(x['overall']), str(int(x['goals'])),
                                                           fr_num(x['xg_total'], 2), str(x['transfer_open'])]
            st.dataframe(pd.DataFrame({t("Attribut", "Attribute"): rows, p['player']: col_vals(p), p2_name: col_vals(p2)}),
                         hide_index=True, width="stretch")

    # ── RAPPORT DÉTAILLÉ ───────────────────────────────────────────────
    if has_report:
        with tabs[4]:
            e = enriched
            pct = e.get("percentiles", {})
            n_matches = e.get("matches_analyzed", "—")
            note(t(f"<b>Rapport : données réelles StatsBomb</b>. Statistiques avancées calculées action par action sur "
                   f"<b>{n_matches} matchs</b> des données ouvertes (passes progressives, pressions, interceptions, xG, conduites…), "
                   "contrairement aux scores modélisés de l’onglet Attributs.",
                   f"<b>Report: real StatsBomb data</b>. Advanced stats computed action by action over <b>{n_matches} matches</b> "
                   "of the open data (progressive passes, pressures, interceptions, xG, carries…), unlike the modelled scores of "
                   "the Attributes tab."))

            st.markdown(f"#### {t('Statistiques avancées par 90 minutes', 'Advanced stats per 90 minutes')}")
            r = st.columns(6)
            kpi(r[0], num(e.get("progressive_passes_per90")), t("Passes prog./90", "Prog. passes/90"))
            kpi(r[1], num(e.get("progressive_carries_per90")), t("Conduites prog./90", "Prog. carries/90"))
            kpi(r[2], num(e.get("passes_final_third_per90")), t("Passes dernier tiers/90", "Final-third passes/90"))
            kpi(r[3], num(e.get("pressures_per90")), t("Pressions/90", "Pressures/90"))
            kpi(r[4], num(e.get("interceptions_per90")), t("Interceptions/90", "Interceptions/90"))
            kpi(r[5], num(e.get("ball_recoveries_per90")), t("Récupérations/90", "Recoveries/90"))
            st.write("")
            r = st.columns(6)
            kpi(r[0], num(e.get("xg_total")), t("xG total", "Total xG"))
            kpi(r[1], num(e.get("xg_per90")), "xG/90")
            kpi(r[2], num(e.get("xA_per90")), "xA/90")
            kpi(r[3], num(e.get("key_passes_per90")), t("Passes clés/90", "Key passes/90"))
            pc, dw = e.get('pass_completion_pct'), e.get('duel_win_pct')
            kpi(r[4], fr_num(pc, 1, pct=True) if pc is not None else "—", t("Passes réussies", "Pass completion"))
            kpi(r[5], fr_num(dw, 1, pct=True) if dw is not None else "—", t("Duels gagnés", "Duels won"))
            st.write("")

            col_radar, col_pct = st.columns(2)
            with col_radar:
                st.markdown(f"##### {t('Radar sur données réelles', 'Radar on real data')}")

                def norm(val, lo, hi):
                    if val is None:
                        return 50
                    return max(0, min(100, (val - lo) / (hi - lo + 1e-9) * 100))

                dims = [(t("Progression", "Progression"), norm(e.get("progressive_passes_per90", 0), 0, 20)),
                        (t("Création", "Creation"), norm(e.get("key_passes_per90", 0), 0, 5)),
                        (t("Pressing", "Pressing"), norm(e.get("pressures_per90", 0), 0, 20)),
                        (t("Récupération", "Recovery"), norm(e.get("ball_recoveries_per90", 0), 0, 10)),
                        (t("Interceptions", "Interceptions"), norm(e.get("interceptions_per90", 0), 0, 4)),
                        (t("Précision de passe", "Passing accuracy"), norm(e.get("pass_completion_pct", 0), 60, 100))]
                st.plotly_chart(radar([(p['player'], ([d[0] for d in dims], [d[1] for d in dims]), C["teal"])],
                                      height=320, rng=(0, 100)), width="stretch", theme="streamlit")
            with col_pct:
                st.markdown(f"##### {t('Percentiles par poste', 'Percentiles by position')}")
                if pct:
                    pct_display = [(t("Passes prog./90", "Prog. passes/90"), pct.get("pct_progressive_passes_per90")),
                                   (t("Conduites prog./90", "Prog. carries/90"), pct.get("pct_progressive_carries_per90")),
                                   (t("Pressions/90", "Pressures/90"), pct.get("pct_pressures_per90")),
                                   (t("Interceptions/90", "Interceptions/90"), pct.get("pct_interceptions_per90")),
                                   (t("Récupérations/90", "Recoveries/90"), pct.get("pct_ball_recoveries_per90")),
                                   ("xG/90", pct.get("pct_xg_per90")),
                                   (t("Passes clés/90", "Key passes/90"), pct.get("pct_key_passes_per90")),
                                   (t("Passes réussies", "Pass completion"), pct.get("pct_pass_completion_pct"))]
                    bar_rows([(lab, v) for lab, v in pct_display if v is not None], suffix=t("e", "th"))
                    if e.get("percentile_group"):
                        st.caption(t(f"Groupe de comparaison : {e.get('percentile_group')} ({e.get('percentile_sample_size', '—')} profils).",
                                     f"Comparison group: {e.get('percentile_group')} ({e.get('percentile_sample_size', '—')} profiles)."))
                else:
                    st.caption(t("Percentiles non disponibles.", "Percentiles not available."))

            col_off, col_def = st.columns(2)
            with col_off:
                st.markdown(f"##### {t('Profil offensif', 'Attacking profile')}")
                kv_rows({t("Buts", "Goals"): num(e.get("goals"), 0), t("xG total", "Total xG"): num(e.get("xg_total")),
                         "xG/90": num(e.get("xg_per90")), t("Tirs", "Shots"): num(e.get("shots_total"), 0),
                         t("Tirs/90", "Shots/90"): num(e.get("shots_per90"), 1), "xA/90": num(e.get("xA_per90")),
                         t("Passes clés/90", "Key passes/90"): num(e.get("key_passes_per90"), 1),
                         t("Passes dans le dernier tiers", "Final-third passes"): num(e.get("passes_final_third"), 0),
                         t("Passes progressives", "Progressive passes"): num(e.get("progressive_passes"), 0),
                         t("Conduites progressives", "Progressive carries"): num(e.get("progressive_carries"), 0),
                         t("Distance en conduite", "Carry distance"): f"{num(e.get('carry_distance_total', 0), 0)} m"})
            with col_def:
                st.markdown(f"##### {t('Profil défensif', 'Defensive profile')}")
                dwp = e.get('duel_win_pct')
                kv_rows({t("Pressions", "Pressures"): num(e.get("pressures"), 0),
                         t("Pressions/90", "Pressures/90"): num(e.get("pressures_per90"), 1),
                         t("Duels", "Duels"): num(e.get("duels_total"), 0),
                         t("Duels gagnés", "Duels won"): num(e.get("duels_won"), 0),
                         t("Duels gagnés (%)", "Duels won (%)"): fr_num(dwp, 1, pct=True) if dwp is not None else "—",
                         t("Interceptions", "Interceptions"): num(e.get("interceptions"), 0),
                         t("Interceptions/90", "Interceptions/90"): num(e.get("interceptions_per90"), 1),
                         t("Tacles", "Tackles"): num(e.get("tackles"), 0),
                         t("Tacles/90", "Tackles/90"): num(e.get("tackles_per90"), 1),
                         t("Récupérations", "Recoveries"): num(e.get("ball_recoveries"), 0),
                         t("Récupérations/90", "Recoveries/90"): num(e.get("ball_recoveries_per90"), 1)})

    # ── NOTE DE SCOUT ──────────────────────────────────────────────────
    st.markdown(f"##### {t('Note de scout', 'Scout note')}")
    note_key = f"note_{p['player'].replace(' ', '_').lower()}"
    if note_key not in st.session_state:
        st.session_state[note_key] = ""
    note_scout = st.text_area(
        t("Observations vidéo (Dartfish / Once Sport)", "Video observations (Dartfish / Once Sport)"),
        value=st.session_state[note_key], height=120,
        placeholder=t("Ex. : très bon dans la récupération haute, déclenche le pressing au bon moment…",
                      "E.g. very good at winning the ball high, triggers the press at the right moment…"))
    if st.button(t("Enregistrer la note", "Save the note")):
        st.session_state[note_key] = note_scout
        st.success(t("Note enregistrée pour cette session.", "Note saved for this session."))
    st.caption(t("Note conservée le temps de la session uniquement (pas de base de données branchée).",
                 "Note kept for this session only (no database connected)."))
    if st.session_state[note_key]:
        note(f"{t('Note actuelle :', 'Current note:')} {st.session_state[note_key]}")

footer("Données : StatsBomb (Open Data)", "Data: StatsBomb (Open Data)")
