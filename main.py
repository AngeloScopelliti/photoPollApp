import streamlit as st
from supabase import create_client
import datetime
import requests
from st_clickable_images import clickable_images # Libreria per il tocco sulla foto

# ==========================================
# 1. INIZIALIZZAZIONE
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "nome_utente" not in st.session_state:
    st.session_state.nome_utente = ""
if 'foto_selezionata' not in st.session_state:
    st.session_state.foto_selezionata = None
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0
if 'ordinamento' not in st.session_state:
    st.session_state.ordinamento = "Più recenti"

# ==========================================
# 2. LOGIN (NOME + PASSWORD)
# ==========================================
def login():
    if not st.session_state.autenticato:
        st.title("📸 Galleria Privata")
        nome = st.text_input("Come ti chiami?", placeholder="Tuo nome...")
        pwd = st.text_input("Password di accesso", type="password")
        if st.button("Entra"):
            if pwd == st.secrets["PASSWORD_ACCESSO"] and nome.strip() != "":
                st.session_state.autenticato = True
                st.session_state.nome_utente = nome.strip()
                st.rerun()
            else:
                st.error("Dati errati o nome mancante!")
        return False
    return True

if not login():
    st.stop()

# ==========================================
# 3. CONNESSIONE A SUPABASE
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ==========================================
# 4. VISTA DETTAGLIO (FULLSCREEN)
# ==========================================
if st.session_state.foto_selezionata:
    f_info = st.session_state.foto_selezionata
    f_name = f_info['name']
    
    if st.button("⬅️ Torna alla Galleria"):
        st.session_state.foto_selezionata = None
        st.rerun()

    img_url = supabase.storage.from_("PhotoPollApp").get_public_url(f_name)
    col_img, col_info = st.columns([2, 1])
    
    with col_img:
        st.image(img_url, use_container_width=True)
    
    with col_info:
        # Recupera dati foto (Voti e Autore)
        res_db = supabase.table("voti_foto").select("conteggio_voti, autore").eq("file_name", f_name).single().execute()
        voti_totali = res_db.data['conteggio_voti'] if res_db.data else 0
        autore = res_db.data['autore'] if res_db.data else "Sconosciuto"
        
        # Controllo Voto Unico
        res_voto_utente = supabase.table("voti_per_utente").select("*").eq("file_name", f_name).eq("nome_utente", st.session_state.nome_utente).execute()
        ha_votato = len(res_voto_utente.data) > 0

        st.subheader(f"Caricata da {autore}")
        st.metric("Punteggio", f"⭐ {voti_totali}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            label_voto = "❤️ Votato" if ha_votato else "👍 Vota"
            if st.button(label_voto, use_container_width=True, type="secondary" if ha_votato else "primary"):
                if not ha_votato:
                    supabase.table("voti_per_utente").insert({"file_name": f_name, "nome_utente": st.session_state.nome_utente}).execute()
                    supabase.table("voti_foto").update({"conteggio_voti": voti_totali + 1}).eq("file_name", f_name).execute()
                else:
                    supabase.table("voti_per_utente").delete().eq("file_name", f_name).eq("nome_utente", st.session_state.nome_utente).execute()
                    supabase.table("voti_foto").update({"conteggio_voti": max(0, voti_totali - 1)}).eq("file_name", f_name).execute()
                st.rerun()
        
        with c2:
            try:
                img_data = requests.get(img_url).content
                st.download_button("💾", data=img_data, file_name=f_name, mime="image/jpeg", use_container_width=True)
            except: pass
            
        with c3:
            with st.popover("🗑️", use_container_width=True):
                if st.button("Elimina", key="del_det", type="primary"):
                    supabase.storage.from_("PhotoPollApp").remove([f_name])
                    supabase.table("voti_foto").delete().eq("file_name", f_name).execute()
                    st.session_state.foto_selezionata = None
                    st.rerun()

        st.divider()
        st.subheader("💬 Commenti")
        nuovo_comm = st.text_input("Aggiungi un commento...", key="in_comm")
        if st.button("Invia"):
            if nuovo_comm:
                supabase.table("commenti_foto").insert({"file_name": f_name, "testo": nuovo_comm, "autore": st.session_state.nome_utente}).execute()
                st.rerun()
        
        comm_db = supabase.table("commenti_foto").select("*").eq("file_name", f_name).order("creato_at", desc=True).execute()
        for c in comm_db.data:
            st.caption(f"🕒 {c['creato_at'][11:16]} - **{c.get('autore', 'Anonimo')}**")
            st.info(c['testo'])
    st.stop()

# ==========================================
# 5. GALLERIA E CARICAMENTO MULTIPLO
# ==========================================
st.title(f"👋 Ciao {st.session_state.nome_utente}!")

up_files = st.file_uploader("Trascina qui le foto", type=['jpg','png','jpeg','webp','heic'], accept_multiple_files=True, key=f"up_{st.session_state.upload_key}")

if up_files:
    with st.spinner(f'Caricamento di {len(up_files)} foto...'):
        for i, f in enumerate(up_files):
            tstamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            f_name = f"{tstamp}_{i}_{f.name}"
            supabase.storage.from_("PhotoPollApp").upload(path=f_name, file=f.getvalue(), file_options={"content-type": f.type})
            supabase.table("voti_foto").insert({"file_name": f_name, "conteggio_voti": 0, "autore": st.session_state.nome_utente}).execute()
        st.success("Caricamento completato!")
        st.session_state.upload_key += 1
        st.rerun()

st.divider()

# --- MOSTRA GALLERIA CLICCABILE ---
col_t, col_f = st.columns([2, 1])
with col_t: st.subheader("🖼️ Tocca una foto per aprirla")

tutti = supabase.storage.from_("PhotoPollApp").list()
if tutti:
    v_db = supabase.table("voti_foto").select("*").execute()
    v_dict = {item['file_name']: item['conteggio_voti'] for item in v_db.data}
    
    ext = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
    foto_reali = [f for f in tutti if f['name'].lower().endswith(ext)]

    if foto_reali:
        with col_f:
            with st.popover(f"↕️ {st.session_state.ordinamento}", use_container_width=True):
                if st.button("Più recenti"): st.session_state.ordinamento = "Più recenti"; st.rerun()
                if st.button("I più votati"): st.session_state.ordinamento = "I più votati"; st.rerun()

        # Ordinamento
        if st.session_state.ordinamento == "Più recenti":
            foto_reali.sort(key=lambda x: x['name'], reverse=True)
        else:
            foto_reali.sort(key=lambda x: v_dict.get(x['name'], 0), reverse=True)

        # PREPARAZIONE PER LA GRIGLIA CLICCABILE
        lista_url = []
        for f in foto_reali:
            url_img = supabase.storage.from_("PhotoPollApp").get_public_url(f['name'])
            lista_url.append(url_img)

        # RENDERING DELLA GRIGLIA
        # clicked restituisce l'indice della foto cliccata
        clicked = clickable_images(
            lista_url,
            titles=[f"Voti: {v_dict.get(f['name'], 0)}" for f in foto_reali],
            div_style={"display": "flex", "flex-wrap": "wrap", "justify-content": "center", "gap": "10px"},
            img_style={"width": "110px", "height": "110px", "object-fit": "cover", "border-radius": "10px", "cursor": "pointer"}
        )

        # Se l'utente clicca su una foto (-1 significa nessun click)
        if clicked > -1:
            st.session_state.foto_selezionata = foto_reali[clicked]
            st.rerun()
else:
    st.info("La galleria è vuota.")
