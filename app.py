import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.set_page_config(page_title="SERP Video Visibility", page_icon="🎥", layout="wide")

st.title("🎥 SERP Video Visibility Analyzer")
st.write("Analizza la presenza di **YouTube**, **TikTok** e **Instagram** nelle SERP di Google.")

# ---------------- UI: Parametri ----------------
with st.expander("🔧 Impostazioni"):
    col1, col2, col3 = st.columns(3)
    with col1:
        serper_api_key = st.text_input("API Key Serper.dev", type="password")
    with col2:
        google_domain = st.selectbox("Dominio Google", ["google.it", "google.com", "google.es", "google.fr", "google.de"])
    with col3:
        # lingua (hl) e paese (gl)
        hl = st.selectbox("Lingua (hl)", ["it", "en", "es", "fr", "de"])
    gl = st.selectbox("Paese (gl)", ["it", "us", "es", "fr", "de"])
    debug = st.checkbox("Mostra JSON di debug (prima keyword)")

keywords_input = st.text_area("📥 Inserisci una lista di keyword (una per riga)", height=180,
                              placeholder="es.\naspirapolvere\naspirapolvere senza fili\nmacchina caffè cialde")

st.caption("Suggerimento: per risultati coerenti con google.it, usa **gl=it** e **hl=it**.")

def detect_social_in_top10(organic_results, domain_substring):
    # Limita alla Top 10
    top10 = (organic_results or [])[:10]
    for res in top10:
        link = res.get("link", "") or ""
        displayed_link = res.get("displayedLink", "") or ""
        if domain_substring in link or domain_substring in displayed_link:
            return True
    return False

def collect_video_sources(*video_lists):
    """Ritorna (box_presente, sorgenti_set) aggregando liste video di strutture diverse."""
    all_items = []
    for lst in video_lists:
        if isinstance(lst, list):
            all_items.extend(lst)

    sources = set()
    for item in all_items:
        link = item.get("link", "") or ""
        source = (item.get("source") or item.get("displayedLink") or "").lower()

        def add_if(cond, label):
            if cond:
                sources.add(label)

        add_if("youtube.com" in link or "youtube" in source, "YouTube")
        add_if("tiktok.com" in link or "tiktok" in source, "TikTok")
        add_if("instagram.com" in link or "instagram" in source, "Instagram")

    return (len(all_items) > 0), sources

# ---------------- Analisi ----------------
if st.button("🚀 Avvia Analisi"):
    if not serper_api_key or not keywords_input.strip():
        st.warning("⚠️ Inserisci la tua API key e almeno una keyword.")
        st.stop()

    headers = {"X-API-KEY": serper_api_key, "Content-Type": "application/json"}
    url = "https://google.serper.dev/search"

    keywords = [kw.strip() for kw in keywords_input.split("\n") if kw.strip()]
    results = []

    first_json_shown = False

    for kw in keywords:
        st.write(f"🔍 **{kw}**")
        payload = {
            "q": kw,
            "gl": gl,              # paese
            "hl": hl,              # lingua
            "google_domain": google_domain,
            "num": 20              # prendiamo un po' più di risultati, ma filtriamo top10 dopo
        }

        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            st.error(f"Errore con '{kw}': {e}")
            continue

        # Debug JSON solo per la prima keyword
        if debug and not first_json_shown:
            st.subheader("🧪 Debug (prima keyword)")
            st.json(data)
            first_json_shown = True

        organic = data.get("organic", [])

        # Varianti possibili dei box video
        videos_box       = data.get("videos", [])           # video carousel classico
        short_videos_box = data.get("shortVideos", [])      # box "Video brevi"
        inline_videos    = data.get("inlineVideos", [])     # alcune SERP lo usano così

        # Social nelle top 10 organiche
        yt  = detect_social_in_top10(organic, "youtube.com")
        tt  = detect_social_in_top10(organic, "tiktok.com")
        ig  = detect_social_in_top10(organic, "instagram.com")

        # Presenza box + sorgenti
        any_box, sources = collect_video_sources(videos_box, short_videos_box, inline_videos)

        row = {
            "Keyword": kw,
            "YouTube (Top 10)": "✅" if yt else "❌",
            "TikTok (Top 10)": "✅" if tt else "❌",
            "Instagram (Top 10)": "✅" if ig else "❌",
            "Box Video": "✅" if len(videos_box) > 0 else "❌",
            "Box Video Brevi": "✅" if len(short_videos_box) > 0 else "❌",
            "Box (qualsiasi tipo)": "✅" if any_box else "❌",
            "Sorgenti Box": ", ".join(sorted(sources)) if sources else "-"
        }
        results.append(row)

    if results:
        df = pd.DataFrame(results)
        st.subheader("📊 Risultati Analisi")
        st.dataframe(df, use_container_width=True)

        # --- Esportazione CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Scarica CSV", data=csv,
                           file_name="serp_video_visibility.csv", mime="text/csv")

        # --- Esportazione Excel
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Risultati")
        st.download_button("📗 Scarica Excel", data=bio.getvalue(),
                           file_name="serp_video_visibility.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Nessun risultato disponibile.")
