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

# --- POŁĄCZENIE I ŁADOWANIE DANYCH ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczyt danych z Google Sheets
        existing_data = conn.read(ttl=0)
        
        # Jeśli arkusz jest pusty lub ma błąd odczytu (np. same 'Unnamed')
        if existing_data.empty or "Unnamed: 0" in existing_data.columns:
            raise ValueError("Arkusz jest pusty")
            
        # Ustawiamy pierwszą kolumnę jako indeks (daty)
        existing_data.set_index(existing_data.columns[0], inplace=True)
        return existing_data
    except Exception:
        # TWORZENIE NOWEJ TABELI, gdy arkusz jest pusty
        new_df = pd.DataFrame("?", index=DNI_TYGODNIA, columns=OSOBY)
        return new_df

# Ładujemy dane
df = load_data()

# --- POPRAWKA WYŚWIETLANIA ---
# Streamlit czasami gubi nazwy indeksu przy eksporcie, wymuszamy je:
df.index.name = "Dzień (Data)"

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
    key="planer_editor",
    num_rows="fixed" # Blokuje usuwanie/dodawanie wierszy przez użytkowników
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

