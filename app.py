"""
ScoutPro — Application Streamlit de recrutement & profilage
Données : StatsBomb Open Data — 2263 joueurs, 18 compétitions
Lancement : streamlit run app.py
"""

import json, ast
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


@st.cache_data
def load_players():
    path = Path("data/players.json")
    if not path.exists():
        st.error("❌ data/players.json introuvable. Lancez : python data_pipeline.py")
        st.stop()
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)
    for col in ['formations','strengths','weaknesses','systems','competitions']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x if isinstance(x,list) else
                                    (ast.literal_eval(str(x)) if x else []))
    if 'age' not in df.columns:
        df['age'] = 25
    return df

df_all = load_players()
df = df_all.sort_values('overall', ascending=False).drop_duplicates('player').reset_index(drop=True)

# ── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ ScoutPro")
    st.caption("Recrutement & Profilage · StatsBomb Open Data")
    st.markdown("---")

    search = st.text_input("🔍 Recherche joueur", placeholder="Nom…")

    pos_options = ["Toutes"] + sorted(df['pos'].unique().tolist())
    pos_sel = st.selectbox("Position", pos_options)

    nat_options = ["Toutes"] + sorted(df['nationality'].dropna().unique().tolist())
    nat_sel = st.selectbox("Nationalité", nat_options)

    clubs = ["Tous"] + sorted(df['team'].dropna().unique().tolist())
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
    formation_eq = st.selectbox("Formation de ton équipe", [
        "— Sélectionner —","4-3-3","4-4-2","4-2-3-1","3-5-2","3-4-3","5-3-2"
    ])
    poste_besoin = st.selectbox("Poste recherché en priorité", [
        "— Sélectionner —","GK","CB","LB","RB","CDM","CM","CAM","LW","RW","ST"
    ])
    match_btn = st.button("🔍 Trouver les meilleurs profils ↗", use_container_width=True)


# ── FILTRAGE ─────────────────────────────────────────────────────────────────
mask = pd.Series([True]*len(df))
if search:       mask &= df['player'].str.lower().str.contains(search.lower(), na=False)
if pos_sel != "Toutes":  mask &= df['pos'] == pos_sel
if nat_sel != "Toutes":  mask &= df['nationality'] == nat_sel
if club_sel != "Tous":   mask &= df['team'] == club_sel
mask &= df['overall'] >= rating_min
mask &= df['age'].between(age_range[0], age_range[1])
mask &= df['goals'] >= min_goals
mask &= df['xg_total'] >= min_xg
if form_sel: mask &= df['formations'].apply(lambda x: any(f in x for f in form_sel))
if transfer_sel == "high": mask &= df['transfer_open'] >= 70
elif transfer_sel == "med": mask &= (df['transfer_open'] >= 40) & (df['transfer_open'] < 70)
elif transfer_sel == "low": mask &= df['transfer_open'] < 40
filtered = df[mask].reset_index(drop=True)


# ── MATCHING LOGIC ────────────────────────────────────────────────────────────
if match_btn and style_jeu != "— Sélectionner —" and poste_besoin != "— Sélectionner —":
    st.markdown("## 🎯 Matching tactique")
    STYLE_WEIGHTS = {
        "Possession / jeu court":    {'pass_score':0.35,'physic_score':0.2,'defense_score':0.2,'dribble_score':0.15,'shoot_score':0.1},
        "Contre-attaque":            {'pace_score':0.35,'shoot_score':0.3,'dribble_score':0.2,'pass_score':0.1,'physic_score':0.05},
        "Pressing haut":             {'physic_score':0.3,'defense_score':0.3,'pace_score':0.2,'pass_score':0.1,'shoot_score':0.1},
        "Jeu direct / long":         {'physic_score':0.35,'shoot_score':0.3,'defense_score':0.2,'pace_score':0.1,'pass_score':0.05},
        "Transitions rapides":       {'pace_score':0.35,'dribble_score':0.25,'shoot_score':0.2,'pass_score':0.15,'physic_score':0.05},
        "Bloc bas défensif":         {'defense_score':0.4,'physic_score':0.3,'pass_score':0.15,'pace_score':0.1,'shoot_score':0.05},
    }
    weights = STYLE_WEIGHTS.get(style_jeu, {k:0.2 for k in ['pass_score','shoot_score','dribble_score','defense_score','physic_score']})
    candidates = df[df['pos']==poste_besoin].copy()
    if formation_eq != "— Sélectionner —":
        candidates = candidates[candidates['formations'].apply(lambda x: formation_eq in x)]
    candidates['match_score'] = sum(candidates[col]*w for col,w in weights.items())
    candidates['match_score'] = (candidates['match_score'] - candidates['match_score'].min()) / \
                                 (candidates['match_score'].max() - candidates['match_score'].min() + 1e-9) * 100
    top = candidates.nlargest(5, 'match_score')

    cols = st.columns(5)
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
        tbl.columns = ['Joueur','Pos','Club','Âge','Note','Buts','xG','Transf%']
        tbl['xG'] = tbl['xG'].round(2)
        st.dataframe(tbl, hide_index=True, use_container_width=True, height=380,
            column_config={
                "Note":   st.column_config.ProgressColumn("Note",   min_value=55, max_value=97, format="%d"),
                "Transf%":st.column_config.ProgressColumn("Transf%",min_value=0,  max_value=100,format="%d%%"),
            })

with col_detail:
    if filtered.empty:
        st.info("Utilisez les filtres pour trouver des joueurs.")
        st.stop()

    p = selected
    ini = ''.join(w[0] for w in p['player'].split()[:2]).upper()
    comps = p['competitions'] if isinstance(p['competitions'],list) else []

    # FIFA card
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

    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Buts",  int(p['goals']))
    m2.metric("xG",    f"{p['xg_total']:.2f}")
    m3.metric("P.clés",int(p['key_passes']))
    m4.metric("Âge",   int(p['age']))
    m5.metric("Valeur",p['market_value'])
    m6.metric("Transf%",f"{p['transfer_open']}%")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Attributs","⚡ Tactique","💶 Marché","📈 Comparaison"])

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
            showlegend=False,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=280,margin=dict(l=30,r=30,t=20,b=20))
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
        sc1.metric("Passes totales",int(p['passes_total'])); sc1.metric("Complétion",f"{p['pass_completion']*100:.0f}%")
        sc2.metric("Passes prog.",int(p['progressive_passes'])); sc2.metric("Dribbles",int(p['dribbles_total']))
        sc3.metric("Drib. réussis",int(p['dribbles_won'])); sc3.metric("Pressings",int(p['pressures']))
        sc4.metric("Assists",int(p['assists'])); sc4.metric("Passes clés",int(p['key_passes']))

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

    with tab3:
        to = p['transfer_open']
        tc = '#10b981' if to>=65 else '#f59e0b' if to>=35 else '#ef4444'
        tl = 'Probable' if to>=65 else 'Incertain' if to>=35 else 'Peu probable'
        c1,c2,c3 = st.columns(3)
        c1.metric("Valeur estimée", p['market_value'])
        c2.metric("Transfert", f"{to}%")
        c3.metric("Statut", tl)
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
        if to<30: blockers.append("🔴 Club peu enclin à céder")
        if p['overall']>=85: blockers.append("🟡 Prix élevé — négociation complexe")
        if len(p['weaknesses'])>=3: blockers.append("🟡 Axes d'amélioration à surveiller")
        if to>=65: blockers.append("🟢 Fenêtre de transfert favorable")
        for b in blockers: st.markdown(f"- {b}")

    with tab4:
        same_pos = df[df['pos']==p['pos']]['player'].tolist()
        opts = [pl for pl in same_pos if pl!=p['player']]
        if opts:
            p2_name = st.selectbox("Comparer avec", opts)
            p2 = df[df['player']==p2_name].iloc[0]
            attrs = ['pace_score','shoot_score','pass_score','dribble_score','defense_score','physic_score']
            labels = ['Vitesse','Tir','Passe','Dribble','Défense','Physique']
            fig2 = go.Figure()
            fig2.add_trace(go.Scatterpolar(r=[p[a] for a in attrs]+[p[attrs[0]]], theta=labels+[labels[0]],
                fill='toself', fillcolor='rgba(0,200,83,0.12)', line=dict(color='#00c853',width=2), name=p['player']))
            fig2.add_trace(go.Scatterpolar(r=[p2[a] for a in attrs]+[p2[attrs[0]]], theta=labels+[labels[0]],
                fill='toself', fillcolor='rgba(59,130,246,0.12)', line=dict(color='#3b82f6',width=2), name=p2_name))
            fig2.update_layout(polar=dict(bgcolor='#0d1222',
                radialaxis=dict(visible=True,range=[40,99],color='#4b6080',gridcolor='#1e2d45'),
                angularaxis=dict(color='#c9d1e0',gridcolor='#1e2d45')),
                legend=dict(bgcolor='rgba(0,0,0,0)',font=dict(color='#c9d1e0')),
                paper_bgcolor='rgba(0,0,0,0)',height=340,margin=dict(l=40,r=40,t=20,b=20))
            st.plotly_chart(fig2, use_container_width=True)
            cmp = pd.DataFrame({'Attribut':labels+['Overall','Âge','Buts','xG','Transf%'],
                p['player']:[p[a] for a in attrs]+[p['overall'],int(p['age']),int(p['goals']),round(p['xg_total'],2),p['transfer_open']],
                p2_name:[p2[a] for a in attrs]+[p2['overall'],int(p2['age']),int(p2['goals']),round(p2['xg_total'],2),p2['transfer_open']]})
            st.dataframe(cmp, hide_index=True, use_container_width=True)

st.markdown("<div style='text-align:center;color:#1e2d45;font-size:11px;margin-top:20px'>ScoutPro · Julie Landrevie · StatsBomb Open Data · 2263 joueurs · 18 compétitions</div>", unsafe_allow_html=True)
