import streamlit as st
from supabase import create_client
import datetime
import requests

# ==========================================
# 1. INIZIALIZZAZIONE (MEMORIA DELL'APP)
# ==========================================
if "password_corretta" not in st.session_state:
    st.session_state.password_corretta = False
if 'foto_selezionata' not in st.session_state:
    st.session_state.foto_selezionata = None
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0
if 'ordinamento' not in st.session_state:
    st.session_state.ordinamento = "Più recenti"

# ==========================================
# 2. IL BUTTAFUORI (SISTEMA DI PASSWORD)
# ==========================================
def check_password():
    if not st.session_state.password_corretta:
        st.title("🔒 Area Riservata agli Amici")
        st.write("Inserisci la parola d'ordine per vedere la galleria.")
        pwd_inserita = st.text_input("Password", type="password")
        
        if st.button("Entra"):
            if pwd_inserita == st.secrets["PASSWORD_ACCESSO"]:
                st.session_state.password_corretta = True
                st.rerun()
            else:
                st.error("😕 Password errata. Riprova!")
        return False
    return True

# Se la password è sbagliata, fermiamo la pagina qui
if not check_password():
    st.stop()

# ==========================================
# 3. CONNESSIONE A SUPABASE
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ==========================================
# 4. VISTA: DETTAGLIO FOTO (FULLSCREEN)
# ==========================================
# Se abbiamo cliccato una foto, mostriamo SOLO questa sezione
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
        
        # Recupera i voti dal Database
        res_voti = supabase.table("voti_foto").select("conteggio_voti").eq("file_name", f_name).single().execute()
        voti_attuali = res_voti.data['conteggio_voti'] if res_voti.data else 0
        
        st.metric("Punteggio", f"⭐ {voti_attuali}")
        
        # Bottoni delle azioni
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👍 Vota", use_container_width=True):
                supabase.table("voti_foto").update({"conteggio_voti": voti_attuali + 1}).eq("file_name", f_name).execute()
                st.rerun()
        with c2:
            # Download dell'immagine
            try:
                img_data = requests.get(img_url).content
                st.download_button("💾 Salva", data=img_data, file_name=f_name, mime="image/jpeg", use_container_width=True)
            except:
                pass
        with c3:
            # Elimina con conferma
            with st.popover("🗑️ Elimina", use_container_width=True):
                st.warning("Sei sicuro?")
                if st.button("Sì", key="del_det", type="primary"):
                    supabase.storage.from_("PhotoPollApp").remove([f_name])
                    supabase.table("voti_foto").delete().eq("file_name", f_name).execute()
                    st.session_state.foto_selezionata = None
                    st.rerun()

        st.divider()
        
        # Sezione Commenti
        st.subheader("💬 Commenti")
        nuovo_comm = st.text_input("Scrivi qui...", key="input_comm")
        if st.button("Invia commento"):
            if nuovo_comm:
                supabase.table("commenti_foto").insert({"file_name": f_name, "testo": nuovo_comm}).execute()
                st.rerun()
        
        # Mostra i commenti vecchi
        comm_db = supabase.table("commenti_foto").select("*").eq("file_name", f_name).order("creato_at", desc=True).execute()
        for c in comm_db.data:
            # Mostra solo la data e l'ora, togliendo i millisecondi
            st.caption(f"🕒 {c['creato_at'][:10]} alle {c['creato_at'][11:16]}")
            st.info(c['testo'])
            
    # Fine della Vista Dettaglio. Blocchiamo la pagina qui.
    st.stop()


# ==========================================
# 5. VISTA: CARICAMENTO E GALLERIA PRINCIPALE
# ==========================================
st.title("📸 La nostra Galleria")

# --- SEZIONE UPLOAD ---
uploaded_file = st.file_uploader(
    "Carica una nuova foto", 
    type=['jpg', 'png', 'jpeg', 'webp', 'heic'],
    key=f"uploader_{st.session_state.upload_key}"
)

if uploaded_file is not None:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}_{uploaded_file.name}"
    
    with st.spinner('Sto salvando la foto...'):
        # Salviamo la foto
        supabase.storage.from_("PhotoPollApp").upload(
            path=file_name,
            file=uploaded_file.getvalue(),
            file_options={"content-type": uploaded_file.type}
        )
        # Creiamo la riga per i voti nel database
        supabase.table("voti_foto").insert({"file_name": file_name, "conteggio_voti": 0}).execute()
        
        st.success("Caricata con successo!")
        st.session_state.upload_key += 1
        st.rerun()

st.divider()

# --- SEZIONE GALLERIA ---
col_titolo, col_filtro = st.columns([2, 1])
with col_titolo:
    st.subheader("🖼️ Esplora le foto")

# Recuperiamo la lista di tutto
tutti_gli_elementi = supabase.storage.from_("PhotoPollApp").list()

if tutti_gli_elementi:
    # Recuperiamo tutti i voti in un colpo solo
    voti_db = supabase.table("voti_foto").select("*").execute()
    voti_dict = {item['file_name']: item['conteggio_voti'] for item in voti_db.data}

    # Teniamo solo le immagini vere (Filtro magico)
    estensioni = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
    foto_reali = [f for f in tutti_gli_elementi if f['name'].lower().endswith(estensioni)]

    if foto_reali:
        
        # Filtro per riordinare le foto (Finto Selectbox)
        with col_filtro:
            with st.popover(f"↕️ {st.session_state.ordinamento}", use_container_width=True):
                if st.button("Più recenti", use_container_width=True):
                    st.session_state.ordinamento = "Più recenti"
                    st.rerun()
                if st.button("Meno recenti", use_container_width=True):
                    st.session_state.ordinamento = "Meno recenti"
                    st.rerun()
                if st.button("I più votati", use_container_width=True):
                    st.session_state.ordinamento = "I più votati"
                    st.rerun()

        # Logica matematica per riordinare
        if st.session_state.ordinamento == "Più recenti":
            foto_reali.sort(key=lambda x: x['name'], reverse=True)
        elif st.session_state.ordinamento == "Meno recenti":
            foto_reali.sort(key=lambda x: x['name'])
        elif st.session_state.ordinamento == "I più votati":
            foto_reali.sort(key=lambda x: voti_dict.get(x['name'], 0), reverse=True)

        # Disegniamo la griglia a 3 colonne
        cols = st.columns(3)
        for index, file in enumerate(foto_reali):
            img_url = supabase.storage.from_("PhotoPollApp").get_public_url(file['name'])
            voti_attuali = voti_dict.get(file['name'], 0)
            
            with cols[index % 3]:
                st.image(img_url, use_container_width=True)
                st.write(f"⭐ Voti: **{voti_attuali}**")
                
                # Tasto per entrare nella foto grande
                if st.button("🔍 Espandi", key=f"open_{file['name']}", use_container_width=True):
                    st.session_state.foto_selezionata = file
                    st.rerun()
    else:
        st.info("Nessuna immagine valida trovata.")
else:
    st.info("La galleria è vuota. Inizia a caricare la prima foto!")
