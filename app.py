# app.py — Solo visualización desde archivo local (CSV o XLSX)
import os
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime

# ----------------- Parámetros base -----------------
TEAMS = ["FV1","FV2","FV3","FV4","FV5","FV6"]
ACTIVITIES = [
    "Fecha 1 y 2 (01-05/09)",
    "Fecha 3 (08/09)",
    "Fecha 4 (12/09)",
    "Fecha 5 (15/09)",
    "Fecha 6 (19/09)",
]
CANDIDATE_PATHS = ["puntajes.csv", "puntajes.xlsx"]  # archivos locales esperados

# ----------------- Utilidades -----------------
def find_data_path():
    # Prioridad: CSV > XLSX si ambos existen en la carpeta
    for p in CANDIDATE_PATHS:
        if os.path.exists(p):
            return p
    return None

def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Normalizar columna Grupo
    if "Grupo" not in df.columns:
        df.insert(0, "Grupo", "")

    # Asegurar columnas de actividades (si falta alguna, crearla en 0)
    for col in ACTIVITIES:
        if col not in df.columns:
            df[col] = 0

    # Quedarnos solo con columnas esperadas
    keep = ["Grupo"] + ACTIVITIES
    df = df[[c for c in keep if c in df.columns]]

    # Tipos numéricos en actividades
    for col in ACTIVITIES:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Limpiar nombres y filtrar solo equipos válidos
    df["Grupo"] = df["Grupo"].astype(str).str.strip()
    df = df[df["Grupo"].isin(TEAMS)]

    # Quitar duplicados (conservar el último)
    df = df.drop_duplicates(subset="Grupo", keep="last")

    # Asegurar que TODOS los equipos FV1..FV6 existan (rellenar faltantes con 0)
    base = pd.DataFrame({"Grupo": TEAMS})
    df = base.merge(df, on="Grupo", how="left")
    for col in ACTIVITIES:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Total y orden
    df["Total"] = df[ACTIVITIES].sum(axis=1)
    df["Grupo"] = pd.Categorical(df["Grupo"], categories=TEAMS, ordered=True)
    df = df.sort_values("Grupo").reset_index(drop=True)
    return df

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=0)
    else:
        raise ValueError("Formato no soportado. Use .csv o .xlsx")
    return _ensure_columns(df)

def last_updated(path: str) -> str:
    if os.path.exists(path):
        ts = datetime.fromtimestamp(os.path.getmtime(path))
        return ts.strftime("%Y-%m-%d %H:%M")
    return "—"

def medals(pos: int) -> str:
    return "🥇" if pos == 1 else ("🥈" if pos == 2 else ("🥉" if pos == 3 else ""))

# ----------------- App -----------------
st.set_page_config(page_title="Kahoot • Puntajes FV1–FV6", page_icon="📊", layout="wide")
st.title("📊 Eliminatorias Kahoot Pro Exposolar")
st.caption("Edita localmente puntajes en 'puntajes.csv' o 'puntajes.xlsx'. La app solo visualiza y rankea.")

# Barra lateral: actualizar y ruta opcional
with st.sidebar:
    st.header("⚙️ Fuente de datos local")
    st.write("La app busca automáticamente `puntajes.csv` o `puntajes.xlsx` en esta carpeta.")
    custom = st.text_input("Ruta personalizada (opcional)", value="", placeholder="ej. C:/proyecto/puntajes.xlsx")
    if st.button("🔄 Actualizar"):
        st.cache_data.clear()

# Determinar ruta de datos
data_path = custom if custom else find_data_path()

# Si no hay archivo, mostrar instrucciones y plantillas
if not data_path or not os.path.exists(data_path):
    st.warning("No se encontró `puntajes.csv` ni `puntajes.xlsx` en la carpeta actual.")
    st.markdown(
        "- Descarga una plantilla: "
        "[CSV](sandbox:/mnt/data/puntajes_FV_fechas_template.csv) | "
        "[XLSX](sandbox:/mnt/data/puntajes_FV_fechas_template.xlsx)\n"
        "- Edítala localmente y guárdala como **`puntajes.csv`** o **`puntajes.xlsx`** "
        "en el mismo directorio de la app.\n"
        "- Luego presiona **Actualizar** en la barra lateral."
    )
    st.stop()

# Cargar datos
try:
    df = load_data(data_path)
except Exception as e:
    st.error(f"Error al cargar el archivo: {e}")
    st.stop()

st.success(f"Datos cargados desde: `{data_path}` — Última modificación: {last_updated(data_path)}")

# ----------------- Vistas -----------------
tab_team, tab_rank, tab_table = st.tabs(["🔎 Resultados por equipo", "🏆 Ranking", "📋 Tabla completa"])

with tab_team:
    st.subheader("Resultados por equipo")
    sel = st.selectbox("Equipo", options=TEAMS, index=0)
    fila = df[df["Grupo"] == sel].iloc[0]
    st.metric("Total", f"{int(fila['Total'])}")

    colA, colB = st.columns([1,2], vertical_alignment="top")
    with colA:
        detalle = pd.DataFrame({"Actividad": ACTIVITIES,
                                "Puntaje": [int(fila[a]) for a in ACTIVITIES]})
        st.table(detalle)
    with colB:
        serie = detalle.set_index("Actividad")["Puntaje"]
        st.bar_chart(serie)

with tab_rank:
    st.subheader("Ranking general")
    ranking = df[["Grupo", "Total"]].copy()
    ranking["Total"] = ranking["Total"].astype(int)
    ranking = ranking.sort_values("Total", ascending=False).reset_index(drop=True)
    ranking.insert(0, "Posición", np.arange(1, len(ranking) + 1))
    ranking.insert(0, "", ranking["Posición"].apply(medals))
    st.dataframe(ranking[["", "Posición", "Grupo", "Total"]], use_container_width=True, hide_index=True)

with tab_table:
    st.subheader("Tabla completa (solo lectura)")
    st.dataframe(df[["Grupo"] + ACTIVITIES + ["Total"]], use_container_width=True, hide_index=True)

st.caption("Tip: tras cada actualización de puntajes en el archivo, pulsa **Actualizar** en la barra lateral.")
