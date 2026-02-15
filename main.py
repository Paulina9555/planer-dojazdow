import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACJA ---
st.set_page_config(page_title="Planer Dojazdów", layout="wide")
st.title("🚗 Planer Dojazdów")

OSOBY = ["Błażej", "Krzysztof", "Magda", "Norbert", "Paulina", "Przemek"]
OPCJE = ["?", "kierowca", "pasażer", "nie jadę"]

# --- FUNKCJA DATY ---
def get_current_week_dates():
    today = datetime.now()
    # Jeśli jest sobota (5) lub niedziela (6), celujemy w przyszły tydzień
    # W pozostałe dni pokazujemy obecny tydzień roboczy
    if today.weekday() >= 5:
        start_monday = today + timedelta(days=(7 - today.weekday()))
    else:
        start_monday = today - timedelta(days=today.weekday())
    
    dni = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
    return [f"{dni[i]} ({(start_monday + timedelta(days=i)).strftime('%d.%m')})" for i in range(5)]

DNI_TYGODNIA = get_current_week_dates()

# --- POŁĄCZENIE Z BAZĄ (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Próba odczytu istniejących danych
        return conn.read(ttl=0)
    except:
        # Jeśli arkusz pusty, stwórz szkielet
        df = pd.DataFrame("?", index=DNI_TYGODNIA, columns=OSOBY)
        return df

df = load_data()

# --- STYLIZACJA ---
def color_cells(val):
    if val == "kierowca": return "background-color: #1E90FF; color: white;" # Niebieski
    if val == "pasażer": return "background-color: #2E8B57; color: white;"  # Zielony
    if val == "nie jadę": return "background-color: #B22222; color: white;" # Czerwony
    return "background-color: #808080; color: white;" # Szary dla "?"

# --- EDYCJA ---
st.write("Kliknij w komórkę, aby zmienić status. Zmiany zostaną zapisane dla wszystkich.")

config = {
    osoba: st.column_config.SelectboxColumn(osoba, options=OPCJE, width="medium") 
    for osoba in OSOBY
}

# Wyświetlanie edytora
edited_df = st.data_editor(
    df,
    column_config=config,
    use_container_width=True,
    key="planer_editor"
)

# --- ZAPIS ---
if st.button("Zapisz zmiany i odśwież u innych"):
    conn.update(data=edited_df)
    st.success("Zapisano pomyślnie!")
    st.rerun()

# --- WIDOK TYLKO DO ODCZYTU ZE STYLAMI ---
st.markdown("---")
st.subheader("Aktualny podgląd (kolory):")
styled_df = edited_df.style.applymap(color_cells)
st.table(styled_df)
