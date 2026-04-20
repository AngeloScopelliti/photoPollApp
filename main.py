import streamlit as st
from supabase import create_client
import datetime
import requests

# ==========================================
# 1. INIZIALIZZAZIONE (MEMORIA DELL'APP)
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
# 2. IL NUOVO LOGIN (NOME + PASSWORD)
# ==========================================
def login():
    if not st.session_state.autenticato:
        st.title("📸 Benvenuto in Galleria")
        st.write("Identificati per accedere alla bacheca privata.")
        
        # Campi di inserimento
        nome = st.text_input("Come ti chiami?", placeholder="Es. Marco, Giulia...")
        pwd = st.text_input("Parola d'ordine", type="password")
        
        if st.button("Entra nell'App"):
            if pwd == st.secrets["PASSWORD_ACCESSO"] and nome.strip() != "":
                st.session_state.autenticato = True
                st.session_state.nome_utente = nome
                st.rerun()
            elif nome.strip() == "":
                st.warning("Ehi, inserisci il tuo nome!")
            else:
                st.error("Password errata!")
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
# 4. VISTA DETTAGLIO (CON COMMENTI IDENTIFICATI)
# ==========================================
if st.session_state.foto_selezionata:
    file_info = st.session_state.foto_selezionata
    f_name = file_info['name']
    
    if st.button("⬅️ Torna alla Galleria"):
        st.session_state.foto_selezionata = None
        st.rerun()

    img_url = supabase.storage.from_("PhotoPollApp").get_public_url(f_name)
    col_img, col_info = st.columns([2, 1])
    
    with col_img:
        st.image(img_url, use_container_width=True)
    
    with col_info:
        st.subheader("Dettagli")
        
        # Dati foto (Chi l'ha caricata e voti)
        res_data = supabase.table("voti_foto").select("conteggio_voti, autore").eq("file_name", f_name).single().execute()
        voti_attuali = res_data.data['conteggio_voti'] if res_data.data else 0
        autore_foto = res_data.data['autore'] if res_data.data else "Sconosciuto"
        
        st.write(f"📤 Caricata da: **{autore_foto}**")
        st.metric("Punteggio", f"⭐ {voti_attuali}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👍 Vota", use_container_width=True):
                supabase.table("voti_foto").update({"conteggio_voti": voti_attuali + 1}).eq("file_name", f_name).execute()
                st.rerun()
        with c2:
            try:
                img_data = requests.get(img_url).content
                st.download_button("💾", data=img_data, file_name=f_name, mime="image/jpeg", use_container_width=True)
            except: pass
        with c3:
            with st.popover("🗑️", use_container_width=True):
                if st.button("Sì", key="del_det", type="primary"):
                    supabase.storage.from_("PhotoPollApp").remove([f_name])
                    supabase.table("voti_foto").delete().eq("file_name", f_name).execute()
                    st.session_state.foto_selezionata = None
                    st.rerun()

        st.divider()
        st.subheader("💬 Commenti")
        nuovo_comm = st.text_input("Aggiungi un commento...", key="input_comm")
        if st.button("Invia"):
            if nuovo_comm:
                # SALVIAMO IL NOME DI CHI COMMENTA
                supabase.table("commenti_foto").insert({
                    "file_name": f_name, 
                    "testo": nuovo_comm,
                    "autore": st.session_state.nome_utente
                }).execute()
                st.rerun()
        
        # Mostra i commenti con il nome dell'autore
        comm_db = supabase.table("commenti_foto").select("*").eq("file_name", f_name).order("creato_at", desc=True).execute()
        for c in comm_db.data:
            autore_c = c.get('autore', 'Anonimo')
            st.caption(f"🕒 {c['creato_at'][11:16]} - **{autore_c}** ha scritto:")
            st.info(c['testo'])
            
    st.stop()

# ==========================================
# 5. VISTA GALLERIA (IDENTIFICA CHI CARICA)
# ==========================================
st.title(f"👋 Ciao {st.session_state.nome_utente}!")

# Abbiamo aggiunto l'opzione per il caricamento multiplo e cambiato il nome in "uploaded_files"
uploaded_files = st.file_uploader(
    "Carica le tue foto (puoi selezionarne più di una!)", 
    type=['jpg', 'png', 'jpeg', 'webp', 'heic'],
    accept_multiple_files=True, # <--- LA MAGIA È QUI
    key=f"uploader_{st.session_state.upload_key}"
)

# Se la lista di file non è vuota...
if uploaded_files:
    with st.spinner(f'Sto salvando {len(uploaded_files)} foto...'):
        
        # Facciamo un ciclo "for" per caricare una foto alla volta
        for indice, file in enumerate(uploaded_files):
            # Usiamo i microsecondi (%f) e l'indice per avere nomi assolutamente unici
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_name = f"{timestamp}_num{indice}_{file.name}"
            
            # Salvataggio su Storage
            supabase.storage.from_("PhotoPollApp").upload(
                path=file_name, 
                file=file.getvalue(), 
                file_options={"content-type": file.type}
            )
            
            # Creazione riga nel Database
            supabase.table("voti_foto").insert({
                "file_name": file_name, 
                "conteggio_voti": 0,
                "autore": st.session_state.nome_utente
            }).execute()
            
        st.success(f"Hai caricato {len(uploaded_files)} foto con successo!")
        st.session_state.upload_key += 1
        st.rerun()


st.divider()

# --- GALLERIA ---
col_t, col_f = st.columns([2, 1])
with col_t: st.subheader("🖼️ Esplora")

tutti = supabase.storage.from_("PhotoPollApp").list()
if tutti:
    voti_db = supabase.table("voti_foto").select("*").execute()
    voti_dict = {item['file_name']: item['conteggio_voti'] for item in voti_db.data}
    autore_dict = {item['file_name']: item.get('autore', 'Sconosciuto') for item in voti_db.data}

    estensioni = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
    foto_reali = [f for f in tutti if f['name'].lower().endswith(estensioni)]

    if foto_reali:
        with col_f:
            with st.popover(f"↕️ {st.session_state.ordinamento}", use_container_width=True):
                if st.button("Più recenti"): st.session_state.ordinamento = "Più recenti"; st.rerun()
                if st.button("Meno recenti"): st.session_state.ordinamento = "Meno recenti"; st.rerun()
                if st.button("I più votati"): st.session_state.ordinamento = "I più votati"; st.rerun()

        if st.session_state.ordinamento == "Più recenti": foto_reali.sort(key=lambda x: x['name'], reverse=True)
        elif st.session_state.ordinamento == "Meno recenti": foto_reali.sort(key=lambda x: x['name'])
        elif st.session_state.ordinamento == "I più votati": foto_reali.sort(key=lambda x: voti_dict.get(x['name'], 0), reverse=True)

        cols = st.columns(3)
        for index, file in enumerate(foto_reali):
            img_url = supabase.storage.from_("PhotoPollApp").get_public_url(file['name'])
            voti_att = voti_dict.get(file['name'], 0)
            autore_f = autore_dict.get(file['name'], "Sconosciuto")
            
            with cols[index % 3]:
                st.image(img_url, use_container_width=True)
                st.caption(f"By: **{autore_f}**")
                st.write(f"⭐ Voti: **{voti_att}**")
                if st.button("🔍 Espandi", key=f"op_{file['name']}", use_container_width=True):
                    st.session_state.foto_selezionata = file
                    st.rerun()
else:
    st.info("Galleria vuota.")
