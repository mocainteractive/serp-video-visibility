# 🎥 SERP Video Visibility Analyzer

Questa app **Streamlit** analizza la presenza di video e social media (YouTube, TikTok, Instagram) nelle **SERP di Google**, 
utilizzando l’API di [Serper.dev](https://serper.dev).

## ⚙️ Funzionalità
- Analisi di una lista di keyword
- Rilevazione di risultati organici provenienti da YouTube, TikTok, Instagram
- Identificazione della presenza del box “Video” e “Video brevi”
- Verifica delle fonti video presenti nel box
- Esportazione risultati in formato CSV

## 🧠 Input richiesti
- API Key di Serper.dev
- Dominio Google (es. `google.it`, `google.com`)
- Lista di keyword

## 📦 Requisiti
Librerie principali (già elencate in `requirements.txt`):
streamlit
pandas
requests
openpyxl

## 🚀 Avvio in locale
1. Clona il repository:
   ```bash
   git clone https://github.com/mocainteractive/serp-video-visibility.git
pip install -r requirements.txt
streamlit run app.py
