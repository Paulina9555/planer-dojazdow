import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
import json

# --- 1. STAŁE I KONFIGURACJA (Muszą być na początku!) ---
st.set_page_config(page_title="Planer Dojazdów", layout="wide")
st.title("🚗 Planer Dojazdów")

OSOBY = ["Błażej", "Krzysztof", "Magda", "Norbert", "Paulina", "Przemek"]
OPCJE = ["?", "kierowca", "pasażer", "nie jadę"]

# Funkcja generująca daty - zdefiniowana przed użyciem
def get_current_week_dates():
    today = datetime.now()
    # Logika sobotnia: jeśli sobota(5) lub niedziela(6) -> następny tydzień
    if today.weekday() >= 5:
        start_monday = today + timedelta(days=(7 - today.weekday()))
    else:
        start_monday = today - timedelta(days=today.weekday())
    
    dni_nazwy = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
    return [f"{dni_nazwy[i]} ({(start_monday + timedelta(days=i)).strftime('%d.%m')})" for i in range(5)]

# Definiujemy DNI jako zmienną globalną
DNI = get_current_week_dates()

# --- 2. BAZA DANYCH ---
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        s.execute(text('CREATE TABLE IF NOT EXISTS planer (dzien TEXT PRIMARY KEY, dane JSONB);'))
        s.commit()

def load_data():
    try:
        # Pobieramy dane z bazy
        df_db = conn.query("SELECT * FROM planer", ttl=0)
        
        # Jeśli baza jest pusta, zwróć czysty arkusz
        if df_db is None or df_db.empty:
            return pd.DataFrame("?", index=DNI, columns=OSOBY)
        
        # Przygotowanie danych do wyświetlenia
        current_data = {osoba: [] for osoba in OSOBY}
        for d in DNI:
            row = df_db[df_db['dzien'] == d]
            if not row.empty:
                # Wyciągamy dane JSON
                saved_vals = row.iloc[0]['dane']
                # Jeśli baza zwróciła string zamiast słownika, parsujemy go
                if isinstance(saved_vals, str):
                    saved_vals = json.loads(saved_vals)
                
                for o in OSOBY:
                    current_data[o].append(saved_vals.get(o, "?"))
            else:
                for o in OSOBY:
                    current_data[o].append("?")
        
        return pd.DataFrame(current_data, index=DNI)
    except Exception as e:
        # W razie jakiegokolwiek błędu zwracamy pustą tabelę
        return pd.DataFrame("?", index=DNI, columns=OSOBY)

# --- 3. LOGIKA APLIKACJI ---
init_db()
df_to_edit = load_data()

# Konfiguracja kolumn dla edytora
column_config = {o: st.column_config.SelectboxColumn(o, options=OPCJE, width="medium") for o in OSOBY}

st.write("Wybierz status i kliknij przycisk poniżej, aby zapisać zmiany dla wszystkich.")

# Edytor tabeli
edited_df = st.data_editor(
    df_to_edit, 
    column_config=column_config, 
    use_container_width=True,
    key="main_editor"
)

# Przycisk zapisu
if st.button("Zapisz zmiany"):
    with conn.session as s:
        for index, row in edited_df.iterrows():
            json_val = row.to_json()
            query = text('INSERT INTO planer (dzien, dane) VALUES (:d, :j) ON CONFLICT (dzien) DO UPDATE SET dane = :j')
            s.execute(query, {"d": index, "j": json_val})
        s.commit()
    st.success("Zapisano pomyślnie!")
    st.rerun()

# --- 4. PODGLĄD Z KOLORAMI ---
def color_cells(val):
    colors = {
        "kierowca": "background-color: #1E90FF; color: white;",
        "pasażer": "background-color: #2E8B57; color: white;",
        "nie jadę": "background-color: #B22222; color: white;",
        "?": "background-color: #808080; color: white;"
    }
    return colors.get(val, "")

st.markdown("---")
st.subheader("Aktualny podgląd (kolory):")
st.table(edited_df.style.applymap(color_cells))
