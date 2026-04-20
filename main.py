import streamlit as st
from supabase import create_client
import datetime

# 1. Configurazione e Session State per la pulizia dell'upload
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📸 Galleria con Votazione")

# 2. SEZIONE UPLOAD con chiave dinamica
uploaded_file = st.file_uploader(
    "Carica una foto", 
    type=['jpg', 'png', 'jpeg'],
    key=f"uploader_{st.session_state.upload_key}"
)

if uploaded_file is not None:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}_{uploaded_file.name}"
    
    with st.spinner('Caricamento...'):
        # Upload Storage
        supabase.storage.from_("PhotoPollApp").upload(
            path=file_name,
            file=uploaded_file.getvalue(),
            file_options={"content-type": uploaded_file.type}
        )
        
        # Inserimento record voti nel Database
        supabase.table("voti_foto").insert({"file_name": file_name, "conteggio_voti": 0}).execute()
        
        st.success("Caricata!")
        
        # PULIZIA: Cambiamo la chiave per resettare il widget al prossimo refresh
        st.session_state.upload_key += 1
        st.rerun()

# 3. GALLERIA, VOTI, FILTRI ED ELIMINAZIONE
st.divider()

# Creiamo due colonne per il titolo e per il filtro di ordinamento
col_titolo, col_filtro = st.columns([2, 1])
with col_titolo:
    st.subheader("🖼️ Galleria delle Foto")

tutti_gli_elementi = supabase.storage.from_("PhotoPollApp").list()

if tutti_gli_elementi:
    voti_db = supabase.table("voti_foto").select("*").execute()
    voti_dict = {item['file_name']: item['conteggio_voti'] for item in voti_db.data}

    estensioni_valide = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
    foto_reali = [f for f in tutti_gli_elementi if f['name'].lower().endswith(estensioni_valide)]

    if foto_reali:
        
        # --- NUOVA SEZIONE: FILTRO DI ORDINAMENTO ---
        with col_filtro:
            ordinamento = st.selectbox(
                "Ordina per:",
                ("Più recenti", "Meno recenti", "I più votati"),
                label_visibility="collapsed" # Nasconde l'etichetta per un look più pulito
            )
        
        # Logica per riordinare la lista 'foto_reali'
        if ordinamento == "Più recenti":
            # Ordine alfabetico inverso (dal timestamp più alto al più basso)
            foto_reali.sort(key=lambda x: x['name'], reverse=True)
        
        elif ordinamento == "Meno recenti":
            # Ordine alfabetico normale (dal timestamp più basso al più alto)
            foto_reali.sort(key=lambda x: x['name'])
            
        elif ordinamento == "I più votati":
            # Ordina in base al numero di voti nel dizionario (dal più alto al più basso)
            foto_reali.sort(key=lambda x: voti_dict.get(x['name'], 0), reverse=True)
        # --------------------------------------------

        # Ora disegniamo la griglia con la lista ordinata
        cols = st.columns(3)
        for index, file in enumerate(foto_reali):
            img_url = supabase.storage.from_("PhotoPollApp").get_public_url(file['name'])
            voti_attuali = voti_dict.get(file['name'], 0)
            
            with cols[index % 3]:
                st.image(img_url, use_container_width=True)
                st.write(f"⭐ Voti: **{voti_attuali}**")
                
                btn_vota, btn_del = st.columns(2)
                
                with btn_vota:
                    if st.button("Vota 👍", key=f"voto_{file['name']}"):
                        nuovo_voto = voti_attuali + 1
                        supabase.table("voti_foto").update({"conteggio_voti": nuovo_voto}).eq("file_name", file['name']).execute()
                        st.rerun()
                
                with btn_del:
                    with st.popover("Elimina 🗑️"):
                        st.warning("Sei sicuro?")
                        if st.button("Sì, elimina", key=f"confirm_del_{file['name']}", type="primary"):
                            with st.spinner("Eliminando..."):
                                supabase.storage.from_("PhotoPollApp").remove([file['name']])
                                supabase.table("voti_foto").delete().eq("file_name", file['name']).execute()
                                st.success("Eliminata!")
                                st.rerun()
    else:
        st.info("Nessuna immagine valida trovata.")
else:
    st.info("La galleria è vuota.")
