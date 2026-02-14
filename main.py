import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import altair as alt

# KONFIGURACJA
OSOBY = ["Błażej", "Krzyztof", "Magda", "Norbert", "Paulina", "Przemek"]
OPCJE = ["?", "pasażer", "kierowca", "nie jadę"]
PUNKTY = {"pasażer": 1, "kierowca": 2, "nie jadę": 0, "?": 0}

conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Planer Dojazdów", layout="wide")

# LOGIKA DAT
def get_monday_of_week():
    today = datetime.now()
    # Odświeżanie w sobotę rano: jeśli dziś >= sobota (5), bierzemy przyszły poniedziałek
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
        # ttl=0 wyłącza buforowanie, aby widzieć zmiany od razu
        return conn.read(ttl=0)
    except:
        return pd.DataFrame(columns=["Data_Week", "Dzien", "Osoba", "Wybor"])


def save_to_sheets(df_current, full_history):
    # Czyścimy stare wpisy dla tego tygodnia
    updated_history = full_history[full_history['Data_Week'] != start_monday_str]

    new_rows = []
    for day in df_current.index:
        for osoba in OSOBY:
            new_rows.append({
                "Data_Week": start_monday_str,
                "Dzien": day,
                "Osoba": osoba,
                "Wybor": df_current.at[day, osoba]
            })

    final_df = pd.concat([updated_history, pd.DataFrame(new_rows)], ignore_index=True)
    conn.update(data=final_df)
    st.cache_data.clear()


# SESJA I INTERFEJS
db = load_data()
current_week_data = db[db['Data_Week'] == start_monday_str]

# Przygotowanie tabeli do wyświetlenia
if current_week_data.empty:
    df_display = pd.DataFrame("?", index=dni_tygodnia, columns=OSOBY)
else:
    df_display = current_week_data.pivot(index='Dzien', columns='Osoba', values='Wybor').reindex(dni_tygodnia)
    for osoba in OSOBY:
        if osoba not in df_display.columns:
            df_display[osoba] = '?'
    df_display = df_display[OSOBY]


# GRATULACJE (System rekordów)
stats = db.copy()
stats['Pkt'] = stats['Wybor'].map(PUNKTY)
total_points = stats.groupby('Osoba')['Pkt'].sum()

if not total_points.empty:
    user1_pts = total_points.get(OSOBY[0], 0)
    if user1_pts >= 50:
        threshold = (user1_pts // 50) * 50
        st.balloons()
        st.success(f"🎊 Gratulacje @{OSOBY[0]}! Jako pierwszy zebrałeś {threshold} pkt!")

st.title("🚗 Planer Dojazdów")

# TABELA (Menu kontekstowe / Dropdown)
st.subheader(f"Plan na tydzień: {dni_tygodnia[0]} - {dni_tygodnia[-1]}")
edited_df = st.data_editor(
    df_display,
    column_config={osoba: st.column_config.SelectboxColumn(options=OPCJE) for osoba in OSOBY},
    use_container_width=True
)

if st.button("Zapisz zmiany"):
    save_to_sheets(edited_df, db)
    st.rerun()

# WYKRESY
col1, col2 = st.columns(2)

with col1:
    st.subheader("Suma punktów (Ranking)")
    # Upewniamy się, że wszystkie osoby są w rankingu (nawet z 0 pkt)
    full_points = total_points.reindex(OSOBY, fill_value=0).reset_index()
    full_points.columns = ['Osoba', 'Punkty']

    chart1 = alt.Chart(full_points).mark_bar().encode(
        x=alt.X('Osoba:N', sort=None, title=None),  # Usunięcie "Osoba" z osi X
        y=alt.Y('Punkty:Q', title=None),  # Usunięcie "Punkty" z osi Y
        color=alt.value("#1f77b4")
    ).properties(height=300)

    st.altair_chart(chart1, use_container_width=True)

with col2:
    st.subheader("Licznik roli 'Kierowca'")
    # Licznik kierowców
    driver_counts = db[db['Wybor'] == "kierowca"].groupby('Osoba').size().reindex(OSOBY, fill_value=0).reset_index()
    driver_counts.columns = ['Osoba', 'Ilość']

    chart2 = alt.Chart(driver_counts).mark_bar().encode(
        x=alt.X('Osoba:N', sort=None, title=None),  # Usunięcie "Osoba" z osi X
        y=alt.Y('Ilość:Q', title=None),  # Usunięcie "Ilość" z osi Y
        color=alt.value("#ff7f0e")
    ).properties(height=300)

    st.altair_chart(chart2, use_container_width=True)
