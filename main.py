import streamlit as st
from supabase import create_client
import datetime
import requests

# ==========================================
# 1. INIZIALIZZAZIONE MEMORIA (SESSION STATE)
# ==========================================
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "nome_utente" not in st.session_state:
    st.session_state.nome_utente = ""
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0
if 'ordinamento' not in st.session_state:
    st.session_state.ordinamento = "Più recenti"

# Variabili per gestire il popup senza riaperture accidentali
if 'foto_in_dialog' not in st.session_state:
    st.session_state.foto_in_dialog = None
if 'apri_cliccato' not in st.session_state:
    st.session_state.apri_cliccato = False

# PULIZIA AUTOMATICA: Se l'app si ricarica per un filtro o un upload, svuotiamo la memoria del popup!
if not st.session_state.apri_cliccato:
    st.session_state.foto_in_dialog = None
st.session_state.apri_cliccato = False # Resetta il trigger per il prossimo giro

# ==========================================
# 2. CONNESSIONE A SUPABASE E CACHE
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

@st.cache_data(ttl=3600)
def recupera_dati_globali():
    tutti_files = supabase.storage.from_("PhotoPollApp").list()
    v_db = supabase.table("voti_foto").select("*").execute()
    return tutti_files, v_db.data

# ==========================================
# 3. IL LOGIN
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
# 4. FUNZIONE DIALOG E CALLBACK
# ==========================================
# Callback: Questa funzione si attiva SOLO quando clicchi esattamente il tasto "Apri"
def imposta_foto_da_aprire(file_obj):
    st.session_state.foto_in_dialog = file_obj
    st.session_state.apri_cliccato = True

@st.dialog("Dettaglio Foto", width="large")
def mostra_popup_foto(file_obj):
    f_name = file_obj['name']
    img_url = supabase.storage.from_("PhotoPollApp").get_public_url(f_name)
    
    col_img, col_info = st.columns([2, 1])
    
    with col_img:
        st.image(img_url, use_container_width=True)
    
    with col_info:
        res_db = supabase.table("voti_foto").select("conteggio_voti, autore").eq("file_name", f_name).single().execute()
        voti_totali = res_db.data['conteggio_voti'] if res_db.data else 0
        autore_f = res_db.data['autore'] if res_db.data else "Sconosciuto"
        
        res_voto_utente = supabase.table("voti_per_utente").select("*").eq("file_name", f_name).eq("nome_utente", st.session_state.nome_utente).execute()
        ha_votato = len(res_voto_utente.data) > 0

        st.subheader(f"Di {autore_f}")
        st.metric("Punteggio", f"⭐ {voti_totali}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            testo_voto = "Votato" if ha_votato else "Vota"
            icona_voto = ":material/favorite:" if not ha_votato else "❤️"
            
            if st.button(testo_voto, icon=icona_voto, use_container_width=True, type="secondary" if ha_votato else "primary", key="btn_vota_pop"):
                if not ha_votato:
                    supabase.table("voti_per_utente").insert({"file_name": f_name, "nome_utente": st.session_state.nome_utente}).execute()
                    supabase.table("voti_foto").update({"conteggio_voti": voti_totali + 1}).eq("file_name", f_name).execute()
                else:
                    supabase.table("voti_per_utente").delete().eq("file_name", f_name).eq("nome_utente", st.session_state.nome_utente).execute()
                    supabase.table("voti_foto").update({"conteggio_voti": max(0, voti_totali - 1)}).eq("file_name", f_name).execute()
                
                recupera_dati_globali.clear()
                st.rerun() # Aggiorna i dati senza chiudere
        
        with c2:
            try:
                img_data = requests.get(img_url).content
                st.download_button("Salva", icon=":material/download:", data=img_data, file_name=f_name, mime="image/jpeg", use_container_width=True)
            except: pass
            
        with c3:
            with st.popover("Elimina", icon=":material/delete:", use_container_width=True):
                if st.button("Conferma", type="primary", key="confirm_del_pop"):
                    supabase.storage.from_("PhotoPollApp").remove([f_name])
                    supabase.table("voti_foto").delete().eq("file_name", f_name).execute()
                    recupera_dati_globali.clear()
                    st.session_state.foto_in_dialog = None
                    st.rerun() # Chiude il popup

        st.divider()
        st.subheader("💬 Commenti")
        nuovo_comm = st.text_input("Aggiungi un commento...", key="in_comm_pop")
        if st.button("Invia", icon=":material/send:", key="btn_comm_pop"):
            if nuovo_comm:
                supabase.table("commenti_foto").insert({"file_name": f_name, "testo": nuovo_comm, "autore": st.session_state.nome_utente}).execute()
                st.rerun() 
        
        comm_db = supabase.table("commenti_foto").select("*").eq("file_name", f_name).order("creato_at", desc=True).execute()
        for c in comm_db.data:
            st.caption(f"🕒 {c['creato_at'][11:16]} - **{c.get('autore', 'Anonimo')}**")
            st.info(c['testo'])
            
    if st.button("Chiudi", icon=":material/close:", use_container_width=True, type="tertiary"):
        st.session_state.foto_in_dialog = None
        st.rerun()

# ==========================================
# 5. LOGICA DI ATTIVAZIONE POPUP
# ==========================================
if st.session_state.foto_in_dialog:
    mostra_popup_foto(st.session_state.foto_in_dialog)

# ==========================================
# 6. PAGINA PRINCIPALE (UPLOAD)
# ==========================================
st.title(f"👋 Ciao, {st.session_state.nome_utente}!")

up_files = st.file_uploader("Seleziona una o più foto", type=['jpg','png','jpeg','webp','heic'], accept_multiple_files=True, key=f"up_{st.session_state.upload_key}")

if up_files:
    with st.spinner('Caricamento...'):
        for i, f in enumerate(up_files):
            tstamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            f_name = f"{tstamp}_{i}_{f.name}"
            supabase.storage.from_("PhotoPollApp").upload(path=f_name, file=f.getvalue(), file_options={"content-type": f.type})
            supabase.table("voti_foto").insert({"file_name": f_name, "conteggio_voti": 0, "autore": st.session_state.nome_utente}).execute()
        recupera_dati_globali.clear()
        st.success("Foto caricate!")
        st.session_state.upload_key += 1
        st.rerun()

st.divider()

# ==========================================
# 7. GALLERIA
# ==========================================
col_t, col_f = st.columns([2, 1])
with col_t: st.subheader("🖼️ Esplora")

tutti, voti_data = recupera_dati_globali()
v_dict = {item['file_name']: item['conteggio_voti'] for item in voti_data}
a_dict = {item['file_name']: item.get('autore', 'Sconosciuto') for item in voti_data}

miei_voti = supabase.table("voti_per_utente").select("file_name").eq("nome_utente", st.session_state.nome_utente).execute()
miei_voti_list = [v['file_name'] for v in miei_voti.data]

ext = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
foto = [f for f in tutti if f['name'].lower().endswith(ext)]

if foto:
    with col_f:
        with st.popover(f"↕️ {st.session_state.ordinamento}", use_container_width=True):
            if st.button("Più recenti", use_container_width=True): st.session_state.ordinamento = "Più recenti"; st.rerun()
            if st.button("I più votati", use_container_width=True): st.session_state.ordinamento = "I più votati"; st.rerun()

    if st.session_state.ordinamento == "Più recenti": foto.sort(key=lambda x: x['name'], reverse=True)
    else: foto.sort(key=lambda x: v_dict.get(x['name'], 0), reverse=True)

    cols = st.columns(3)
    for i, f in enumerate(foto):
        img_url = supabase.storage.from_("PhotoPollApp").get_public_url(f['name'])
        v_att = v_dict.get(f['name'], 0)
        gia_votato = f['name'] in miei_voti_list
        
        with cols[i % 3]:
            st.image(img_url, use_container_width=True)
            v_icon_testo = " ❤️" if gia_votato else ""
            st.caption(f"By: {a_dict.get(f['name'], 'Sconosciuto')} | ⭐ **{v_att}**{v_icon_testo}")
            
            # --- TASTI SENZA BORDI (TERTIARY) E PROPORZIONI 1 A 3 ---
            b_vota, b_apri = st.columns([1, 3]) 
            
            with b_vota:
                icona_btn = ":material/favorite:" if not gia_votato else "❤️"
                
                if st.button("", icon=icona_btn, key=f"v_{f['name']}", use_container_width=True, type="tertiary"):
                    if not gia_votato:
                        supabase.table("voti_per_utente").insert({"file_name": f['name'], "nome_utente": st.session_state.nome_utente}).execute()
                        supabase.table("voti_foto").update({"conteggio_voti": v_att + 1}).eq("file_name", f['name']).execute()
                    else:
                        supabase.table("voti_per_utente").delete().eq("file_name", f['name']).eq("nome_utente", st.session_state.nome_utente).execute()
                        supabase.table("voti_foto").update({"conteggio_voti": max(0, v_att - 1)}).eq("file_name", f['name']).execute()
                    recupera_dati_globali.clear()
                    st.rerun()
            
            with b_apri:
                # Usa ON_CLICK per attivare la funzione callback in modo sicuro
                st.button("Apri", icon=":material/fullscreen:", key=f"a_{f['name']}", use_container_width=True, type="tertiary", on_click=imposta_foto_da_aprire, args=(f,))
else:
    st.info("Galleria vuota.")
