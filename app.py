"""
ScoutPro — Application Streamlit de recrutement & profilage
Données : StatsBomb Open Data — 2263 joueurs, 18 compétitions
v2 : + onglet Scout Report (stats enrichies CdM 2022 / Euro 2024)
Lancement : streamlit run app.py
"""

import json, ast, os, unicodedata
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="ScoutPro | Football Scouting",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{background:#0a0e1a}
[data-testid="stSidebar"]{background:#0f1624 !important;border-right:1px solid #1e2d45}
[data-testid="stSidebar"] *{color:#c9d1e0 !important}
[data-testid="stSidebar"] input,[data-testid="stSidebar"] select{
background:#1a2235 !important;border:1px solid #2a3a55 !important;color:#e8ecf4 !important;border-radius:8px}
[data-testid="metric-container"]{background:#141e30;border:1px solid #1e2d45;border-radius:10px;padding:12px}
[data-testid="metric-container"] label{color:#6b7fa3 !important;font-size:12px !important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#e8ecf4 !important}
div[data-testid="stDataFrame"]{background:#141e30;border-radius:10px}
.stTabs [data-baseweb="tab-list"]{background:#0f1624;border-radius:8px;padding:4px}
.stTabs [data-baseweb="tab"]{color:#6b7fa3;border-radius:6px}
.stTabs [aria-selected="true"]{background:#1a2235 !important;color:#e8ecf4 !important}
h1,h2,h3{color:#e8ecf4 !important}
p,li{color:#c9d1e0}
.stMarkdown{color:#c9d1e0}
div[data-testid="stVerticalBlock"] > div > div > div{color:#c9d1e0}
</style>
""", unsafe_allow_html=True)


# ── CHARGEMENT DES DONNÉES ───────────────────────────────────────────────────

@st.cache_data
def load_players():
    path = Path("data/players.json")
    if not path.exists():
        st.error("❌ data/players.json introuvable. Lancez : python data_pipeline.py")
        st.stop()
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)
    def safe_parse(x):
        if isinstance(x, list): return x
        if not x or (isinstance(x, float) and pd.isna(x)): return []
        try:
            result = ast.literal_eval(str(x))
            return result if isinstance(result, list) else []
        except Exception:
            return []

    for col in ['formations','strengths','weaknesses','systems','competitions']:
        if col in df.columns:
            df[col] = df[col].apply(safe_parse)
    if 'age' not in df.columns:
        df['age'] = 25
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


# ── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚽ ScoutPro")
    st.caption("Recrutement & Profilage · StatsBomb Open Data")
    st.markdown("---")

    search = st.text_input("🔍 Recherche joueur", placeholder="Nom…")
    pos_options = ["Toutes"] + sorted([str(x) for x in df['pos'].dropna().unique().tolist()])
    pos_sel = st.selectbox("Position", pos_options)
    nat_options = ["Toutes"] + sorted([str(x) for x in df['nationality'].dropna().unique().tolist()])
    nat_sel = st.selectbox("Nationalité", nat_options)
    # Filtrer les équipes nationales de la liste clubs
    NATIONAL_NAMES = {
        'France','Spain','Germany','Portugal','Brazil','Argentina','England',
        'Italy','Netherlands','Belgium','Croatia','Morocco','Senegal','Nigeria',
        'Serbia','Denmark','Switzerland','Austria','Turkey','Ukraine','Poland',
        'Georgia','Scotland','Hungary','Albania','Romania','Slovenia','Uruguay',
        'Colombia','Ecuador','Chile','Mexico','United States','Canada','Japan',
        'South Korea','Australia','Cameroon','Ghana','Tunisia','Saudi Arabia',
        'Iran','Costa Rica','Wales','Czech Republic','Slovakia','Bolivia',
        'Peru','Paraguay','Jamaica',
    }
    all_teams = df['team'].dropna().unique().tolist()
    club_list = sorted([t for t in all_teams if t not in NATIONAL_NAMES])
    clubs = ["Tous"] + club_list
    club_sel = st.selectbox("Club", clubs)
    rating_min = st.slider("Note minimale", 55, 97, 65)
    age_range = st.slider("Tranche d'âge", 17, 40, (17, 35))
    all_forms = ['4-3-3','4-4-2','4-2-3-1','3-5-2','3-4-3','5-3-2']
    form_sel = st.multiselect("Dispositif tactique", all_forms)
    t_opts = {"Tous": None, "Probable (>70%)": "high", "Incertain (40-70%)": "med", "Peu probable (<40%)": "low"}
    transfer_sel = t_opts[st.selectbox("Ouverture au transfert", list(t_opts.keys()))]
    st.markdown("---")
    min_goals = st.slider("Buts min", 0, 20, 0)
    min_xg    = st.slider("xG min", 0.0, 10.0, 0.0, 0.5)

    # MATCHING
    st.markdown("---")
    st.markdown("### 🎯 Matching tactique")
    st.caption("Décris ton style de jeu pour trouver les meilleurs profils")
    style_jeu = st.selectbox("Style de jeu", [
        "— Sélectionner —","Possession / jeu court","Contre-attaque","Pressing haut",
        "Jeu direct / long","Transitions rapides","Bloc bas défensif"
    ])
    formation_eq  = st.selectbox("Formation de ton équipe", [
        "— Sélectionner —","4-3-3","4-4-2","4-2-3-1","3-5-2","3-4-3","5-3-2"
    ])
    poste_besoin  = st.selectbox("Poste recherché en priorité", [
        "— Sélectionner —","GK","CB","LB","RB","CDM","CM","CAM","LW","RW","ST"
    ])
    st.caption("Le matching calcule un score de compatibilité selon les attributs clés du style choisi (vitesse, passe, défense...). Les scores sont normalisés entre 0 et 100%.")
    match_btn = st.button("🔍 Trouver les meilleurs profils ↗", use_container_width=True)


# ── FILTRAGE ─────────────────────────────────────────────────────────────────

mask = pd.Series([True]*len(df))
if search:            mask &= df['player'].str.lower().str.contains(search.lower(), na=False)
if pos_sel  != "Toutes": mask &= df['pos'] == pos_sel
if nat_sel  != "Toutes": mask &= df['nationality'] == nat_sel
if club_sel != "Tous":   mask &= df['team'] == club_sel
mask &= df['overall'] >= rating_min
mask &= df['age'].between(age_range[0], age_range[1])
mask &= df['goals'] >= min_goals
mask &= df['xg_total'] >= min_xg
if form_sel:          mask &= df['formations'].apply(lambda x: any(f in x for f in form_sel))
if transfer_sel == "high": mask &= df['transfer_open'] >= 70
elif transfer_sel == "med": mask &= (df['transfer_open'] >= 40) & (df['transfer_open'] < 70)
elif transfer_sel == "low": mask &= df['transfer_open'] < 40
filtered = df[mask].reset_index(drop=True)


# ── MATCHING LOGIC ────────────────────────────────────────────────────────────

if match_btn and style_jeu != "— Sélectionner —" and poste_besoin != "— Sélectionner —":
    st.markdown("## 🎯 Matching tactique")
    STYLE_WEIGHTS = {
        "Possession / jeu court":  {'pass_score':0.35,'physic_score':0.2,'defense_score':0.2,'dribble_score':0.15,'shoot_score':0.1},
        "Contre-attaque":          {'pace_score':0.35,'shoot_score':0.3,'dribble_score':0.2,'pass_score':0.1,'physic_score':0.05},
        "Pressing haut":           {'physic_score':0.3,'defense_score':0.3,'pace_score':0.2,'pass_score':0.1,'shoot_score':0.1},
        "Jeu direct / long":       {'physic_score':0.35,'shoot_score':0.3,'defense_score':0.2,'pace_score':0.1,'pass_score':0.05},
        "Transitions rapides":     {'pace_score':0.35,'dribble_score':0.25,'shoot_score':0.2,'pass_score':0.15,'physic_score':0.05},
        "Bloc bas défensif":       {'defense_score':0.4,'physic_score':0.3,'pass_score':0.15,'pace_score':0.1,'shoot_score':0.05},
    }
    weights    = STYLE_WEIGHTS.get(style_jeu, {k:0.2 for k in ['pass_score','shoot_score','dribble_score','defense_score','physic_score']})
    candidates = df[df['pos']==poste_besoin].copy()
    if formation_eq != "— Sélectionner —":
        candidates = candidates[candidates['formations'].apply(lambda x: formation_eq in x)]
    candidates['match_score'] = sum(candidates[col]*w for col,w in weights.items() if col in candidates.columns)
    candidates['match_score'] = (candidates['match_score'] - candidates['match_score'].min()) / \
                                 (candidates['match_score'].max() - candidates['match_score'].min() + 1e-9) * 100
    top  = candidates.nlargest(5, 'match_score')
    if top.empty:
        st.warning("Aucun joueur trouvé pour cette combinaison. Essaie un autre poste ou une autre formation.")
        st.stop()
    cols = st.columns(min(5, len(top)))
    for i,(_, p) in enumerate(top.iterrows()):
        with cols[i]:
            score_color = '#00c853' if p['match_score']>=70 else '#f59e0b' if p['match_score']>=50 else '#ef4444'
            st.markdown(f"""
<div style="background:#141e30;border:1px solid #1e2d45;border-radius:12px;padding:16px;text-align:center">
<div style="font-size:28px;font-weight:900;color:{score_color}">{p['match_score']:.0f}%</div>
<div style="font-size:13px;font-weight:700;color:#e8ecf4;margin:6px 0">{p['player'].split()[-1]}</div>
<div style="font-size:11px;color:#6b7fa3">{p['team']}</div>
<div style="background:#1a2235;border-radius:20px;padding:3px 8px;display:inline-block;font-size:10px;color:#00c853;margin-top:6px">{p['pos']} · {p['overall']}</div>
<div style="font-size:10px;color:#4b6080;margin-top:6px">{p['market_value']}</div>
</div>""", unsafe_allow_html=True)
    st.markdown("---")


# ── LAYOUT PRINCIPAL ──────────────────────────────────────────────────────────

col_list, col_detail = st.columns([1, 2], gap="medium")

with col_list:
    st.markdown(f"<div style='font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#4b6080;border-bottom:1px solid #1e2d45;padding-bottom:8px;margin-bottom:16px'>🎯 {len(filtered)} joueurs</div>", unsafe_allow_html=True)
    st.info("🔬 **Scout Report** disponible pour de nombreux joueurs — sélectionne un joueur et vérifie l’onglet 🔬 Scout Report pour ses vraies stats StatsBomb (xG, pressing, passes progressives, percentiles vs groupe de poste).")
    if filtered.empty:
        st.info("Aucun joueur ne correspond.")
    else:
        selected_name = st.selectbox("Sélectionner",
            filtered['player'].tolist(),
            format_func=lambda n: f"{n} ({filtered[filtered['player']==n]['pos'].values[0]}) — {filtered[filtered['player']==n]['overall'].values[0]}"
        )
        selected = filtered[filtered['player']==selected_name].iloc[0]
        st.markdown("---")
        tbl = filtered[['player','pos','team','age','overall','goals','xg_total','transfer_open']].copy()
        tbl.columns = ['Joueur','Pos','Club','Âge','Note','Buts','xG','Transfert']
        tbl['xG'] = tbl['xG'].round(2)
        st.dataframe(tbl, hide_index=True, use_container_width=True, height=380,
            column_config={
                "Note":      st.column_config.ProgressColumn("Note",      min_value=55, max_value=97,  format="%d"),
                "Transfert": st.column_config.ProgressColumn("Transfert", min_value=0,  max_value=100, format="%d%%"),
                "Joueur":    st.column_config.TextColumn("Joueur",    width="large"),
                "Club":      st.column_config.TextColumn("Club",      width="medium"),
                "xG":        st.column_config.NumberColumn("xG",      width="small", format="%.2f"),
                "Buts":      st.column_config.NumberColumn("Buts",    width="small"),
                "Âge":       st.column_config.NumberColumn("Âge",     width="small"),
                "Pos":       st.column_config.TextColumn("Pos",       width="small"),
            })


with col_detail:
    if filtered.empty:
        st.info("Utilisez les filtres pour trouver des joueurs.")
        st.stop()

    p   = selected
    ini = ''.join(w[0] for w in p['player'].split()[:2]).upper()
    comps = p['competitions'] if isinstance(p['competitions'],list) else []

    # ── FIFA CARD ──────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0d2a0d,#091a09,#102810);border:1px solid rgba(0,200,83,0.25);border-radius:16px;padding:24px;text-align:center;margin-bottom:16px">
<div style="font-size:56px;font-weight:900;color:#c8a200;line-height:1">{p['overall']}</div>
<div style="font-size:36px;font-weight:900;color:rgba(100,180,100,0.2);margin:4px 0">{ini}</div>
<div style="font-size:20px;font-weight:800;color:#e8ecf4;letter-spacing:1px">{p['player']}</div>
<div style="font-size:13px;color:#6b7fa3;margin-top:4px">{p['team']} · {p['nationality']} · {p['age']} ans</div>
<div style="display:inline-block;background:rgba(0,200,83,0.15);border:1px solid rgba(0,200,83,0.35);color:#00c853;font-size:11px;font-weight:700;padding:3px 14px;border-radius:20px;letter-spacing:1px;margin-top:8px">{p['pos']}</div>
<div style="display:flex;justify-content:center;gap:16px;margin-top:14px">
{"".join(f'<div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:8px 12px;text-align:center"><div style="font-size:18px;font-weight:800;color:#c8a200">{v}</div><div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.35)">{l}</div></div>'
for v,l in [(p['pace_score'],'PAC'),(p['shoot_score'],'TIR'),(p['pass_score'],'PAS'),(p['dribble_score'],'DRI'),(p['defense_score'],'DEF'),(p['physic_score'],'PHY')])}
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="background:#1a1a0a;border:1px solid #3a3a10;border-radius:8px;padding:8px 14px;margin-bottom:10px;font-size:11px;color:#a0a060">
⚠️ <strong>Données modélisées</strong> — Les notes et scores sont calculés à partir des actions StatsBomb open data.
Ils reflètent l'activité dans les compétitions couvertes, pas le niveau réel du joueur.
L'onglet <strong>🔬 Scout Report</strong> contient les vraies stats avancées pour les joueurs couverts par StatsBomb.
</div>
""", unsafe_allow_html=True)

    st.caption("📅 Données issues de StatsBomb open data — compétitions couvertes : La Liga 2005-2021, UCL 2008-2019, Premier League 2015/16, Ligue 1 2022/23, Bundesliga 2023/24, World Cup 2018 & 2022, Euro 2024. Le club affiché correspond à la période couverte, pas nécessairement au club actuel.")

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Buts",      int(p['goals']))
    m2.metric("xG",        f"{p['xg_total']:.2f}")
    m3.metric("P.clés",    int(p['key_passes']))
    m4.metric("Âge",       int(p['age']))
    m5.metric("Transfert", f"{p['transfer_open']}%")

    st.markdown(f"""
<div style="background:#141e30;border:1px solid #1e2d45;border-radius:10px;padding:10px 18px;margin-top:8px;display:flex;align-items:center;gap:14px">
<span style="color:#6b7fa3;font-size:12px;white-space:nowrap">💶 Valeur estimée</span>
<span style="color:#e8ecf4;font-size:18px;font-weight:700;letter-spacing:0.5px">{p['market_value']}</span>
</div>
""", unsafe_allow_html=True)

    # ── TABS — on ajoute Scout Report ─────────────────────────────────────
    enriched = load_enriched(p['player'])
    has_report = enriched is not None

    tab_labels = ["📊 Attributs", "⚡ Tactique", "💶 Marché", "📈 Comparaison"]
    if has_report:
        tab_labels.append("🔬 Scout Report")

    tabs = st.tabs(tab_labels)
    tab1, tab2, tab3, tab4 = tabs[0], tabs[1], tabs[2], tabs[3]
    tab_report = tabs[4] if has_report else None

    # ── TAB 1 : ATTRIBUTS ─────────────────────────────────────────────────
    with tab1:
        c1,c2 = st.columns(2)
        cats = ['Vitesse','Tir','Passe','Dribble','Défense','Physique']
        vals = [p['pace_score'],p['shoot_score'],p['pass_score'],p['dribble_score'],p['defense_score'],p['physic_score']]
        fig = go.Figure(go.Scatterpolar(
            r=vals+[vals[0]], theta=cats+[cats[0]], fill='toself',
            fillcolor='rgba(0,200,83,0.12)', line=dict(color='#00c853',width=2)))
        fig.update_layout(polar=dict(bgcolor='#0d1f0d',
            radialaxis=dict(visible=True,range=[40,99],color='#4b6080',gridcolor='#1e2d45'),
            angularaxis=dict(color='#c9d1e0',gridcolor='#1e2d45')),
            showlegend=False,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
            height=280,margin=dict(l=30,r=30,t=20,b=20))
        c1.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("<div style='font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#4b6080;margin-bottom:12px'>Attributs</div>",unsafe_allow_html=True)
            def bc(v): return '#10b981' if v>=80 else '#3b82f6' if v>=70 else '#f59e0b' if v>=60 else '#ef4444'
            for attr,val in zip(cats,vals):
                st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
<div style="width:72px;font-size:12px;color:#6b7fa3">{attr}</div>
<div style="flex:1;background:#1a2235;border-radius:3px;height:7px">
<div style="width:{val}%;background:{bc(val)};height:7px;border-radius:3px"></div></div>
<div style="width:28px;font-size:13px;font-weight:600;color:{bc(val)};text-align:right">{val}</div>
</div>""",unsafe_allow_html=True)

        st.markdown("---")
        sc1,sc2,sc3,sc4 = st.columns(4)
        sc1.metric("Passes totales", int(p['passes_total']));    sc1.metric("Complétion", f"{p['pass_completion']*100:.0f}%")
        sc2.metric("Passes prog.",   int(p['progressive_passes'])); sc2.metric("Dribbles",  int(p['dribbles_total']))
        sc3.metric("Drib. réussis",  int(p['dribbles_won']));     sc3.metric("Pressings",  int(p['pressures']))
        sc4.metric("Assists",        int(p['assists']));           sc4.metric("Passes clés",int(p['key_passes']))

    # ── TAB 2 : TACTIQUE ──────────────────────────────────────────────────
    with tab2:
        ca,cb = st.columns(2)
        with ca:
            st.markdown("<div style='font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#4b6080;margin-bottom:10px'>✅ Points forts</div>",unsafe_allow_html=True)
            st.markdown(''.join(f'<span style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:#10b981;border-radius:20px;padding:4px 10px;font-size:11px;margin:3px;display:inline-block">✓ {s}</span>' for s in p['strengths']), unsafe_allow_html=True)
            st.markdown("<div style='font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#4b6080;margin:12px 0 10px'>❌ Points faibles</div>",unsafe_allow_html=True)
            st.markdown(''.join(f'<span style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#ef4444;border-radius:20px;padding:4px 10px;font-size:11px;margin:3px;display:inline-block">✗ {s}</span>' for s in p['weaknesses']), unsafe_allow_html=True)
        with cb:
            st.markdown("<div style='font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#4b6080;margin-bottom:10px'>🔷 Systèmes</div>",unsafe_allow_html=True)
            st.markdown(''.join(f'<span style="background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.3);color:#60a5fa;border-radius:20px;padding:4px 10px;font-size:11px;margin:3px;display:inline-block">◆ {s}</span>' for s in p['systems']), unsafe_allow_html=True)
            st.markdown("<div style='font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#4b6080;margin:12px 0 10px'>📐 Dispositifs</div>",unsafe_allow_html=True)
            st.markdown(''.join(f'<span style="background:{"rgba(0,200,83,0.15)" if f==p["best_formation"] else "rgba(139,92,246,0.15)"};border:1px solid {"rgba(0,200,83,0.35)" if f==p["best_formation"] else "rgba(139,92,246,0.35)"};color:{"#00c853" if f==p["best_formation"] else "#a78bfa"};border-radius:20px;padding:4px 10px;font-size:11px;margin:3px;display:inline-block">{"★ " if f==p["best_formation"] else ""}{f}</span>' for f in p['formations']), unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:12px;font-size:12px;color:#6b7fa3'>Compétitions : {' · '.join(comps[:4])}</div>", unsafe_allow_html=True)

    # ── TAB 3 : MARCHÉ ────────────────────────────────────────────────────
    with tab3:
        to = p['transfer_open']
        tc = '#10b981' if to>=65 else '#f59e0b' if to>=35 else '#ef4444'
        tl = 'Probable' if to>=65 else 'Incertain' if to>=35 else 'Peu probable'
        c1,c2,c3 = st.columns(3)
        c1.metric("Valeur estimée", p['market_value'])
        c2.metric("Transfert",      f"{to}%")
        c3.metric("Statut",         tl)
        st.markdown(f"""
<div style="background:#141e30;border:1px solid #1e2d45;border-radius:12px;padding:16px;margin-top:12px">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
<span style="font-size:13px;color:#8b97b0">Probabilité de transaction</span>
<span style="background:{tc}22;border:1px solid {tc}55;color:{tc};border-radius:20px;padding:3px 12px;font-size:12px;font-weight:600">{tl}</span>
</div>
<div style="height:8px;border-radius:4px;background:linear-gradient(90deg,#ef4444,#f59e0b,#10b981)">
<div style="width:{to}%;height:8px"></div></div>
<div style="display:flex;justify-content:space-between;font-size:10px;color:#4b6080;margin-top:4px">
<span>Bloqué</span><span>Neutre</span><span>Ouvert</span></div>
</div>""", unsafe_allow_html=True)
        blockers = []
        if to<30:              blockers.append("🔴 Club peu enclin à céder")
        if p['overall']>=85:   blockers.append("🟡 Prix élevé — négociation complexe")
        if len(p['weaknesses'])>=3: blockers.append("🟡 Axes d'amélioration à surveiller")
        if to>=65:             blockers.append("🟢 Fenêtre de transfert favorable")
        for b in blockers:     st.markdown(f"- {b}")

    # ── TAB 4 : COMPARAISON ───────────────────────────────────────────────
    with tab4:
        same_pos = df[df['pos']==p['pos']]['player'].tolist()
        opts = [pl for pl in same_pos if pl!=p['player']]
        if opts:
            p2_name = st.selectbox("Comparer avec", opts)
            p2      = df[df['player']==p2_name].iloc[0]
            attrs   = ['pace_score','shoot_score','pass_score','dribble_score','defense_score','physic_score']
            labels  = ['Vitesse','Tir','Passe','Dribble','Défense','Physique']
            fig2 = go.Figure()
            fig2.add_trace(go.Scatterpolar(r=[p[a] for a in attrs]+[p[attrs[0]]],  theta=labels+[labels[0]],
                fill='toself', fillcolor='rgba(0,200,83,0.12)',  line=dict(color='#00c853',width=2), name=p['player']))
            fig2.add_trace(go.Scatterpolar(r=[p2[a] for a in attrs]+[p2[attrs[0]]],theta=labels+[labels[0]],
                fill='toself', fillcolor='rgba(59,130,246,0.12)',line=dict(color='#3b82f6',width=2), name=p2_name))
            fig2.update_layout(polar=dict(bgcolor='#0d1222',
                radialaxis=dict(visible=True,range=[40,99],color='#4b6080',gridcolor='#1e2d45'),
                angularaxis=dict(color='#c9d1e0',gridcolor='#1e2d45')),
                legend=dict(bgcolor='rgba(0,0,0,0)',font=dict(color='#c9d1e0')),
                paper_bgcolor='rgba(0,0,0,0)',height=340,margin=dict(l=40,r=40,t=20,b=20))
            st.plotly_chart(fig2, use_container_width=True)
            cmp = pd.DataFrame({'Attribut':labels+['Overall','Âge','Buts','xG','Transf%'],
                p['player']: [p[a] for a in attrs]+[p['overall'],int(p['age']),int(p['goals']),round(p['xg_total'],2),p['transfer_open']],
                p2_name:     [p2[a] for a in attrs]+[p2['overall'],int(p2['age']),int(p2['goals']),round(p2['xg_total'],2),p2['transfer_open']]})
            st.dataframe(cmp, hide_index=True, use_container_width=True)

    # ── TAB 5 : SCOUT REPORT ─────────────────────────────────────────────
    if has_report and tab_report is not None:
        with tab_report:
            e = enriched
            pct = e.get("percentiles", {})
            n_matches = e.get("matches_analyzed", "—")

            # ── Explication du Scout Report ────────────────────────────────
            st.markdown(f"""
<div style="background:#0f1a2e;border:1px solid #1e3a5f;border-radius:12px;padding:18px 22px;margin-bottom:20px">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
<div style="font-size:15px;font-weight:700;color:#60a5fa">🔬 Scout Report — Données réelles StatsBomb</div>
<div style="font-size:10px;color:#2563eb;background:#1e3a5f;border-radius:6px;padding:4px 10px;white-space:nowrap">Open Data</div>
</div>
<div style="font-size:12px;color:#8b97b0;line-height:1.7">
Cet onglet enrichit la fiche joueur avec des <strong style="color:#c9d1e0">stats avancées calculées sur les vrais événements StatsBomb</strong> 
— <strong style="color:#e8ecf4">{n_matches} matchs analysés</strong> issus des données StatsBomb open data.<br>
Contrairement aux scores FIFA-like de l'onglet Attributs (modélisés), ces données sont <strong style="color:#c9d1e0">extraites action par action</strong> : 
passes progressives, pressing, interceptions, xG réels, carries...<br>
Disponible uniquement pour les joueurs de l'Équipe de France présents dans les données StatsBomb open data.
</div>
</div>
""", unsafe_allow_html=True)

            # ── Métriques clés ──────────────────────────────────────────────
            st.markdown("#### 📊 Stats avancées / 90 min")
            r1c1,r1c2,r1c3,r1c4,r1c5,r1c6 = st.columns(6)
            r1c1.metric("Passes prog./90",    e.get("progressive_passes_per90","—"))
            r1c2.metric("Carries prog./90",   e.get("progressive_carries_per90","—"))
            r1c3.metric("Passes tiers off./90",e.get("passes_final_third_per90","—"))
            r1c4.metric("Pressings/90",       e.get("pressures_per90","—"))
            r1c5.metric("Interceptions/90",   e.get("interceptions_per90","—"))
            r1c6.metric("Récups./90",         e.get("ball_recoveries_per90","—"))

            r2c1,r2c2,r2c3,r2c4,r2c5,r2c6 = st.columns(6)
            r2c1.metric("xG total",           e.get("xg_total","—"))
            r2c2.metric("xG/90",              e.get("xg_per90","—"))
            r2c3.metric("xA/90",              e.get("xA_per90","—"))
            r2c4.metric("Passes clés/90",     e.get("key_passes_per90","—"))
            r2c5.metric("Complétion passes",  f"{e.get('pass_completion_pct','—')}%")
            r2c6.metric("Duels gagnés %",     f"{e.get('duel_win_pct','—')}%")

            st.markdown("---")

            # ── Radar enrichi (6 dimensions réelles) ───────────────────────
            col_radar, col_pct = st.columns([1, 1])

            with col_radar:
                st.markdown("##### Radar — données réelles StatsBomb")

                def norm(val, lo, hi):
                    """Normalise une valeur entre 0 et 100."""
                    if val is None: return 50
                    return max(0, min(100, (val - lo) / (hi - lo + 1e-9) * 100))

                radar_dims = [
                    ("Progression",   norm(e.get("progressive_passes_per90",0),  0, 20)),
                    ("Création",      norm(e.get("key_passes_per90",0),           0, 5)),
                    ("Pressing",      norm(e.get("pressures_per90",0),            0, 20)),
                    ("Récupération",  norm(e.get("ball_recoveries_per90",0),      0, 10)),
                    ("Interceptions", norm(e.get("interceptions_per90",0),        0, 4)),
                    ("Volume passes", norm(e.get("pass_completion_pct",0),        60, 100)),
                ]
                r_labels = [d[0] for d in radar_dims]
                r_vals   = [d[1] for d in radar_dims]

                fig_r = go.Figure(go.Scatterpolar(
                    r=r_vals+[r_vals[0]], theta=r_labels+[r_labels[0]], fill='toself',
                    fillcolor='rgba(96,165,250,0.15)', line=dict(color='#60a5fa', width=2)))
                fig_r.update_layout(
                    polar=dict(bgcolor='#0d1222',
                        radialaxis=dict(visible=True, range=[0,100], color='#4b6080', gridcolor='#1e2d45'),
                        angularaxis=dict(color='#c9d1e0', gridcolor='#1e2d45')),
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=300,
                    margin=dict(l=30,r=30,t=20,b=20))
                st.plotly_chart(fig_r, use_container_width=True)

            with col_pct:
                st.markdown("##### Percentiles vs dataset")
                if pct:
                    pct_display = {
                        "Passes prog./90":   pct.get("pct_progressive_passes_per90"),
                        "Carries prog./90":  pct.get("pct_progressive_carries_per90"),
                        "Pressing/90":       pct.get("pct_pressures_per90"),
                        "Interceptions/90":  pct.get("pct_interceptions_per90"),
                        "Récupérations/90":  pct.get("pct_ball_recoveries_per90"),
                        "xG/90":             pct.get("pct_xg_per90"),
                        "Passes clés/90":    pct.get("pct_key_passes_per90"),
                        "Complétion passes": pct.get("pct_pass_completion_pct"),
                    }
                    for label, val in pct_display.items():
                        if val is None: continue
                        color = '#10b981' if val>=75 else '#3b82f6' if val>=50 else '#f59e0b' if val>=25 else '#ef4444'
                        bar_w = int(val)
                        st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
<div style="width:130px;font-size:11px;color:#8b97b0">{label}</div>
<div style="flex:1;background:#1a2235;border-radius:3px;height:6px">
<div style="width:{bar_w}%;background:{color};height:6px;border-radius:3px"></div></div>
<div style="width:36px;font-size:12px;font-weight:600;color:{color};text-align:right">{val:.0f}e</div>
</div>""", unsafe_allow_html=True)
                else:
                    st.caption("Percentiles non disponibles — relancer le pipeline avec plusieurs joueurs.")

            st.markdown("---")

            # ── Détail offensif / défensif côte à côte ─────────────────────
            col_off, col_def = st.columns(2)

            with col_off:
                st.markdown("##### Profil offensif")
                def fmt(v, dec=2):
                    if v is None: return "—"
                    if isinstance(v, float): return round(v, dec)
                    return v

                off_data = {
                    "Buts":              fmt(e.get("goals"), 0),
                    "xG total":          fmt(e.get("xg_total")),
                    "xG/90":             fmt(e.get("xg_per90")),
                    "Tirs total":        fmt(e.get("shots_total"), 0),
                    "Tirs/90":           fmt(e.get("shots_per90"), 1),
                    "xA/90":             fmt(e.get("xA_per90")),
                    "Passes clés/90":    fmt(e.get("key_passes_per90"), 1),
                    "Passes tiers off.": fmt(e.get("passes_final_third"), 0),
                    "Passes prog.":      fmt(e.get("progressive_passes"), 0),
                    "Carries prog.":     fmt(e.get("progressive_carries"), 0),
                    "Distance portée":   f"{round(e.get('carry_distance_total', 0))} m",
                }
                for k, v in off_data.items():
                    st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2235;font-size:12px">
<span style="color:#6b7fa3">{k}</span><span style="color:#e8ecf4;font-weight:500">{v}</span></div>""", unsafe_allow_html=True)

            with col_def:
                st.markdown("##### Profil défensif")
                def_data = {
                    "Pressings":          fmt(e.get("pressures"), 0),
                    "Pressings/90":       fmt(e.get("pressures_per90"), 1),
                    "Duels total":        fmt(e.get("duels_total"), 0),
                    "Duels gagnés":       fmt(e.get("duels_won"), 0),
                    "Duels gagnés %":     f"{round(e.get('duel_win_pct', 0), 1)}%",
                    "Interceptions":      fmt(e.get("interceptions"), 0),
                    "Interceptions/90":   fmt(e.get("interceptions_per90"), 1),
                    "Interc. gagnées":    fmt(e.get("interceptions_won"), 0),
                    "Tacles":             fmt(e.get("tackles"), 0),
                    "Tacles/90":          fmt(e.get("tackles_per90"), 1),
                    "Récupérations":      fmt(e.get("ball_recoveries"), 0),
                    "Récupérations/90":   fmt(e.get("ball_recoveries_per90"), 1),
                }
                for k, v in def_data.items():
                    st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2235;font-size:12px">
<span style="color:#6b7fa3">{k}</span><span style="color:#e8ecf4;font-weight:500">{v}</span></div>""", unsafe_allow_html=True)

            st.markdown("---")

            # ── Note de scout ───────────────────────────────────────────────
            st.markdown("##### 📝 Note de scout")
            st.markdown(f"""
<div style="background:#0f1624;border:1px solid #1e2d45;border-left:3px solid #60a5fa;border-radius:8px;padding:14px 16px;font-size:13px;color:#c9d1e0;line-height:1.7">
<em>Zone de saisie — ajouter ici l'analyse qualitative issue des vidéos Dartfish / Once Sport.
Observations tactiques, points forts observés, contexte des actions clés...</em>
</div>
""", unsafe_allow_html=True)

            note_scout = st.text_area(
                "Observations vidéo (Dartfish / Once Sport)",
                placeholder="Ex : Très bon dans la récupération haute, déclenche le pressing au bon moment. Vision de jeu remarquable dans les transitions...",
                height=120,
                label_visibility="collapsed"
            )

            if note_scout:
                note_path = Path(f"data/enriched/notes_{p['player'].replace(' ','_').lower()}.txt")
                if st.button("💾 Sauvegarder la note"):
                    note_path.write_text(note_scout, encoding="utf-8")
                    st.success(f"Note sauvegardée → {note_path}")

            # Load existing note if any
            note_path = Path(f"data/enriched/notes_{p['player'].replace(' ','_').lower()}.txt")
            if note_path.exists():
                st.markdown(f"""
<div style="background:#0a1a0a;border:1px solid rgba(16,185,129,0.3);border-radius:8px;padding:12px 16px;font-size:12px;color:#6b9e6b;margin-top:8px">
📎 Note existante : {note_path.read_text(encoding='utf-8')}
</div>""", unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────────
    st.markdown("<div style='text-align:center;color:#1e2d45;font-size:11px;margin-top:20px'>ScoutPro v2 · Julie Landrevie · StatsBomb Open Data · 2263 joueurs · 18 compétitions · Scout Report CdM 2022 / Euro 2024</div>", unsafe_allow_html=True)
