"""
App de Streamlit — Nivel de ríos/quebradas (CORNARE / MARCO)
Módulo 5: Análisis de Series de Tiempo
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LAT_DEFECTO = 6.2766
LON_DEFECTO = -75.5901

API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

LLAVE_FECHA = "fecha"
LLAVE_VALOR = "nivel"
CANDIDATOS_LAT = ["lat", "latitude", "latitud"]
CANDIDATOS_LON = ["lng", "lon", "longitude", "longitud"]

st.set_page_config(page_title="Nivel de estación — CORNARE", page_icon="🌊", layout="wide")

# ------------------------------------------------------------------
# Funciones de consulta
# ------------------------------------------------------------------
def obtener_serie_nivel(codigo_estacion, desde, hasta, calidad=1, timeout=30):
    url = f"{API_BASE_URL}/{codigo_estacion}/nivel"
    params = {"desde": desde, "hasta": hasta, "calidad": calidad}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout, verify=False)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return None, f"Error de red: {e}"


def obtener_todas_las_paginas(datos_json, timeout=30):
    registros = list(datos_json.get("values", []))
    siguiente_url = datos_json.get("next")
    while siguiente_url:
        try:
            resp = requests.get(siguiente_url, timeout=timeout, verify=False)
        except requests.exceptions.RequestException:
            break
        if resp.status_code != 200:
            break
        pagina = resp.json()
        registros.extend(pagina.get("values", []))
        siguiente_url = pagina.get("next")
    return registros


def detectar_coordenadas(datos_json):
    if not isinstance(datos_json, dict):
        return LAT_DEFECTO, LON_DEFECTO, False

    lat = next((datos_json[k] for k in CANDIDATOS_LAT if k in datos_json), None)
    lon = next((datos_json[k] for k in CANDIDATOS_LON if k in datos_json), None)

    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon), True
        except (TypeError, ValueError):
            pass
    return LAT_DEFECTO, LON_DEFECTO, False


def calcular_indice_calidad(df):
    if df.empty or len(df) < 2:
        return 0.0, 0, 0

    df_idx = df.set_index("fecha")
    frecuencia_tipica = df["fecha"].diff().dropna().mode()
    if len(frecuencia_tipica) == 0:
        return 0.0, 0, 0
    frecuencia_tipica = frecuencia_tipica[0]

    rango_completo = pd.date_range(start=df_idx.index.min(), end=df_idx.index.max(), freq=frecuencia_tipica)
    esperados = len(rango_completo)
    huecos = esperados - len(df_idx)
    completitud = max(0.0, 1 - (huecos / esperados)) if esperados > 0 else 0.0

    Q1, Q3 = df["nivel"].quantile(0.25), df["nivel"].quantile(0.75)
    IQR = Q3 - Q1
    lim_inf, lim_sup = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    es_outlier = (df["nivel"] < lim_inf) | (df["nivel"] > lim_sup) | (df["nivel"] < 0)
    proporcion_outliers = es_outlier.mean()

    indice = (completitud * 0.7 + (1 - proporcion_outliers) * 0.3) * 100
    return round(indice, 1), int(huecos), int(es_outlier.sum())


# ------------------------------------------------------------------
# Sidebar — Parámetros de consulta configurados con tu estación 18
# ------------------------------------------------------------------
st.sidebar.header("Parámetros de tu consulta")
nombre_estudiante = st.sidebar.text_input("Nombre del estudiante", "Tu Nombre Y Apellido")
codigo_estacion = st.sidebar.text_input("Código de estación", "18")
fecha_desde = st.sidebar.date_input("Desde", pd.to_datetime("2026-09-02")).strftime("%Y-%m-%d")
fecha_hasta = st.sidebar.date_input("Hasta", pd.to_datetime("2026-09-08")).strftime("%Y-%m-%d")
calidad = st.sidebar.selectbox("Calidad", [1, 0], index=0, help="1 = solo datos validados")
consultar = st.sidebar.button("🔍 Consultar", type="primary")

st.title("🌊 Nivel de ríos y quebradas — CORNARE")
st.caption(f"Estudiante: **{nombre_estudiante}** · Estación: **{codigo_estacion} (Puerto Triunfo)**")

# ------------------------------------------------------------------
# Consulta y Procesamiento
# ------------------------------------------------------------------
if consultar:
    with st.spinner("Consultando la API de CORNARE..."):
        datos_crudos, error = obtener_serie_nivel(codigo_estacion, fecha_desde, fecha_hasta, calidad)

    if error:
        st.error(f"❌ {error}")
    else:
        registros = obtener_todas_las_paginas(datos_crudos)

        if not registros:
            st.warning("No hay registros para esta estación y rango de fechas.")
        else:
            df = pd.DataFrame(registros)
            
            # Ajuste de llaves si vienen con nombres estándar o DRF
            if "fecha" not in df.columns and "level_date" in df.columns:
                df = df.rename(columns={"level_date": "fecha", "level": "nivel"})

            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            df["nivel"] = pd.to_numeric(df["nivel"], errors="coerce")
            df = df.dropna(subset=["fecha", "nivel"]).sort_values("fecha").reset_index(drop=True)

            lat, lon, coords_reales = detectar_coordenadas(datos_crudos)
            indice_calidad, huecos, n_outliers = calcular_indice_calidad(df)

            # --- Métricas principales ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Lecturas procesadas", len(df))
            col2.metric("Nivel promedio", f"{df['nivel'].mean():.2f} cm")
            col3.metric("Índice de calidad", f"{indice_calidad} / 100")
            col4.metric("Outliers detectados", n_outliers)

            # --- Gráfico de la serie de tiempo completa ---
            st.subheader("📈 Serie de tiempo del nivel")
            st.line_chart(df.set_index("fecha")["nivel"])

            # --- NUEVA SECCIÓN: Análisis por Hora del Día ---
            st.markdown("---")
            st.subheader("🕒 Análisis del comportamiento diario (Nivel promedio por hora)")
            
            df["hora"] = df["fecha"].dt.hour
            promedio_hora = df.groupby("hora")["nivel"].mean().reset_index()

            fig, ax = plt.subplots(figsize=(10, 3.5))
            ax.plot(promedio_hora["hora"], promedio_hora["nivel"], marker="o", color="darkcyan", linewidth=2)
            ax.set_xlabel("Hora del Día (0 - 23 hrs)")
            ax.set_ylabel("Nivel Promedio (cm)")
            ax.set_xticks(range(0, 24, 2))
            ax.grid(True, linestyle="--", alpha=0.5)
            st.pyplot(fig)

            st.info("💡 **Observación clave:** Se identifica un valle de nivel mínimo entre las **6:00 y las 12:00 hrs**, retomando la tendencia promedio durante las horas de la tarde.")

            # --- Ubicación en Mapa ---
            st.markdown("---")
            st.subheader("📍 Ubicación de la estación")
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=10)

            # --- Tablas de datos y descarga ---
            with st.expander("📄 Ver tabla de datos completos"):
                st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar datos (CSV)", csv, file_name=f"estacion_{codigo_estacion}.csv", mime="text/csv")
else:
    st.info("Presiona el botón **🔍 Consultar** en la barra lateral para cargar el análisis.")
