import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ============== CONFIG ==============
st.set_page_config(page_title="SERP Video Visibility", page_icon="🎥", layout="wide")

st.title("🎥 SERP Video Visibility Analyzer")
st.write("Verifica se **YouTube**, **TikTok** o **Instagram** compaiono nella SERP (in qualunque sezione) "
         "e se sono presenti nella **Top 10 organica**.")

# ============== UI PARAMS ==============
with st.expander("🔧 Impostazioni"):
    col1, col2, col3 = st.columns(3)
    with col1:
        serper_api_key = st.text_input("API Key Serper.dev", type="password")
    with col2:
        google_domain = st.selectbox(
            "Dominio Google",
            ["google.it", "google.com", "google.es", "google.fr", "google.de"],
            index=0
        )
    with col3:
        hl = st.selectbox("Lingua (hl)", ["it", "en", "es", "fr", "de"], index=0)
    gl = st.selectbox("Paese (gl)", ["it", "us", "es", "fr", "de"], index=0)
    num_results = st.slider("Quanti risultati organici prelevare", 10, 50, 20, 10)
    debug = st.checkbox("Mostra JSON di debug (prima keyword)")

keywords_input = st.text_area(
    "📥 Inserisci una lista di keyword (una per riga)",
    height=180,
    placeholder="es.\naspirapolvere\nlavare tappezzeria auto\nmacchina caffè cialde"
)
st.caption("Suggerimento: per risultati coerenti con google.it, usa **gl=it** e **hl=it**.")

# ============== HELPERS ==============
SOCIAL = {
    "YouTube": {
        "domains": ["youtube.com", "youtu.be"],
        "sources": ["youtube"]
    },
    "TikTok": {
        "domains": ["tiktok.com", "vm.tiktok.com"],
        "sources": ["tiktok"]
    },
    "Instagram": {
        "domains": ["instagram.com"],
        "sources": ["instagram"]
    },
}

def _to_str(s):
    return s if isinstance(s, str) else ""

def walk_collect_strings(obj, acc=None):
    """
    Raccoglie *tutte* le stringhe presenti nel JSON (valori; non solo 'link').
    Restituisce una lista di stringhe lower-case.
    """
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        for _, v in obj.items():
            if isinstance(v, str):
                acc.append(v.lower())
            elif isinstance(v, (dict, list)):
                walk_collect_strings(v, acc)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                acc.append(item.lower())
            else:
                walk_collect_strings(item, acc)
    return acc

def detect_domains_anywhere_from_strings(strings_lower):
    """
    Presenza domini/social *ovunque* nella SERP.
    Match su domini (es. 'tiktok.com') o su sorgenti (es. source='tiktok').
    """
    presence = {k: False for k in SOCIAL.keys()}
    for label, cfg in SOCIAL.items():
        # Match domini
        if any(dom in s for dom in cfg["domains"] for s in strings_lower):
            presence[label] = True
            continue
        # Match 'source'
        if any(src in s for src in cfg["sources"] for s in strings_lower):
            presence[label] = True
    return presence

def detect_domains_top10(organic):
    """
    Presenza domini nella Top 10 organica + prima posizione (1-based).
    """
    presence = {k: False for k in SOCIAL.keys()}
    first_pos = {k: None for k in SOCIAL.keys()}

    top10 = (organic or [])[:10]
    for idx, res in enumerate(top10, start=1):
        link = _to_str(res.get("link", "")).lower()
        displayed = _to_str(res.get("displayedLink", "")).lower()
        for label, cfg in SOCIAL.items():
            if any(dom in link for dom in cfg["domains"]) or any(dom in displayed for dom in cfg["domains"]):
                presence[label] = True
                if first_pos[label] is None:
                    first_pos[label] = idx
    return presence, first_pos

# ============== MAIN ==============
if st.button("🚀 Avvia Analisi"):
    if not serper_api_key or not keywords_input.strip():
        st.warning("⚠️ Inserisci la tua API key e almeno una keyword.")
        st.stop()

    headers = {"X-API-KEY": serper_api_key, "Content-Type": "application/json"}
    url = "https://google.serper.dev/search"

    keywords = [kw.strip() for kw in keywords_input.split("\n") if kw.strip()]
    rows = []
    first_json_shown = False

    for kw in keywords:
        st.write(f"🔍 **{kw}**")
        payload = {
            "q": kw,
            "gl": gl,
            "hl": hl,
            "google_domain": google_domain,
            "num": int(num_results)
        }

        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            st.error(f"Errore con '{kw}': {e}")
            continue

        # Debug solo per la prima keyword
        if debug and not first_json_shown:
            st.subheader("🧪 Debug (prima keyword)")
            st.json(data)
            first_json_shown = True

        # Presenza ovunque (string-scan dell'intero JSON)
        strings_lower = walk_collect_strings(data)
        presence_any = detect_domains_anywhere_from_strings(strings_lower)

        # Presenza Top 10 organica
        organic = data.get("organic", [])
        presence_top10, first_pos = detect_domains_top10(organic)

        rows.append({
            "Keyword": kw,
            # Ovunque
            "YouTube (ovunque)": "✅" if presence_any["YouTube"] else "❌",
            "TikTok (ovunque)": "✅" if presence_any["TikTok"] else "❌",
            "Instagram (ovunque)": "✅" if presence_any["Instagram"] else "❌",
            # Top 10 organica
            "YouTube (Top 10)": "✅" if presence_top10["YouTube"] else "❌",
            "TikTok (Top 10)": "✅" if presence_top10["TikTok"] else "❌",
            "Instagram (Top 10)": "✅" if presence_top10["Instagram"] else "❌",
            # Prima posizione se presente
            "Pos YouTube (Top 10)": first_pos["YouTube"] if first_pos["YouTube"] else "-",
            "Pos TikTok (Top 10)": first_pos["TikTok"] if first_pos["TikTok"] else "-",
            "Pos Instagram (Top 10)": first_pos["Instagram"] if first_pos["Instagram"] else "-",
        })

    if rows:
        df = pd.DataFrame(rows)
        st.subheader("📊 Risultati")
        st.dataframe(df, use_container_width=True)

        # ---- Export CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Scarica CSV", data=csv,
                           file_name="serp_social_presence.csv", mime="text/csv")

        # ---- Export Excel
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Risultati")
        st.download_button("📗 Scarica Excel", data=bio.getvalue(),
                           file_name="serp_social_presence.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Nessun risultato disponibile.")
