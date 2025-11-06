import streamlit as st
import pandas as pd
import requests

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="SERP Video Visibility", page_icon="🎥", layout="wide")

st.title("🎥 SERP Video Visibility Analyzer")
st.write("Analizza la presenza di **YouTube**, **TikTok** e **Instagram** nelle SERP di Google.")

# --- INPUT UTENTE ---
st.subheader("🔑 Impostazioni API e Parametri")
serper_api_key = st.text_input("Inserisci la tua API Key di Serper.dev", type="password")
google_domain = st.selectbox("Seleziona il dominio Google", ["google.it", "google.com", "google.es", "google.fr"])
keywords_input = st.text_area("Inserisci una lista di keyword (una per riga)")

# --- ANALISI SERP ---
if st.button("Avvia Analisi"):
    if not serper_api_key or not keywords_input:
        st.warning("⚠️ Inserisci la tua API key e almeno una keyword.")
    else:
        keywords = [kw.strip() for kw in keywords_input.split("\n") if kw.strip()]
        results_data = []

        for kw in keywords:
            st.write(f"🔍 Analizzo: **{kw}** ...")
            url = "https://google.serper.dev/search"
            payload = {"q": kw, "gl": google_domain.split(".")[-1]}
            headers = {"X-API-KEY": serper_api_key, "Content-Type": "application/json"}

            try:
                r = requests.post(url, json=payload, headers=headers)
                data = r.json()
            except Exception as e:
                st.error(f"Errore con la keyword {kw}: {e}")
                continue

            # --- Estrazione organici ---
            organic = data.get("organic", [])

            def contains(domain):
                return any(domain in res.get("link", "") for res in organic)

            youtube = contains("youtube.com")
            tiktok = contains("tiktok.com")
            instagram = contains("instagram.com")

            # --- Estrazione avanzata box video ---
            videos = []
            possible_video_keys = ["videos", "inlineVideos", "video_results", "top_videos", "shortVideos"]

            for key in possible_video_keys:
                if key in data and isinstance(data[key], list):
                    videos.extend(data[key])

            has_video_box = len(videos) > 0

            # Verifica se ci sono video da YouTube / TikTok / Instagram
            youtube_present = any("youtube.com" in v.get("link", "").lower() for v in videos)
            tiktok_present = any("tiktok.com" in v.get("link", "").lower() for v in videos)
            instagram_present = any("instagram.com" in v.get("link", "").lower() for v in videos)

            # --- Costruzione risultati ---
            video_sources = set()
            for v in videos:
                link = v.get("link", "")
                if "youtube.com" in link:
                    video_sources.add("YouTube")
                elif "tiktok.com" in link:
                    video_sources.add("TikTok")
                elif "instagram.com" in link:
                    video_sources.add("Instagram")

            results_data.append({
                "Keyword": kw,
                "YouTube (Top 10)": "✅" if youtube else "❌",
                "TikTok (Top 10)": "✅" if tiktok else "❌",
                "Instagram (Top 10)": "✅" if instagram else "❌",
                "Box Video Presente": "✅" if has_video_box else "❌",
                "Video YouTube": "✅" if youtube_present else "❌",
                "Video TikTok": "✅" if tiktok_present else "❌",
                "Video Instagram": "✅" if instagram_present else "❌",
                "Sorgenti Box Video": ", ".join(video_sources) if video_sources else "-"
            })

        # --- RISULTATI ---
        df = pd.DataFrame(results_data)
        st.subheader("📊 Risultati Analisi")
        st.dataframe(df, use_container_width
