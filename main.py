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

# ODCZYT I ZAPIS GOOGLE SHEETS
def load_data():
    try:
        # Dodajemy parametr 'nocache', aby wymusić na Google Apps Script świeże dane
        url = f"{APPS_SCRIPT_URL}?nocache={datetime.now().timestamp()}"
        response = requests.get(url, allow_redirects=True, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if not data:
                return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])
            
            df = pd.DataFrame(data)
            df.columns = df.columns.str.strip()
            # Ważne: usuwamy duplikaty, zostawiając ostatni wpis dla danej osoby w danym dniu
            df = df.drop_duplicates(subset=['Data_Week', 'Dzien', 'Osoba'], keep='last')
            return df
    except Exception as e:
        st.error(f"Błąd połączenia z bazą: {e}")
    return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])

def save_to_sheets(edited_df, full_db):
    try:
        # Przygotowanie nowych danych z edytora
        temp_df = edited_df.reset_index().rename(columns={'index': 'Dzien'})
        new_entries = temp_df.melt(id_vars=['Dzien'], var_name='Osoba', value_name='Wybor')
        new_entries['Data_Week'] = start_monday_str
        
        # Łączymy stare dane z nowymi
        if not full_db.empty:
            # Usuwamy z bazy stare wpisy dla BIEŻĄCEGO tygodnia, by zastąpić je nowymi
            updated_db = full_db[full_db['Data_Week'] != start_monday_str].copy()
            updated_db = pd.concat([updated_db, new_entries], ignore_index=True)
        else:
            updated_db = new_entries

        json_payload = json.dumps(updated_db.to_dict(orient='records'))
        
        # Wysłanie danych
        response = requests.post(APPS_SCRIPT_URL, data=json_payload, allow_redirects=True)
        if response.status_code == 200:
            st.success("✅ Dane zapisane w Google Sheets!")
            # Czyścimy cache i wymuszamy odświeżenie
            st.cache_data.clear()
            st.rerun()
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")

# --- POCZĄTEK LOGIKI INTERFEJSU ---
db = load_data()

# Filtrowanie danych na obecny tydzień
current_week_data = db[db['Data_Week'].astype(str) == start_monday_str]

if current_week_data.empty:
    df_display = pd.DataFrame("?", index=dni_tygodnia, columns=OSOBY)
else:
    # Odbudowanie widoku tabeli
    df_display = current_week_data.pivot(index='Dzien', columns='Osoba', values='Wybor')
    # Reindexacja, aby zachować kolejność dni i osób, nawet jeśli brakuje danych w Sheets
    df_display = df_display.reindex(index=dni_tygodnia, columns=OSOBY, fill_value="?")

st.title("🚗 Planer Dojazdów")
st.subheader(f"Plan na tydzień: {dni_tygodnia[0]} do {dni_tygodnia[-1]}")

# DATA EDITOR
# Używamy st.session_state, aby tabela nie czyściła się podczas klikania innych elementów
if "editor_key" not in st.session_state:
    st.session_state.editor_key = 0

edited_df = st.data_editor(
    df_display,
    column_config={osoba: st.column_config.SelectboxColumn(options=OPCJE) for osoba in OSOBY},
    use_container_width=True,
    key=f"plan_editor_{st.session_state.editor_key}"
)

if st.button("💾 Zapisz i odśwież"):
    save_to_sheets(edited_df, db)
    st.session_state.editor_key += 1 # Wymusza odświeżenie widżetu nowymi danymi
    st.rerun()
    
# STATYSTYKI
if not db.empty:
    st.divider()
    stats = db.copy()
    stats['Pkt'] = stats['Wybor'].map(PUNKTY)
    
    total_points = stats.groupby('Osoba')['Pkt'].sum().reindex(OSOBY, fill_value=0).reset_index()
    total_points.columns = ['Osoba', 'Punkty']

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Ranking Punktowy")
        chart1 = alt.Chart(total_points).mark_bar().encode(
            x=alt.X('Osoba:N', sort=None, title=None),
            y=alt.Y('Punkty:Q', title=None),
            color=alt.value("#1f77b4")
        ).properties(height=300)
        st.altair_chart(chart1, use_container_width=True)

    with col2:
        st.subheader("Licznik roli 'Kierowca'")
        driver_counts = db[db['Wybor'] == "kierowca"].groupby('Osoba').size().reindex(OSOBY, fill_value=0).reset_index()
        driver_counts.columns = ['Osoba', 'Ilość']
        
        chart2 = alt.Chart(driver_counts).mark_bar().encode(
            x=alt.X('Osoba:N', sort=None, title=None),
            y=alt.Y('Ilość:Q', title=None),
            color=alt.value("#ff7f0e")
        ).properties(height=300)
        st.altair_chart(chart2, use_container_width=True)









