"""Sistema de diseño de EduPerú IA (estilo SaaS, modo claro premium).

Todo el CSS vive aquí. Para cambiar colores o tipografía basta con editar los tokens de :root.
Se conservan los nombres de clase que usan las vistas (hero, chip, tool-*, curso-*, usercard...).
"""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');

/* ================= TOKENS ================= */
:root {
  --brand-1:#4F46E5; --brand-2:#7C3AED; --brand-soft:#EEF2FF; --brand-soft-2:#F5F3FF;
  --ink:#111827; --ink-2:#374151; --muted:#6B7280;
  --bg:#F8F9FC; --surface:#FFFFFF; --border:#E5E7EB;
  --ok-bg:#ECFDF5; --ok-fg:#047857; --warn-bg:#FFFBEB; --warn-fg:#B45309;
  --err-bg:#FEF2F2; --err-fg:#B91C1C; --info-bg:#EEF2FF; --info-fg:#4338CA;
  --radius:16px; --radius-sm:12px;
  --shadow:0 4px 20px -2px rgba(0,0,0,.05); --shadow-hover:0 12px 30px -6px rgba(79,70,229,.18);
  --grad:linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%);
}

/* ================= BASE ================= */
.stApp { background: var(--bg); }
.stApp, .stMarkdown, p, label, li, input, textarea, button, h1, h2, h3, h4, h5, h6,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
  font-family:'Plus Jakarta Sans','Inter',system-ui,-apple-system,'Segoe UI',sans-serif !important;
}
.main .block-container { padding-top:1.6rem; padding-bottom:4rem; max-width:1140px; }
h1 { font-weight:800; color:var(--ink); letter-spacing:-.02em; font-size:2rem; }
h2, h3 { font-weight:700; color:var(--ink); letter-spacing:-.01em; margin-top:.6rem; }
h4, h5 { font-weight:700; color:var(--ink-2); }
div[data-testid="stVerticalBlock"] { gap:1rem; }
div[data-testid="stForm"] { border:none; padding:0; }
footer, #MainMenu { visibility:hidden; }
[data-testid="stStatusWidget"] { display:none !important; }
[data-stale="true"], .stApp [data-stale="true"] { opacity:1 !important; transition:none !important; }
hr { border-color:var(--border) !important; }

/* ================= BOTONES ================= */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius:var(--radius-sm); font-weight:600; border:1px solid var(--border);
  background:var(--surface); color:var(--ink-2); padding:.5rem 1rem; min-height:2.6rem;
  transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease, background .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  transform:translateY(-1px); border-color:#C7D2FE; color:var(--brand-1);
  box-shadow:0 6px 16px -6px rgba(79,70,229,.25);
}
.stButton > button:active { transform:translateY(0); }
button[kind="primary"], button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background:var(--grad) !important; border:0 !important; color:#fff !important;
  box-shadow:0 6px 16px -6px rgba(79,70,229,.55);
}
button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p { color:#fff !important; }
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
  filter:brightness(1.07); box-shadow:0 10px 22px -8px rgba(79,70,229,.6); color:#fff !important;
}
button:focus-visible { outline:3px solid #C7D2FE !important; outline-offset:1px; }
/* botón eliminar: se tiñe de rojo suave al pasar el cursor */
[class*="st-key-x_"] button:hover, [class*="st-key-del_"] button:hover, [class*="st-key-ev_del_"] button:hover {
  background:var(--err-bg) !important; border-color:#FCA5A5 !important; color:var(--err-fg) !important;
}
/* botón ← Volver */
.st-key-btn_volver button {
  background:transparent; border:1px solid transparent; color:var(--muted); font-weight:600;
  padding:.25rem .7rem; min-height:2rem; box-shadow:none;
}
.st-key-btn_volver button:hover { background:var(--brand-soft); color:var(--brand-1); border-color:#C7D2FE; transform:none; }

/* ================= CAMPOS ================= */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], .stNumberInput > div > div {
  border-radius:var(--radius-sm) !important;
}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
  background:var(--surface) !important; border-color:var(--border) !important;
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within {
  border-color:var(--brand-1) !important; box-shadow:0 0 0 3px rgba(79,70,229,.15) !important;
}
label p, [data-testid="stWidgetLabel"] p { font-weight:600; color:var(--ink-2); font-size:.88rem; }

/* ================= ALERTAS (pasteles suaves) ================= */
div[data-testid="stAlert"] { border-radius:14px; border:1px solid rgba(17,24,39,.06); box-shadow:var(--shadow); }
div[data-testid="stAlert"] p { font-size:.93rem; line-height:1.5; }

/* ================= EXPANDERS / TABS / TABLAS ================= */
[data-testid="stExpander"] { border:1px solid var(--border) !important; border-radius:var(--radius) !important;
  background:var(--surface); box-shadow:var(--shadow); overflow:hidden; }
[data-testid="stExpander"] summary { font-weight:600; color:var(--ink-2); }
[data-testid="stExpander"] summary:hover { color:var(--brand-1); }
[data-baseweb="tab-list"] { gap:.25rem; border-bottom:1px solid var(--border); }
[data-baseweb="tab"] { border-radius:10px 10px 0 0; font-weight:600; }
[data-baseweb="tab"][aria-selected="true"] { color:var(--brand-1); }
[data-baseweb="tab-highlight"] { background:var(--grad) !important; height:3px; border-radius:3px; }
[data-testid="stDataFrame"], [data-testid="stDataEditor"] { border:1px solid var(--border); border-radius:var(--radius-sm); overflow:hidden; }
[data-testid="stMetric"] { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  padding:.9rem 1rem; box-shadow:var(--shadow); }
[data-testid="stMetricValue"] { font-weight:800; color:var(--ink); }
[data-testid="stProgress"] > div > div > div > div { background:var(--grad); }

/* ================= BARRA LATERAL ================= */
[data-testid="stSidebar"] { background:var(--surface); border-right:1px solid var(--border); }
[data-testid="stSidebar"] > div:first-child { padding:1.2rem 1rem 1rem; }
.brand { font-size:1.45rem; font-weight:800; letter-spacing:-.02em; margin:.1rem 0 1.1rem .3rem;
  background:var(--grad); -webkit-background-clip:text; background-clip:text; color:transparent; }
.usercard { display:flex; align-items:center; gap:.75rem; background:linear-gradient(180deg,#FAFAFF,#F5F3FF);
  border:1px solid #E0E7FF; border-radius:var(--radius); padding:.8rem .9rem; margin-bottom:1.1rem; }
.avatar { flex:0 0 auto; width:42px; height:42px; border-radius:12px; color:#fff; font-weight:800; font-size:1.1rem;
  display:flex; align-items:center; justify-content:center; background:var(--grad);
  box-shadow:0 6px 14px -4px rgba(79,70,229,.5); }
.usercard .nombre { font-weight:700; color:var(--ink); line-height:1.2; font-size:.95rem; }
.usercard .rol { font-size:.74rem; color:var(--muted); font-weight:500; }
.chip { display:inline-block; border-radius:999px; padding:.15rem .7rem; font-size:.78rem; margin-top:.3rem;
  background:var(--brand-soft); color:var(--info-fg); font-weight:700; }
.menu-t { font-size:.7rem; letter-spacing:.14em; color:#9CA3AF; font-weight:700; margin:.6rem 0 .5rem .5rem; }
[data-testid="stSidebar"] div[role="radiogroup"] { gap:4px; }
[data-testid="stSidebar"] div[role="radiogroup"] > label { padding:.7rem .95rem; border-radius:var(--radius-sm); width:100%;
  cursor:pointer; transition:background .15s ease, transform .15s ease; border:1px solid transparent; }
[data-testid="stSidebar"] div[role="radiogroup"] > label p { font-size:.95rem; margin:0; font-weight:500; color:var(--ink-2); }
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background:var(--brand-soft); transform:translateX(2px); }
[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display:none; }
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
  background:var(--grad); box-shadow:0 8px 18px -6px rgba(79,70,229,.55); }
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) * { color:#fff !important; font-weight:600; }
.pie-lateral { font-size:.72rem; color:#9CA3AF; margin-top:.8rem; text-align:center; line-height:1.5; }

/* ================= HERO ================= */
.st-key-hero { position:relative; overflow:hidden; background:var(--grad); border-radius:20px;
  padding:1.9rem 2.1rem 1.6rem; box-shadow:0 16px 36px -12px rgba(79,70,229,.45); }
.st-key-hero::before { content:""; position:absolute; right:-80px; top:-80px; width:300px; height:300px; border-radius:50%;
  background:radial-gradient(circle,rgba(255,255,255,.22),rgba(255,255,255,0) 70%); pointer-events:none; }
.st-key-hero::after { content:""; position:absolute; left:35%; bottom:-120px; width:280px; height:280px; border-radius:50%;
  background:radial-gradient(circle,rgba(255,255,255,.12),rgba(255,255,255,0) 70%); pointer-events:none; }
.hero-t { font-size:1.9rem; font-weight:800; color:#fff; letter-spacing:-.02em; }
.hero-s { color:#fff; opacity:.92; max-width:720px; margin:.35rem 0 .8rem; line-height:1.55; font-size:.98rem; }
.st-key-hero .chip { background:rgba(255,255,255,.2); color:#fff; backdrop-filter:blur(4px); }
.st-key-hero button { background:#fff !important; border:0 !important; border-radius:var(--radius-sm); font-weight:700;
  box-shadow:0 6px 16px -6px rgba(0,0,0,.25); }
.st-key-hero button p, .st-key-hero button div { color:var(--brand-1) !important; }
.st-key-hero button:hover { transform:translateY(-2px); filter:none; }

/* ================= KPI CARDS ================= */
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:1rem; margin:1.1rem 0 .4rem; }
.kpi { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:1rem 1.1rem;
  box-shadow:var(--shadow); transition:transform .2s ease, box-shadow .2s ease; }
.kpi:hover { transform:translateY(-3px); box-shadow:var(--shadow-hover); }
.kpi-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:.5rem; }
.kpi-ico { width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  font-size:1.15rem; background:var(--brand-soft); }
.kpi-v { font-size:1.75rem; font-weight:800; color:var(--ink); line-height:1.1; letter-spacing:-.02em; }
.kpi-l { font-size:.8rem; color:var(--muted); font-weight:600; margin-top:.15rem; }
.kpi-b { font-size:.68rem; font-weight:700; padding:.12rem .5rem; border-radius:999px; }
.kpi-b.ok { background:var(--ok-bg); color:var(--ok-fg); }
.kpi-b.info { background:var(--info-bg); color:var(--info-fg); }
.kpi-b.warn { background:var(--warn-bg); color:var(--warn-fg); }

/* ================= TARJETAS ================= */
[class*="st-key-card_"], [class*="st-key-curso_"], .st-key-continuar, .st-key-form_crear {
  padding:1.25rem 1.35rem !important; border-radius:var(--radius) !important; background:var(--surface);
  border:1px solid var(--border) !important; box-shadow:var(--shadow);
  transition:box-shadow .2s ease, transform .2s ease, border-color .2s ease; }
[class*="st-key-card_"]:hover, [class*="st-key-curso_"]:hover {
  box-shadow:var(--shadow-hover); transform:translateY(-3px); border-color:#C7D2FE !important; }
.st-key-continuar { background:linear-gradient(180deg,#FFFFFF,#FAFAFF); }
.tool-i { width:46px; height:46px; border-radius:13px; display:flex; align-items:center; justify-content:center;
  font-size:1.5rem; line-height:1; margin-bottom:.35rem; background:var(--brand-soft); }
.tool-t { font-weight:700; font-size:1.02rem; margin-top:.4rem; color:var(--ink); }
.tool-d { color:var(--muted); font-size:.85rem; min-height:2.6rem; margin:.2rem 0 .7rem; line-height:1.45; }
.curso-t { font-weight:700; font-size:1.05rem; color:var(--ink); line-height:1.3; }
.curso-s { color:var(--muted); font-size:.84rem; margin:.2rem 0 .55rem; }
.curso-p { font-size:.85rem; color:var(--ink-2); margin:.2rem 0 .8rem; }
.pills { display:flex; flex-wrap:wrap; gap:.4rem; margin:.2rem 0 .9rem; }
.pill { display:inline-flex; align-items:center; gap:.3rem; font-size:.74rem; font-weight:700; padding:.22rem .65rem;
  border-radius:999px; background:#F3F4F6; color:var(--ink-2); white-space:nowrap; }
.pill.ok { background:var(--ok-bg); color:var(--ok-fg); }
.pill.warn { background:var(--warn-bg); color:var(--warn-fg); }
.pill.info { background:var(--info-bg); color:var(--info-fg); }
.pill.active { background:var(--grad); color:#fff; }

/* tarjetas de curso: botones siempre completos y alineados (no se cortan ni se apilan) */
[class*="st-key-curso_"] { overflow:visible; min-width:0; }
[class*="st-key-curso_"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:.5rem; }
[class*="st-key-curso_"] [data-testid="stColumn"] { min-width:0 !important; }
[class*="st-key-curso_"] button { padding-left:.5rem; padding-right:.5rem; white-space:nowrap; }


/* ================= PASOS (guía para el docente) ================= */
.steps { display:flex; gap:.6rem; margin:.4rem 0 1.1rem; flex-wrap:wrap; }
.step { display:flex; align-items:center; gap:.55rem; background:var(--surface); border:1px solid var(--border);
  border-radius:999px; padding:.4rem .95rem .4rem .45rem; font-size:.86rem; font-weight:600; color:var(--muted); }
.step-n { width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background:#F3F4F6; color:var(--muted); font-size:.8rem; font-weight:800; }
.step.on { color:var(--brand-1); border-color:#C7D2FE; background:var(--brand-soft); }
.step.on .step-n { background:var(--grad); color:#fff; }
.step.done { color:var(--ok-fg); border-color:#A7F3D0; background:var(--ok-bg); }
.step.done .step-n { background:#10B981; color:#fff; }
.opc { font-size:.78rem; font-weight:500; color:var(--muted); }
h5 { margin-top:.4rem; }

/* ================= RESPONSIVE ================= */
@media (max-width:768px) {
  .main .block-container { padding-left:1rem; padding-right:1rem; }
  .hero-t { font-size:1.4rem; } .st-key-hero { padding:1.4rem 1.2rem 1.2rem; }
  h1 { font-size:1.6rem; } .kpi-v { font-size:1.45rem; }
}
@media (prefers-reduced-motion:reduce) { * { transition:none !important; animation:none !important; } }
</style>
"""


def inyectar_tema():
    st.markdown(CSS, unsafe_allow_html=True)
