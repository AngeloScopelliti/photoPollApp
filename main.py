import streamlit as st
from supabase import create_client
import datetime
import requests
import streamlit.components.v1 as components

# ==========================================
# 1. INIZIALIZZAZIONE MEMORIA (SESSION STATE)
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
if 'scroll_to' not in st.session_state:
    st.session_state.scroll_to = None

# ==========================================
# 2. CONNESSIONE A SUPABASE
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ==========================================
# 3. GESTIONE CACHE (VELOCITÀ MASSIMA)
# ==========================================
@st.cache_data(ttl=3600) # Memorizza i dati per un'ora
def recupera_dati_globali():
    # Recupera lista file dallo Storage
    tutti_files = supabase.storage.from_("PhotoPollApp").list()
    # Recupera voti e autori dal Database
    v_db = supabase.table("voti_foto").select("*").execute()
    return tutti_files, v_db.data

# ==========================================
# 4. IL LOGIN (NOME + PASSWORD)
# ==========================================
def login():
    if not st.session_state.autenticato:
        st.title("📸 Galleria Privata")
        nome = st.text_input("Come ti chiami?", placeholder="Inserisci il tuo nome...")
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
# 5. VISTA DETTAGLIO (FULLSCREEN & COMMENTI)
# ==========================================
if st.session_state.foto_selezionata:
    f_info = st.session_state.foto_selezionata
    f_name = f_info['name']
    
    if st.button("⬅️ Torna alla Galleria"):
        st.session_state.scroll_to = f_name # Ricorda la posizione
        st.session_state.foto_selezionata = None
        st.rerun()

    img_url = supabase.storage.from_("PhotoPollApp").get_public_url(f_name)
    col_img, col_info = st.columns([2, 1])
    
    with col_img:
        st.image(img_url, use_container_width=True)
    
    with col_info:
        res_db = supabase.table("voti_foto").select("conteggio_voti, autore").eq("file_name", f_name).single().execute()
        voti_totali = res_db.data['conteggio_voti'] if res_db.data else 0
        autore_originale = res_db.data['autore'] if res_db.data else "Sconosciuto"
        
        res_voto_utente = supabase.table("voti_per_utente").select("*").eq("file_name", f_name).eq("nome_utente", st.session_state.nome_utente).execute()
        ha_votato = len(res_voto_utente.data) > 0

        st.subheader(f"Inviata da {autore_originale}")
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
                recupera_dati_globali.clear() # Invalida cache per aggiornare i voti
                st.rerun()
        with c2:
            try:
                img_data = requests.get(img_url).content
                st.download_button("💾", data=img_data, file_name=f_name, mime="image/jpeg", use_container_width=True)
            except: pass
        with c3:
            with st.popover("🗑️", use_container_width=True):
                if st.button("Elimina", type="primary"):
                    supabase.storage.from_("PhotoPollApp").remove([f_name])
                    supabase.table("voti_foto").delete().eq("file_name", f_name).execute()
                    recupera_dati_globali.clear() # Invalida cache
                    st.session_state.foto_selezionata = None
                    st.rerun()

        st.divider()
        st.subheader("💬 Commenti")
        nuovo_comm = st.text_input("Scrivi un commento...")
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
# 6. PAGINA PRINCIPALE (UPLOAD E GALLERIA)
# ==========================================
st.title(f"👋 Ciao, {st.session_state.nome_utente}!")

# Sezione Caricamento Multiplo
up_files = st.file_uploader("Carica una o più foto", type=['jpg','png','jpeg','webp','heic'], accept_multiple_files=True, key=f"up_{st.session_state.upload_key}")

if up_files:
    with st.spinner(f'Caricamento in corso...'):
        for i, f in enumerate(up_files):
            tstamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            f_name = f"{tstamp}_{i}_{f.name}"
            supabase.storage.from_("PhotoPollApp").upload(path=f_name, file=f.getvalue(), file_options={"content-type": f.type})
            supabase.table("voti_foto").insert({"file_name": f_name, "conteggio_voti": 0, "autore": st.session_state.nome_utente}).execute()
        
        recupera_dati_globali.clear() # Svuota la cache dopo l'upload!
        st.success("Foto caricate correttamente!")
        st.session_state.upload_key += 1
        st.rerun()

st.divider()

# Gestione Galleria
col_tit, col_filt = st.columns([2, 1])
with col_tit: st.subheader("🖼️ Esplora la galleria")

# Recupero dati (tramite cache)
tutti, voti_data = recupera_dati_globali()
v_dict = {item['file_name']: item['conteggio_voti'] for item in voti_data}
a_dict = {item['file_name']: item.get('autore', 'Sconosciuto') for item in voti_data}

# Recupero voti personali per icone dinamiche
miei_voti = supabase.table("voti_per_utente").select("file_name").eq("nome_utente", st.session_state.nome_utente).execute()
miei_voti_list = [v['file_name'] for v in miei_voti.data]

# Filtro estensioni
ext = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
foto = [f for f in tutti if f['name'].lower().endswith(ext)]

if foto:
    with col_filt:
        with st.popover(f"↕️ {st.session_state.ordinamento}", use_container_width=True):
            if st.button("Più recenti", use_container_width=True): st.session_state.ordinamento = "Più recenti"; st.rerun()
            if st.button("I più votati", use_container_width=True): st.session_state.ordinamento = "I più votati"; st.rerun()

    if st.session_state.ordinamento == "Più recenti":
        foto.sort(key=lambda x: x['name'], reverse=True)
    else:
        foto.sort(key=lambda x: v_dict.get(x['name'], 0), reverse=True)

    # Disegno della Griglia
    cols = st.columns(3)
    for i, f in enumerate(foto):
        img_url = supabase.storage.from_("PhotoPollApp").get_public_url(f['name'])
        v_att = v_dict.get(f['name'], 0)
        gia_votato = f['name'] in miei_voti_list
        safe_id = "anchor_" + f['name'].replace(".", "_")
        
        with cols[i % 3]:
            # Ancora per lo scroll
            st.markdown(f'<div id="{safe_id}"></div>', unsafe_allow_html=True)
            st.image(img_url, use_container_width=True)
            st.caption(f"By: {a_dict.get(f['name'], 'Sconosciuto')} | ⭐ **{v_att}**  {"❤️" if gia_votato}")
            
            # Bottoni Rapidi
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
                    
                    recupera_dati_globali.clear() # Aggiorna cache voti
                    st.session_state.scroll_to = f['name']
                    st.rerun()
            with b_apri:
                if st.button("🔍", key=f"a_{f['name']}", use_container_width=True):
                    st.session_state.foto_selezionata = f
                    st.rerun()

# ==========================================
# 7. LOGICA DI SCROLL AUTOMATICO (JS)
# ==========================================
if st.session_state.scroll_to:
    target = "anchor_" + st.session_state.scroll_to.replace(".", "_")
    js = f"""<script>
        var el = window.parent.document.getElementById('{target}');
        if (el) {{ el.scrollIntoView({{behavior: 'smooth', block: 'center'}}); }}
    </script>"""
    components.html(js, height=0)
    st.session_state.scroll_to = None
