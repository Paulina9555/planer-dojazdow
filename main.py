import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
import altair as alt

# --- KONFIGURACJA ---
OSOBY = ["Błażej", "Krzyztof", "Magda", "Norbert", "Paulina", "Przemek"]
OPCJE = ["?", "pasażer", "kierowca", "nie jadę"]
PUNKTY = {"pasażer": 1, "kierowca": 2, "nie jadę": 0, "?": 0}
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZDyJOQ--kF__8RZmjP_Qh82_sAhnZkklJX4-bQwRmlkt4KtMtREZLQLZf9i0RBYde/exec"

st.set_page_config(page_title="Planer Dojazdów", layout="wide")

# --- LOGIKA DAT ---
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

# --- KOMUNIKACJA Z GOOGLE SHEETS ---
def load_data():
    try:
        url = f"{APPS_SCRIPT_URL}?t={datetime.now().timestamp()}"
        response = requests.get(url, allow_redirects=True, timeout=15)
        
        # Jeśli Google zwróci błąd 401/404/500
        if response.status_code != 200:
            st.error(f"Google zwrócił błąd HTTP: {response.status_code}")
            return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])

        # Próba odczytu JSON
        try:
            data = response.json()
            df = pd.DataFrame(data)
            if not df.empty:
                df.columns = df.columns.str.strip()
                return df
        except Exception:
            # Jeśli to nie JSON, pokaż co to jest (np. błąd HTML)
            st.warning("Otrzymano nieprawidłowy format danych z Google. Sprawdź wdrożenie skryptu.")
            # st.write(response.text) # Opcjonalnie: odkomentuj, żeby zobaczyć treść błędu
            
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
    return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])

# --- GŁÓWNA LOGIKA DANYCH ---
db = load_data()

# Przygotowanie widoku tabeli dla bieżącego tygodnia
current_week_data = db[db['Data_Week'].astype(str) == start_monday_str]

if not current_week_data.empty:
    # Usuwamy duplikaty przed pivotem (zostawiamy ostatni wybór)
    clean_data = current_week_data.drop_duplicates(subset=['Dzien', 'Osoba'], keep='last')
    df_display = clean_data.pivot(index='Dzien', columns='Osoba', values='Wybor')
    df_display = df_display.reindex(index=dni_tygodnia, columns=OSOBY, fill_value="?")
else:
    df_display = pd.DataFrame("?", index=dni_tygodnia, columns=OSOBY)

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("🚗 Planer Dojazdów")
st.subheader(f"Tydzień: {start_monday_str}")

# Edytor danych
edited_df = st.data_editor(
    df_display,
    column_config={osoba: st.column_config.SelectboxColumn(options=OPCJE) for osoba in OSOBY},
    use_container_width=True
)

if st.button("💾 Zapisz i synchronizuj"):
    with st.spinner("Zapisywanie danych..."):
        # Przygotowanie danych do wysyłki
        temp_df = edited_df.reset_index().rename(columns={'index': 'Dzien'})
        new_entries = temp_df.melt(id_vars=['Dzien'], var_name='Osoba', value_name='Wybor')
        new_entries['Data_Week'] = start_monday_str
        
        # Paczka danych dla Google Script (aktualizujemy TYLKO bieżący tydzień)
        payload = {
            "week": start_monday_str,
            "data": new_entries.to_dict(orient='records')
        }
        
        try:
            res = requests.post(APPS_SCRIPT_URL, data=json.dumps(payload), timeout=15)
            if res.status_code == 200:
                st.success("✅ Zapisano pomyślnie!")
                st.rerun() # Wymusza pobranie nowych danych z Google
            else:
                st.error(f"Serwer zwrócił błąd: {res.status_code}")
        except Exception as e:
            st.error(f"Błąd wysyłania: {e}")

# --- STATYSTYKI ---
if not db.empty and 'Wybor' in db.columns:
    st.divider()
    st.subheader("Statystyki ogólne (Wszystkie tygodnie)")
    
    # Kopiujemy bazę do statystyk i mapujemy punkty
    stats_data = db.copy()
    stats_data['Pkt'] = stats_data['Wybor'].map(PUNKTY).fillna(0)
    
    # Agregacja punktów
    total_points = stats_data.groupby('Osoba')['Pkt'].sum().reindex(OSOBY, fill_value=0).reset_index()
    total_points.columns = ['Osoba', 'Suma Punktów']

    col1, col2 = st.columns(2)
    
    with col1:
        chart1 = alt.Chart(total_points).mark_bar().encode(
            x=alt.X('Osoba:N', sort=None),
            y='Suma Punktów:Q',
            color=alt.value("#1f77b4")
        ).properties(height=300)
        st.altair_chart(chart1, use_container_width=True)

    with col2:
        # Licznik roli kierowcy
        drivers = stats_data[stats_data['Wybor'] == "kierowca"].groupby('Osoba').size().reindex(OSOBY, fill_value=0).reset_index()
        drivers.columns = ['Osoba', 'Liczba kursów']
        
        chart2 = alt.Chart(drivers).mark_bar().encode(
            x=alt.X('Osoba:N', sort=None),
            y='Liczba kursów:Q',
            color=alt.value("#ff7f0e")
        ).properties(height=300)
        st.altair_chart(chart2, use_container_width=True)











