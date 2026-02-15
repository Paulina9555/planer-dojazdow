import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACJA ---
st.set_page_config(page_title="Planer Dojazdów", layout="wide")
st.title("🚗 Planer Dojazdów")

OSOBY = ["Błażej", "Krzysztof", "Magda", "Norbert", "Paulina", "Przemek"]
OPCJE = ["?", "kierowca", "pasażer", "nie jadę"]

# --- DATY ---
def get_current_week_dates():
    today = datetime.now()
    start_monday = today + timedelta(days=(7-today.weekday())) if today.weekday() >= 5 else today - timedelta(days=today.weekday())
    dni = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
    return [f"{dni[i]} ({(start_monday + timedelta(days=i)).strftime('%d.%m')})" for i in range(5)]

DNI = get_current_week_dates()

# --- BAZA DANYCH (st.connection) ---
# Automatycznie pobiera dane z [connections.postgresql] w Secrets
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        s.execute('CREATE TABLE IF NOT EXISTS planer (dzien TEXT PRIMARY KEY, dane JSONB);')
        s.commit()

def load_data():
    try:
        df_db = conn.query("SELECT * FROM planer", ttl=0)
        if df_db.empty:
            return pd.DataFrame("?", index=DNI, columns=OSOBY)
        
        # Przetwarzanie danych z bazy do formatu tabeli
        current_data = {osoba: [] for osoba in OSOBY}
        for d in DNI:
            row = df_db[df_db['dzien'] == d]
            saved_vals = row.iloc[0]['dane'] if not row.empty else {}
            for o in OSOBY:
                current_data[o].append(saved_vals.get(o, "?"))
        return pd.DataFrame(current_data, index=DNI)
    except:
        return pd.DataFrame("?", index=DNI, columns=OSOBY)

init_db()
df = load_data()

# --- EDYCJA I KOLORY ---
config = {o: st.column_config.SelectboxColumn(o, options=OPCJE, width="medium") for o in OSOBY}
edited_df = st.data_editor(df, column_config=config, use_container_width=True)

if st.button("Zapisz zmiany dla wszystkich"):
    with conn.session as s:
        for index, row in edited_df.iterrows():
            json_val = row.to_json()
            s.execute(
                'INSERT INTO planer (dzien, dane) VALUES (:d, :j) ON CONFLICT (dzien) DO UPDATE SET dane = :j',
                {"d": index, "j": json_val}
            )
        s.commit()
    st.success("Zapisano!")
    st.rerun()

def color_cells(val):
    colors = {"kierowca": "#1E90FF", "pasażer": "#2E8B57", "nie jadę": "#B22222"}
    return f"background-color: {colors.get(val, '#808080')}; color: white;"

st.markdown("---")
st.table(edited_df.style.applymap(color_cells))
lor_cells))

