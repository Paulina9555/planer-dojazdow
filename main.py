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

# FUNKCJA POBIERANIA
def load_data():
    try:
        url = f"{APPS_SCRIPT_URL}?t={datetime.now().timestamp()}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            if not df.empty:
                df.columns = df.columns.str.strip()
                return df
    except Exception as e:
        st.error(f"Błąd pobierania: {e}")
    return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])

# Załaduj dane zawsze na początku
db = load_data()

# Filtrowanie na obecny tydzień
current_week_data = db[db['Data_Week'].astype(str) == start_monday_str]

# BUDOWANIE TABELI
if not current_week_data.empty:
    clean_data = current_week_data.drop_duplicates(subset=['Dzien', 'Osoba'], keep='last')
    df_display = clean_data.pivot(index='Dzien', columns='Osoba', values='Wybor')
    df_display = df_display.reindex(index=dni_tygodnia, columns=OSOBY, fill_value="?")
else:
    df_display = pd.DataFrame("?", index=dni_tygodnia, columns=OSOBY)

# INTERFEJS
st.title("🚗 Planer Dojazdów")

edited_df = st.data_editor(
    df_display,
    column_config={osoba: st.column_config.SelectboxColumn(options=OPCJE) for osoba in OSOBY},
    use_container_width=True
)

if st.button("💾 Zapisz i odśwież"):
    # Przygotowanie danych do zapisu
    temp_df = edited_df.reset_index().rename(columns={'index': 'Dzien'})
    new_entries = temp_df.melt(id_vars=['Dzien'], var_name='Osoba', value_name='Wybor')
    new_entries['Data_Week'] = start_monday_str
    
    # Wysyłamy tylko dane z tego tygodnia do synchronizacji
    payload = {"week": start_monday_str, "data": new_entries.to_dict(orient='records')}
    
    res = requests.post(APPS_SCRIPT_URL, data=json.dumps(payload))
    if res.status_code == 200:
        st.cache_data.clear() # Czyścimy cache Streamlit
        st.success("✅ Zsynchronizowano!")
        st.rerun() # Wymuszamy przeładowanie całego skryptu

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









