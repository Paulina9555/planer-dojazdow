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
        response = requests.get(APPS_SCRIPT_URL, allow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            if not data or len(data) == 0:
                return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])
            
            df = pd.DataFrame(data)
            # KLUCZOWA POPRAWKA: Czyszczenie nazw kolumn i danych z ukrytych spacji
            df.columns = df.columns.str.strip()
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            return df
    except Exception as e:
        st.error(f"Błąd odczytu z Google Sheets: {e}")
    return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])

def save_to_sheets(edited_df, full_db):
    try:
        # 1. Przekształcenie tabeli z edytora na format bazy danych
        temp_df = edited_df.reset_index().rename(columns={'index': 'Dzien'})
        new_entries = temp_df.melt(id_vars=['Dzien'], var_name='Osoba', value_name='Wybor')
        new_entries['Data_Week'] = start_monday_str
        
        # 2. Łączenie z historią (zachowanie innych tygodni)
        if not full_db.empty:
            # Usuwamy tylko wpisy z obecnego tygodnia, by je zastąpić nowymi
            full_db = full_db[full_db['Data_Week'] != start_monday_str]
        
        updated_db = pd.concat([full_db, new_entries], ignore_index=True)
        
        # 3. Wysyłka do Google
        json_payload = json.dumps(updated_db.to_dict(orient='records'))
        with st.spinner('Zapisywanie w arkuszu...'):
            response = requests.post(APPS_SCRIPT_URL, data=json_payload, allow_redirects=True)
        
        if response.status_code == 200:
            st.success("✅ Dane zostały trwale zapisane!")
            st.rerun()
        else:
            st.error("Serwer Google zwrócił błąd przy zapisie.")
    except Exception as e:
        st.error(f"⚠️ Wystąpił błąd: {e}")

# INTERFEJS
db = load_data()

# Filtrowanie danych na obecny tydzień
current_week_data = db[db['Data_Week'] == start_monday_str]

if current_week_data.empty:
    # Jeśli nie ma danych w Google Sheets na ten tydzień, twórz pustą tabelę
    df_display = pd.DataFrame("?", index=dni_tygodnia, columns=OSOBY)
else:
    # Tworzenie widoku tabeli z pobranych danych
    df_display = current_week_data.pivot(index='Dzien', columns='Osoba', values='Wybor')
    # Reindex zapewnia, że dni i osoby są w dobrej kolejności, nawet jeśli ktoś nie wypełnił wszystkiego
    df_display = df_display.reindex(index=dni_tygodnia, columns=OSOBY, fill_value="?")

st.title("🚗 Planer Dojazdów")
st.subheader(f"Plan na tydzień: {dni_tygodnia[0]} do {dni_tygodnia[-1]}")

# EDYTOR
edited_df = st.data_editor(
    df_display,
    column_config={osoba: st.column_config.SelectboxColumn(options=OPCJE) for osoba in OSOBY},
    use_container_width=True,
    key="editor" # Dodanie klucza pomaga Streamlitowi trzymać stan
)

if st.button("💾 Zapisz zmiany w Google Sheets"):
    save_to_sheets(edited_df, db)

# STATYSTYKI (Bez zmian w wyglądzie wykresów)
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





