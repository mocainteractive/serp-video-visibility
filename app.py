import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ============== CONFIG ==============
st.set_page_config(page_title="SERP Video Visibility", page_icon="🎥", layout="wide")

st.title("🎥 SERP Video Visibility Analyzer")
st.write("Verifica se **YouTube**, **TikTok** o **Instagram** compaiono nella SERP (in qualunque sezione) "
         "e se sono presenti nella **Top 10 organica**. Include diagnostica per capire dove vengono trovati.")

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
    relaxed = st.checkbox("Usa match 'rilassato' (matcha anche la parola 'tiktok'/'youtube'/'instagram')", value=True)
    debug = st.checkbox("Mostra JSON di debug (prima keyword)", value=False)

keywords_input = st.text_area(
    "📥 Inserisci una lista di keyword (una per riga)",
    height=180,
    placeholder="es.\naspirapolvere\nlavare tappezzeria auto\nmacchina caffè cialde"
)
st.caption("Suggerimento: per risultati coerenti con google.it, usa **gl=it** e **hl=it**.")

# ============== HELPERS ==============
SOCIAL = {
    "YouTube": {
        "domains": ["youtube.com", "youtu.be", "m.youtube.com"],
        "sources": ["youtube"],
        "relaxed": ["youtube"]  # parole chiave per match rilassato
    },
    "TikTok": {
        "domains": [
            "tiktok.com", "vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com",
            "tiktokv.com", "tiktokcdn.com"  # spesso in thumbnail/CDN
        ],
        "sources": ["tiktok"],
        "relaxed": ["tiktok"]  # parole chiave per match rilassato
    },
    "Instagram": {
        "domains": ["instagram.com", "m.instagram.com"],
        "sources": ["instagram"],
        "relaxed": ["instagram", "ig "]  # 'ig ' per evitare falsi positivi
    },
}

def _to_str(s):
    return s if isinstance(s, str) else ""

def walk_collect_strings_with_paths(obj, path="", acc=None):
    """
    Raccoglie tutte le stringhe presenti nel JSON *con il path* del campo.
    Ritorna lista di tuple: (string_lower, path_string).
    """
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            if isinstance(v, str):
                acc.append((v.lower(), new_path))
            elif isinstance(v, (dict, list)):
                walk_collect_strings_with_paths(v, new_path, acc)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]" if path else f"[{i}]"
            if isinstance(item, str):
                acc.append((item.lower(), new_path))
            else:
                walk_collect_strings_with_paths(item, new_path, acc)
    return acc

def detect_domains_anywhere(strings_with_paths, relaxed_mode=False, max_hits_per_label=5):
    """
    Presenza domini/social ovunque nella SERP.
    - strict: match su domini noti (tiktok.com, etc.) o 'source' noti (tiktok, youtube...)
    - relaxed: se strict fallisce, matcha anche parole chiave ('tiktok', 'youtube', 'instagram') ovunque.
    Restituisce:
      presence: {label: bool}
      hits: {label: [(snippet, path), ...]}  # esempi di match
    """
    presence = {k: False for k in SOCIAL.keys()}
    hits = {k: [] for k in SOCIAL.keys()}

    # pass 1: strict (domains + sources)
    for label, cfg in SOCIAL.items():
        doms = cfg["domains"]
        srcs = cfg["sources"]

        for s, p in strings_with_paths:
            if presence[label] and len(hits[label]) >= max_hits_per_label:
                continue
            if any(dom in s for dom in doms) or any(src in s for src in srcs):
                presence[label] = True
                # salva snippet (accorciato) + path
                snippet = s[:140] + ("…" if len(s) > 140 else "")
                hits[label].append((snippet, p))

    # pass 2: relaxed (keyword 'tiktok' ecc.) solo se non trovato in strict
    if relaxed_mode:
        for label, cfg in SOCIAL.items():
            if presence[label]:
                continue
            for s, p in strings_with_paths:
                if presence[label] and len(hits[label]) >= max_hits_per_label:
                    continue
                if any(tok in s for tok in cfg.get("relaxed", [])):
                    presence[label] = True
                    snippet = s[:140] + ("…" if len(s) > 140 else "")
                    hits[label].append((snippet, p))

    return presence, hits

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
            st.subheader("🧪 Debug (prima keyword) – payload Serper")
            st.json(data)
            first_json_shown = True

        # Presenza ovunque (con diagnosi)
        strings_with_paths = walk_collect_strings_with_paths(data)
        presence_any, hits = detect_domains_anywhere(strings_with_paths, relaxed_mode=relaxed, max_hits_per_label=5)

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

        # Pannello diagnostico snello per ogni keyword (se ci sono hit)
        with st.expander(f"🧭 Diagnostica match - {kw}", expanded=False):
            for label in ["YouTube", "TikTok", "Instagram"]:
                if hits[label]:
                    st.markdown(f"**{label}**: trovati {len(hits[label])} hit (mostro fino a 5)")
                    for snippet, p in hits[label]:
                        st.code(f"[{label}] {snippet}\npath: {p}")
                else:
                    st.markdown(f"**{label}**: nessun hit")

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
