import streamlit as st
import pandas as pd
import requests

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="SERP Video Visibility", page_icon="🎥", layout="wide")

st.title("🎥 SERP Video Visibility Analyzer")
st.write("Analizza la presenza di **YouTube**, **TikTok** e **Instagram** nelle SERP di Google (in qualsiasi formato: organico o box video).")

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

            # --- Unisci tutte le sezioni della SERP per la ricerca dei domini ---
            all_sections = []
            possible_sections = [
                "organic", "videos", "inlineVideos", "shortVideos", "video_results",
                "top_videos", "inline_videos", "videoResults"
            ]

            for key in possible_sections:
                if key in data and isinstance(data[key], list):
                    all_sections.extend(data[key])

            # Aggiungi anche eventuali risultati video dentro "organic"
            for item in data.get("organic", []):
                if isinstance(item, dict) and item.get("type") == "video":
                    all_sections.append(item)

            # --- Controlla la presenza dei domini ---
            youtube = any("youtube.com" in str(item).lower() for item in all_sections)
            tiktok = any("tiktok.com" in str(item).lower() for item in all_sections)
            instagram = any("instagram.com" in str(item).lower() for item in all_sections)

            results_data.append({
                "Keyword": kw,
                "YouTube Presente": "✅" if youtube else "❌",
                "TikTok Presente": "✅" if tiktok else "❌",
                "Instagram Presente": "✅" if instagram else "❌",
            })

        # --- RISULTATI ---
        df = pd.DataFrame(results_data)
        st.subheader("📊 Risultati Analisi")
        st.dataframe(df, use_container_width=True)

        # --- ESPORTAZIONE ---
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "💾 Scarica CSV",
            data=csv,
            file_name="serp_video_visibility.csv",
            mime="text/csv"
        )
