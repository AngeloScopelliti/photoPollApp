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

# 3. GALLERIA E VOTI
st.divider()
files = supabase.storage.from_("PhotoPollApp").list()

if files:
    # Recuperiamo tutti i voti dal database in un colpo solo
    voti_db = supabase.table("voti_foto").select("*").execute()
    voti_dict = {item['file_name']: item['conteggio_voti'] for item in voti_db.data}

    cols = st.columns(3)
    for index, file in enumerate(files):
        if file['name'].startswith('.'): continue
        
        img_url = supabase.storage.from_("PhotoPollApp").get_public_url(file['name'])
        voti_attuali = voti_dict.get(file['name'], 0)
        
        with cols[index % 3]:
            st.image(img_url, use_container_width=True)
            st.write(f"⭐ Voti: {voti_attuali}")
            
            if st.button(f"Vota!", key=f"voto_{file['name']}"):
                # Incrementa il voto nel database
                nuovo_voto = voti_attuali + 1
                supabase.table("voti_foto").update({"conteggio_voti": nuovo_voto}).eq("file_name", file['name']).execute()
                st.rerun()
