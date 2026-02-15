import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text  # DODAJ TO

# ... (reszta kodu bez zmian do momentu bazy danych) ...

# --- BAZA DANYCH ---
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        # Używamy text(), aby SQLAlchemy zaakceptowało surowy SQL
        s.execute(text('CREATE TABLE IF NOT EXISTS planer (dzien TEXT PRIMARY KEY, dane JSONB);'))
        s.commit()

def load_data():
    try:
        # Odczyt danych
        df_db = conn.query("SELECT * FROM planer", ttl=0)
        if df_db is None or df_db.empty:
            return pd.DataFrame("?", index=DNI, columns=OSOBY)
        
        current_data = {osoba: [] for osoba in OSOBY}
        for d in DNI:
            # Szukamy wiersza dla konkretnej daty
            row = df_db[df_db['dzien'] == d]
            if not row.empty:
                # W Pandas dane JSONB mogą być słownikiem lub stringiem
                saved_vals = row.iloc[0]['dane']
                if isinstance(saved_vals, str):
                    import json
                    saved_vals = json.loads(saved_vals)
                
                for o in OSOBY:
                    current_data[o].append(saved_vals.get(o, "?"))
            else:
                for o in OSOBY:
                    current_data[o].append("?")
        return pd.DataFrame(current_data, index=DNI)
    except Exception as e:
        # W razie błędu (np. nowa baza) pokazujemy czystą tabelę
        return pd.DataFrame("?", index=DNI, columns=OSOBY)

init_db()
df = load_data()

# --- EDYCJA I ZAPIS ---
config = {o: st.column_config.SelectboxColumn(o, options=OPCJE, width="medium") for o in OSOBY}
edited_df = st.data_editor(df, column_config=config, use_container_width=True)

if st.button("Zapisz zmiany dla wszystkich"):
    with conn.session as s:
        for index, row in edited_df.iterrows():
            json_val = row.to_json()
            # Tutaj również używamy text() i parametrów z dwukropkiem
            query = text('INSERT INTO planer (dzien, dane) VALUES (:d, :j) ON CONFLICT (dzien) DO UPDATE SET dane = :j')
            s.execute(query, {"d": index, "j": json_val})
        s.commit()
    st.success("Zapisano pomyślnie!")
    st.rerun()

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

