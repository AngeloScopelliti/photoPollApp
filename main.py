import streamlit as st

st.title("📸 La nostra Galleria Privata")

# Caricamento
uploaded_file = st.file_uploader("Scegli una foto", type=['jpg', 'png'])

# Visualizzazione e Voto (Esempio semplificato)
st.image("foto_esempio.jpg", caption="Scattata da Marco")
if st.button("Vota questa foto! 👍"):
    st.write("Grazie per il voto!")