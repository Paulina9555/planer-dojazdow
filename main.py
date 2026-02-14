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
        # Dodanie timestampu do URL zapobiega problemom na telefonach
        url = f"{APPS_SCRIPT_URL}?t={datetime.now().timestamp()}"
        response = requests.get(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            if not df.empty:
                df.columns = df.columns.str.strip()
                return df
    except Exception as e:
        st.error(f"Błąd połączenia z bazą: {e}")
    # Zwraca pusty DataFrame ze strukturą, jeśli baza nie odpowie
    return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])

# 2. INICJALIZACJA I POBIERANIE DANYCH
# Pobieramy dane bezpośrednio do zmiennej lokalnej przy każdym uruchomieniu skryptu
db = load_data()

# 3. FILTROWANIE I BUDOWANIE TABELI
current_week_data = db[db['Data_Week'].astype(str) == start_monday_str]

if not current_week_data.empty:
    # Usuwamy duplikaty, by pivot się nie wywalił
    clean_data = current_week_data.drop_duplicates(subset=['Dzien', 'Osoba'], keep='last')
    df_display = clean_data.pivot(index='Dzien', columns='Osoba', values='Wybor')
    df_display = df_display.reindex(index=dni_tygodnia, columns=OSOBY, fill_value="?")
else:
    df_display = pd.DataFrame("?", index=dni_tygodnia, columns=OSOBY)

# --- STATYSTYKI (na podstawie całej bazy db) ---
if db is not None and not db.empty:
    st.divider()
    stats_df = db.copy()
    # Upewnij się, że kolumna istnieje przed mapowaniem
    if 'Wybor' in stats_df.columns:
        stats_df['Pkt'] = stats_df['Wybor'].map(PUNKTY).fillna(0)
    
    stats = all_data.groupby('Osoba')['Pkt'].sum().reindex(OSOBY, fill_value=0).reset_index()
    
    chart = alt.Chart(stats).mark_bar().encode(
        x='Osoba',
        y='Pkt',
        color=alt.value("#1f77b4")
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)










