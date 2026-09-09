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

# Coordenadas reales de Puerto Triunfo (Quebrada Doradal - Estación 18)
LAT_DEFECTO = 5.9781
LON_DEFECTO = -74.7291

API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

st.set_page_config(page_title="Estación 18 — Quebrada Doradal", page_icon="🌊", layout="wide")

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

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
st.sidebar.header("Parámetros de consulta")
nombre_estudiante = st.sidebar.text_input("Nombre del estudiante", "Tu Nombre Y Apellido")
codigo_estacion = st.sidebar.text_input("Código de estación", "18")
fecha_desde = st.sidebar.date_input("Desde", pd.to_datetime("2026-09-02")).strftime("%Y-%m-%d")
fecha_hasta = st.sidebar.date_input("Hasta", pd.to_datetime("2026-09-08")).strftime("%Y-%m-%d")
consultar = st.sidebar.button("🔍 Consultar", type="primary")

st.title("🌊 Monitoreo Hidrométrico — Estación 18")
st.caption(f"Estudiante: **{nombre_estudiante}** · Ubicación: **Quebrada Doradal (Puerto Triunfo)**")

if consultar:
    with st.spinner("Conectando con la red MARCO de CORNARE..."):
        datos_crudos, error = obtener_serie_nivel(codigo_estacion, fecha_desde, fecha_hasta)

    if error:
        st.error(f"❌ {error}")
    else:
        registros = obtener_todas_las_paginas(datos_crudos)

        if not registros:
            st.warning("No hay registros para este periodo.")
        else:
            df = pd.DataFrame(registros)
            if "fecha" not in df.columns and "level_date" in df.columns:
                df = df.rename(columns={"level_date": "fecha", "level": "nivel"})

            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            df["nivel"] = pd.to_numeric(df["nivel"], errors="coerce")
            df = df.dropna(subset=["fecha", "nivel"]).sort_values("fecha").reset_index(drop=True)

            # Métricas avanzadas
            nivel_max = df["nivel"].max()
            nivel_min = df["nivel"].min()
            nivel_prom = df["nivel"].mean()
            
            # Cálculo de la máxima variación en 1 hora
            df["variacion_1h"] = df["nivel"].diff(60).abs()
            max_var = df["variacion_1h"].max()

            # --- Panel de Métricas ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Lecturas procesadas", f"{len(df):,}")
            col2.metric("Nivel Promedio", f"{nivel_prom:.2f} cm")
            col3.metric("Nivel Máximo (Pico)", f"{nivel_max:.2f} cm")
            col4.metric("Máx. Cambio en 1h", f"{max_var:.2f} cm" if not np.isnan(max_var) else "N/A")

            # --- Gráfico de Serie de Tiempo ---
            st.subheader("📈 Serie de Tiempo del Nivel")
            st.line_chart(df.set_index("fecha")["nivel"])

            # --- Análisis por Hora ---
            st.markdown("---")
            st.subheader("🕒 Patrón Diario (Promedio por Hora)")
            df["hora"] = df["fecha"].dt.hour
            promedio_hora = df.groupby("hora")["nivel"].mean().reset_index()

            fig, ax = plt.subplots(figsize=(10, 3))
            ax.plot(promedio_hora["hora"], promedio_hora["nivel"], marker="o", color="teal", linewidth=2)
            ax.set_xlabel("Hora del Día (0 - 23 hrs)")
            ax.set_ylabel("Nivel (cm)")
            ax.set_xticks(range(0, 24, 2))
            ax.grid(True, linestyle="--", alpha=0.5)
            st.pyplot(fig)

            # --- Galería y Ubicación Corregida ---
            st.markdown("---")
            col_mapa, col_fotos = st.columns([1, 1])

            with col_mapa:
                st.subheader("📍 Ubicación Real de la Estación")
                st.map(pd.DataFrame({"lat": [LAT_DEFECTO], "lon": [LON_DEFECTO]}), zoom=12)
                st.caption("Coordenadas: Puerto Triunfo, Antioquia (5.9781, -74.7291)")

            with col_fotos:
                st.subheader("📷 Referencia Visual de la Zona")
                st.image("https://www.cornare.gov.co/wp-content/uploads/2026/08/TECNOLOGIA-2-1024x768.jpg", caption="Estación Hidrométrica de Monitoreo - Red MARCO", use_container_width=True)

            # --- Datos Crudos ---
            with st.expander("📄 Exportar datos procesados"):
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Descargar CSV", csv, file_name=f"estacion_18_quebrada_doradal.csv", mime="text/csv")
else:
    st.info("Usa el botón **🔍 Consultar** en la barra lateral para procesar la información.")
