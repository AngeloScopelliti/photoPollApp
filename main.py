import streamlit as st
from supabase import create_client
import datetime

# Configurazione connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("📸 La nostra Galleria Privata")

# Tasto per importare le foto
uploaded_file = st.file_uploader("Trascina qui la tua foto o clicca per importare", type=['jpg', 'png', 'jpeg'])

if uploaded_file is not None:
    # 1. Crea un timestamp unico (es: 20231027_153045)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 2. Unisci il timestamp al nome originale
    file_name_unico = f"{timestamp}_{uploaded_file.name}"
    file_path = f"galleria/{file_name_unico}"
    
    with st.spinner('Caricamento in corso...'):
        try:
            file_bytes = uploaded_file.getvalue()
            
            # 3. Usa il nuovo nome file_path
            res = supabase.storage.from_("foto_amici").upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": uploaded_file.type}
            )
            st.success(f"Foto caricata come: {file_name_unico}")
        except Exception as e:
            st.error(f"Errore durante l'upload: {e}")

# Visualizzazione (Logica per mostrare le foto caricate)
st.divider()
st.subheader("Le nostre foto")

# Qui andrebbe la logica per leggere i file dal bucket e mostrarli
# Per ora simuliamo una griglia
