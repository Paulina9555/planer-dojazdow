import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
import altair as alt

# KONFIGURACJA
OSOBY = ["Błażej", "Krzyztof", "Magda", "Norbert", "Paulina", "Przemek"]
OPCJE = ["?", "pasażer", "kierowca", "nie jadę"]
PUNKTY = {"pasażer": 1, "kierowca": 2, "nie jadę": 0, "?": 0}
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZDyJOQ--kF__8RZmjP_Qh82_sAhnZkklJX4-bQwRmlkt4KtMtREZLQLZf9i0RBYde/exec"

st.set_page_config(page_title="Planer Dojazdów", layout="wide")

# LOGIKA DAT
def get_monday_of_week():
    today = datetime.now()
    if today.weekday() >= 5: 
        target_monday = today + timedelta(days=(7 - today.weekday()))
    else:
        target_monday = today - timedelta(days=today.weekday())
    return target_monday.replace(hour=0, minute=0, second=0, microsecond=0)

start_monday = get_monday_of_week()
start_monday_str = start_monday.strftime('%Y-%m-%d')
dni_tygodnia = [(start_monday + timedelta(days=i)).strftime('%Y-%m-%d (%A)') for i in range(5)]

def load_data():
    try:
        # Dodajemy timestamp aby uniknąć cache'owania przez przeglądarkę/Google
        res = requests.get(f"{APPS_SCRIPT_URL}?t={datetime.now().timestamp()}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Błąd pobierania: {e}")
    return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])

# --- INICJALIZACJA DANYCH ---
if "db" not in st.session_state:
    loaded_db = load_data()
    # Jeśli baza jest pusta, stwórz szkielet, aby uniknąć KeyError
    if loaded_db.empty:
        st.session_state.db = pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])
    else:
        st.session_state.db = loaded_db

db = st.session_state.db

# Bezpieczne filtrowanie - sprawdź czy kolumna istnieje
if not db.empty and "Data_Week" in db.columns:
    current_week_df = db[db['Data_Week'] == start_monday_str]
else:
    current_week_df = pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])

# Przygotowanie widoku dla bieżącego tygodnia
db = st.session_state.db
current_week_df = db[db['Data_Week'] == start_monday_str]

# Budujemy tabelę do edycji (zawsze 5 dni x liczba osób)
if current_week_df.empty:
    df_display = pd.DataFrame("?", index=dni_tygodnia, columns=OSOBY)
else:
    df_display = current_week_df.pivot(index='Dzien', columns='Osoba', values='Wybor')
    df_display = df_display.reindex(index=dni_tygodnia, columns=OSOBY, fill_value="?")

# --- INTERFEJS ---
st.title("🚗 Planer Dojazdów")
st.subheader(f"Tydzień: {start_monday_str}")

edited_df = st.data_editor(
    df_display,
    column_config={osoba: st.column_config.SelectboxColumn(options=OPCJE) for osoba in OSOBY},
    use_container_width=True
)

if st.button("💾 Zapisz zmiany dla wszystkich"):
    with st.spinner("Synchronizacja z Google Sheets..."):
        # 1. Przekształć edytowaną tabelę na format listy wierszy
        temp_df = edited_df.reset_index().rename(columns={'index': 'Dzien'})
        new_data_to_send = temp_df.melt(id_vars=['Dzien'], var_name='Osoba', value_name='Wybor')
        new_data_to_send['Data_Week'] = start_monday_str
        
        # 2. Wyślij do Google Apps Script
        payload = {
            "week": start_monday_str,
            "data": new_data_to_send.to_dict(orient='records')
        }
        
        try:
            response = requests.post(APPS_SCRIPT_URL, data=json.dumps(payload))
            if response.status_code == 200:
                st.success("Zapisano pomyślnie!")
                st.session_state.db = load_data() # Odśwież lokalną kopię
                st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

# --- STATYSTYKI (na podstawie całej bazy db) ---
if not st.session_state.db.empty:
    st.divider()
    all_data = st.session_state.db.copy()
    all_data['Pkt'] = all_data['Wybor'].map(PUNKTY).fillna(0)
    
    stats = all_data.groupby('Osoba')['Pkt'].sum().reindex(OSOBY, fill_value=0).reset_index()
    
    chart = alt.Chart(stats).mark_bar().encode(
        x='Osoba',
        y='Pkt',
        color=alt.value("#1f77b4")
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)








