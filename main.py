import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACJA ---
st.set_page_config(page_title="Planer Dojazdów", layout="wide")
st.title("🚗 Planer Dojazdów")

OSOBY = ["Błażej", "Krzysztof", "Magda", "Norbert", "Paulina", "Przemek"]
OPCJE = ["?", "kierowca", "pasażer", "nie jadę"]

# --- GENEROWANIE DAT ---
def get_current_week_dates():
    today = datetime.now()
    # Jeśli sobota/niedziela -> następny tydzień, inaczej obecny
    start_day = today + timedelta(days=(7-today.weekday())) if today.weekday() >= 5 else today - timedelta(days=today.weekday())
    dni = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
    return [f"{dni[i]} ({(start_day + timedelta(days=i)).strftime('%d.%m')})" for i in range(5)]

DNI_TYGODNIA = get_current_week_dates()

# --- PROSTA OBSŁUGA DANYCH (Public CSV) ---
# Używamy triku z exportem do CSV, który nie wymaga logowania
SHEET_URL = st.secrets["gsheets"]["spreadsheet"]
CSV_URL = SHEET_URL.replace("/edit#gid=", "/export?format=csv&gid=")

def load_data():
    try:
        # Odczytujemy dane bezpośrednio z linku CSV
        return pd.read_csv(CSV_URL, index_col=0)
    except:
        return pd.DataFrame("?", index=DNI_TYGODNIA, columns=OSOBY)

# --- WYŚWIETLANIE ---
df = load_data()

config = {o: st.column_config.SelectboxColumn(o, options=OPCJE, width="medium") for o in OSOBY}

st.write("Wybierz status i kliknij przycisk na dole, aby zapisać.")
edited_df = st.data_editor(df, column_config=config, use_container_width=True)

# Funkcja kolorowania dla podglądu
def color_cells(val):
    colors = {"kierowca": "#1E90FF", "pasażer": "#2E8B57", "nie jadę": "#B22222"}
    return f"background-color: {colors.get(val, '#808080')}; color: white;"

if st.button("Zapisz zmiany"):
    # UWAGA: Bez plików JSON zapisywanie bezpośrednio ze Streamlit jest trudne.
    # Wyświetlę instrukcję, jeśli zapis się nie powiedzie.
    st.info("Aby zapisać zmiany na stałe bez plików JSON, musisz udostępnić arkusz jako 'Edytor' dla każdego.")
    # Tutaj możesz dodać link do arkusza, żeby użytkownik mógł go otworzyć i tam wpisać
    st.markdown(f"[KLIKNIJ TUTAJ, ABY OTWORZYĆ ARKUSZ I ZAPISAĆ]({SHEET_URL})")

st.markdown("---")
st.subheader("Aktualny podgląd (kolory):")
st.table(edited_df.style.applymap(color_cells))
