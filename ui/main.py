import streamlit as st
import requests

st.set_page_config(page_title="AI Core", layout="wide")
st.title("🔥 AI Core – Dein lokales KI-Betriebssystem")
st.success("15/15 Phasen abgeschlossen")

with st.sidebar:
    st.header("System Status")
    st.write("Gateway: http://localhost:10010")
    st.write("UI: http://localhost:8000")
    st.write("Model: 4B Instruct bereit")

message = st.chat_input("Schreib hier deine Nachricht...")

if message:
    with st.chat_message("user"):
        st.write(message)
    with st.chat_message("assistant"):
        with st.spinner("Josie denkt..."):
            try:
                resp = requests.post("http://localhost:10010/chat", json={"message": message})
                st.write(resp.json()["response"])
            except:
                st.error("Gateway nicht erreichbar – ist er gestartet?")