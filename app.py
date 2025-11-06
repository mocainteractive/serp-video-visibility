import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.set_page_config(page_title="SERP Video Visibility", page_icon="🎥", layout="wide")

st.title("🎥 SERP Video Visibility Analyzer")
st.write("Verifica se **YouTube**, **TikTok** o **Instagram** compaiono nella SERP (organico o qualsiasi box).")

# ---------------- UI: Parametri ----------------
with st.expander("🔧 Impostazioni"):
    col1, col2, col3 = st.columns(3)
    with col1:
        serper_api_key = st.text_input("API Key Serper.dev", type="password")
    with col2:
        google_domain = st.selectbox("Dominio Google", ["google.it", "google.com", "google.es", "google.fr", "google.de"])
    with col3:
        hl = st.selectbox("Lingua (hl)", ["it", "en", "es", "fr", "de"])
    gl = st.selectbox("Paese (gl)", ["it", "us", "es", "fr", "de"])
    num_results = st.slider("Quanti risultati organici prelevare (per sicurezza)", min_value=10, max_value=50, value=20, step=10)
    debug = st.checkbox("Mostra JSON di debug (prima keyword)")

keywords_input = st.text_area(
    "📥 Inserisci una lista di keyword (una per riga)",
    height=180,
    placeholder="es.\naspirapolvere\naspirapolvere senza fili\nmacchina caffè cialde"
)
st.caption("Suggerimento: per risultati coerenti con google.it, usa **gl=it** e **hl=it**.")

# ---------------- Utilità ----------------
SOCIAL_DOMAINS = {
    "YouTube": "youtube.com",
    "TikTok": "tiktok.com",
    "Instagram": "instagram.com",
}

def in_str(s):
    return s if isinstance(s, str) else ""

def walk_collect_links(obj, path="", acc=None):
    """
    Traversing generico del JSON SERP.
    Raccoglie tutte le URL (campi 'link') e la 'displayedLink' dove presente,
    insieme al path (per eventuali debug/analisi).
    """
    if acc is None:
        acc = []

    if isinstance(obj, dict):
        # Se c'è un 'link', raccoglilo
        if "link" in obj and isinstance(obj["link"], str):
            acc.append((obj["link"], path or "root"))
        # Alcune sezioni usano displayedLink come stringa utile al matching dominio
        if "displayedLink" in obj and isinstance(obj["displayedLink"], str):
            acc.append((obj["displayedLink"], (path or "root") + ".displayedLink"))

        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            walk_collect_links(v, new_path, acc)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            walk_collect_links(item, f"{path}[{i}]" if path else f"[{i}]", acc)

    return acc

def detect_domains_anywhere(all_links):
    """
    Controlla se ciascun dominio dei SOCIAL_DOMAINS compare in almeno un link raccolto.
    """
    presence = {k: False for k in SOCIAL_DOMAINS.keys()}
    for url, _path in all_links:
        url_l = url.lower()
        for label, dom in SOCIAL_DOMAINS.items():
            if dom in url_l:
                presence[label] = True
    return presence

def detect_domains_top10(organic):
    """
    Controlla presenza domini nella Top 10 organica.
    Ritorna: dict presenza, e dizionario con prime posizioni (1-based) se presenti.
    """
    presence = {k: False for k in SOCIAL_DOMAINS.keys()}
    first_pos = {k: None for k in SOCIAL_DOMAINS.keys()}

    top10 = (organic or [])[:10]
    for idx, res in enumerate(top10, start=1):
        link = in_str(res.get("link", "")).lower()
        displayed = in_str(res.get("displayedLink", "")).lower()

        for label, dom in SOCIAL_DOMAINS.items():
            if (dom in link) or (dom in displayed):
                presence[label] = True
                if first_pos[label] is None:
                    first_pos[label] = idx

    return presence, first_pos

# ---------------- Analisi ----------------
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
            "num": int(num_results)  # fetcha più risultati organici, ma Top10 resta Top10
        }

        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            st.error(f"Errore con '{kw}': {e}")
            continue

        if debug and not first_json_shown:
            st.subheader("🧪 Debug (prima keyword)")
            st.json(data)
            first_json_shown = True

        organic = data.get("organic", [])

        # 1) Presenza ovunque (scansione completa del JSON)
        all_links = walk_collect_links(data)
        presence_any = detect_domains_anywhere(all_links)

        # 2) Presenza nella Top 10 organica
        presence_top10, first_pos = detect_domains_top10(organic)

        rows.append({
            "Keyword": kw,
            # Ovunque in SERP
            "YouTube (Ovunque)": "✅" if presence_any["YouTube"] else "❌",
            "TikTok (Ovunque)": "✅" if presence_any["TikTok"] else "❌",
            "Instagram (Ovunque)": "✅" if presence_any["Instagram"] else "❌",
            # Top 10 organico
            "YouTube (Top 10)": "✅" if presence_top10["YouTube"] else "❌",
            "TikTok (Top 10)": "✅" if presence_top10["TikTok"] else "❌",
            "Instagram (Top 10)": "✅" if presence_top10["Instagram"] else "❌",
            # Prima posizione organica se presente
            "Pos YouTube (Top 10)": first_pos["YouTube"] if first_pos["YouTube"] else "-",
            "Pos TikTok (Top 10)": first_pos["TikTok"] if first_pos["TikTok"] else "-",
            "Pos Instagram (Top 10)": first_pos["Instagram"] if first_pos["Instagram"] else "-",
        })

    if rows:
        df = pd.DataFrame(rows)
        st.subheader("📊 Risultati")
        st.dataframe(df, use_container_width=True)

        # --- Export CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Scarica CSV", data=csv,
                           file_name="serp_social_presence.csv", mime="text/csv")

        # --- Export Excel
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Risultati")
        st.download_button("📗 Scarica Excel", data=bio.getvalue(),
                           file_name="serp_social_presence.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Nessun risultato disponibile.")
