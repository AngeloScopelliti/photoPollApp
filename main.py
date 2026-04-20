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

# ==========================================
# 2. CONNESSIONE A SUPABASE E CACHE
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

@st.cache_data(ttl=3600) # Memorizza i dati per un'ora (velocità massima)
def recupera_dati_globali():
    tutti_files = supabase.storage.from_("PhotoPollApp").list()
    v_db = supabase.table("voti_foto").select("*").execute()
    return tutti_files, v_db.data

# ==========================================
# 3. IL LOGIN (NOME + PASSWORD)
# ==========================================
def login():
    if not st.session_state.autenticato:
        st.title("📸 La Nostra Galleria")
        st.write("Inserisci i tuoi dati per accedere.")
        
        nome = st.text_input("Come ti chiami?", placeholder="Es. Marco, Giulia...")
        pwd = st.text_input("Parola d'ordine", type="password")
        
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
    st.stop() # Ferma l'app qui se non sei loggato

# ==========================================
# 4. VISTA DETTAGLIO (FINESTRA A SCOMPARSA)
# ==========================================
@st.dialog("Dettaglio Foto", width="large")
def apri_dettaglio_foto(f_name, autore_originale, img_url):
    col_img, col_info = st.columns([2, 1])
    
    with col_img:
        st.image(img_url, use_container_width=True)
    
    with col_info:
        # Dati aggiornati in tempo reale
        res_db = supabase.table("voti_foto").select("conteggio_voti").eq("file_name", f_name).single().execute()
        voti_totali = res_db.data['conteggio_voti'] if res_db.data else 0
        
        res_voto_utente = supabase.table("voti_per_utente").select("*").eq("file_name", f_name).eq("nome_utente", st.session_state.nome_utente).execute()
        ha_votato = len(res_voto_utente.data) > 0

        st.subheader(f"Di {autore_originale}")
        st.metric("Voti", f"⭐ {voti_totali}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            label = "❤️ Votato" if ha_votato else "👍 Vota"
            if st.button(label, use_container_width=True, type="secondary" if ha_votato else "primary"):
                if not ha_votato:
                    supabase.table("voti_per_utente").insert({"file_name": f_name, "nome_utente": st.session_state.nome_utente}).execute()
                    supabase.table("voti_foto").update({"conteggio_voti": voti_totali + 1}).eq("file_name", f_name).execute()
                else:
                    supabase.table("voti_per_utente").delete().eq("file_name", f_name).eq("nome_utente", st.session_state.nome_utente).execute()
                    supabase.table("voti_foto").update({"conteggio_voti": max(0, voti_totali - 1)}).eq("file_name", f_name).execute()
                recupera_dati_globali.clear() # Svuota la cache
                st.rerun() # Aggiorna la finestra a comparsa
                
        with c2:
            try:
                img_data = requests.get(img_url).content
                st.download_button("💾", data=img_data, file_name=f_name, mime="image/jpeg", use_container_width=True)
            except: pass
            
        with c3:
            with st.popover("🗑️", use_container_width=True):
                if st.button("Elimina", key="del_dialog", type="primary"):
                    supabase.storage.from_("PhotoPollApp").remove([f_name])
                    supabase.table("voti_foto").delete().eq("file_name", f_name).execute()
                    recupera_dati_globali.clear()
                    st.rerun() 

        st.divider()
        st.subheader("💬 Commenti")
        nuovo_comm = st.text_input("Scrivi qui...", key="in_comm_dialog")
        if st.button("Invia commento", key="btn_invia_comm"):
            if nuovo_comm:
                supabase.table("commenti_foto").insert({"file_name": f_name, "testo": nuovo_comm, "autore": st.session_state.nome_utente}).execute()
                st.rerun() 
        
        comm_db = supabase.table("commenti_foto").select("*").eq("file_name", f_name).order("creato_at", desc=True).execute()
        for c in comm_db.data:
            st.caption(f"🕒 {c['creato_at'][11:16]} - **{c.get('autore', 'Anonimo')}**")
            st.info(c['testo'])

# ==========================================
# 5. PAGINA PRINCIPALE (UPLOAD E GALLERIA)
# ==========================================
st.title(f"👋 Ciao, {st.session_state.nome_utente}!")

# Caricamento Multiplo
up_files = st.file_uploader("Carica una o più foto della serata", type=['jpg','png','jpeg','webp','heic'], accept_multiple_files=True, key=f"up_{st.session_state.upload_key}")

if up_files:
    with st.spinner(f'Salvataggio di {len(up_files)} foto in corso...'):
        for i, f in enumerate(up_files):
            tstamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            f_name = f"{tstamp}_{i}_{f.name}"
            
            supabase.storage.from_("PhotoPollApp").upload(path=f_name, file=f.getvalue(), file_options={"content-type": f.type})
            supabase.table("voti_foto").insert({"file_name": f_name, "conteggio_voti": 0, "autore": st.session_state.nome_utente}).execute()
        
        recupera_dati_globali.clear() # Svuota la cache per mostrare subito le foto nuove
        st.success("Foto caricate con successo!")
        st.session_state.upload_key += 1
        st.rerun()

st.divider()

# Intestazione Galleria
col_tit, col_filt = st.columns([2, 1])
with col_tit: st.subheader("🖼️ Esplora la galleria")

# Chiamata alla CACHE (Velocissima)
tutti, voti_data = recupera_dati_globali()
v_dict = {item['file_name']: item['conteggio_voti'] for item in voti_data}
a_dict = {item['file_name']: item.get('autore', 'Sconosciuto') for item in voti_data}

# Voti personali per sapere cosa si è già votato
miei_voti = supabase.table("voti_per_utente").select("file_name").eq("nome_utente", st.session_state.nome_utente).execute()
miei_voti_list = [v['file_name'] for v in miei_voti.data]

ext = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
foto = [f for f in tutti if f['name'].lower().endswith(ext)]

if foto:
    # Filtro Ordinamento
    with col_filt:
        with st.popover(f"↕️ {st.session_state.ordinamento}", use_container_width=True):
            if st.button("Più recenti", use_container_width=True): st.session_state.ordinamento = "Più recenti"; st.rerun()
            if st.button("I più votati", use_container_width=True): st.session_state.ordinamento = "I più votati"; st.rerun()

    if st.session_state.ordinamento == "Più recenti":
        foto.sort(key=lambda x: x['name'], reverse=True)
    else:
        foto.sort(key=lambda x: v_dict.get(x['name'], 0), reverse=True)

    # Disegno della Griglia Fotografica
    cols = st.columns(3)
    for i, f in enumerate(foto):
        img_url = supabase.storage.from_("PhotoPollApp").get_public_url(f['name'])
        v_att = v_dict.get(f['name'], 0)
        autore_f = a_dict.get(f['name'], 'Sconosciuto')
        gia_votato = f['name'] in miei_voti_list
        
        with cols[i % 3]:
            st.image(img_url, use_container_width=True)
            st.caption(f"Di {autore_f} | ⭐ **{v_att}**")
            
            # Bottoni Rapidi (Vota e Apri Popup)
            b_vota, b_apri = st.columns(2)
            
            with b_vota:
                icona = "❤️" if gia_votato else "👍"
                if st.button(icona, key=f"v_{f['name']}", use_container_width=True, type="secondary" if gia_votato else "primary"):
                    if not gia_votato:
                        supabase.table("voti_per_utente").insert({"file_name": f['name'], "nome_utente": st.session_state.nome_utente}).execute()
                        supabase.table("voti_foto").update({"conteggio_voti": v_att + 1}).eq("file_name", f['name']).execute()
                    else:
                        supabase.table("voti_per_utente").delete().eq("file_name", f['name']).eq("nome_utente", st.session_state.nome_utente).execute()
                        supabase.table("voti_foto").update({"conteggio_voti": max(0, v_att - 1)}).eq("file_name", f['name']).execute()
                    
                    recupera_dati_globali.clear() # Aggiorna i dati per tutti
                    st.rerun()
                    
            with b_apri:
                # Questo bottone attiva la finestra a scomparsa magica!
                if st.button("🔍", key=f"a_{f['name']}", use_container_width=True):
                    apri_dettaglio_foto(f['name'], autore_f, img_url)
else:
    st.info("Nessuna foto trovata. Rompi il ghiaccio e carica la prima!")
