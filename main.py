import streamlit as st
from supabase import create_client

# Configurazione connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📸 La nostra Galleria Privata")

# Tasto per importare le foto
uploaded_file = st.file_uploader("Trascina qui la tua foto o clicca per importare", type=['jpg', 'png', 'jpeg'])

if uploaded_file is not None:
    # Genera un nome file unico
    file_path = f"galleria/{uploaded_file.name}"
    
    # Upload automatico su Supabase Storage
    with st.spinner('Caricamento in corso...'):
        try:
            # Legge i byte del file
            file_bytes = uploaded_file.getvalue()
            
            # Carica nel bucket 'foto_amici'
            res = supabase.storage.from_("foto_amici").upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": uploaded_file.type}
            )
            st.success("Foto caricata con successo!")
        except Exception as e:
            st.error(f"Errore: Forse la foto esiste già?")

# Visualizzazione (Logica per mostrare le foto caricate)
st.divider()
st.subheader("Le nostre foto")

# Qui andrebbe la logica per leggere i file dal bucket e mostrarli
# Per ora simuliamo una griglia
