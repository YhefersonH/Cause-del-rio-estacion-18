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
nombre_estudiante = st.sidebar.text_input("Nombre del estudiante", "Yheferson Henao")
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

            # --- Métricas avanzadas ---
            nivel_actual = df["nivel"].iloc[-1]
            nivel_max = df["nivel"].max()
            nivel_prom = df["nivel"].mean()
            
            # Tasa de variación por hora
            df["variacion_1h"] = df["nivel"].diff(60)
            var_actual = df["variacion_1h"].iloc[-1] if len(df) > 60 else 0.0

            # Desviación estándar móvil (6 horas)
            df["volatilidad_6h"] = df["nivel"].rolling(window=360, min_periods=1).std()

            # --- MÓDULO 1: Semáforo de Alerta ---
            st.markdown("### 🚨 Estado de Alerta de la Quebrada")
            if nivel_actual < 98.0:
                st.success(f"🟢 **NIVEL NORMAL**: El cauce se encuentra en {nivel_actual:.2f} cm (Sin riesgo de desbordamiento).")
            elif 98.0 <= nivel_actual < 105.0:
                st.warning(f"🟡 **ALERTA AMARILLA**: Nivel elevado en {nivel_actual:.2f} cm. Se recomienda monitoreo continuo.")
            else:
                st.error(f"🔴 **ALERTA ROJA**: Riesgo alto de creciente en {nivel_actual:.2f} cm.")

            # --- MÓDULO 2: Panel de Métricas ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Lecturas procesadas", f"{len(df):,}")
            col2.metric("Nivel Promedio", f"{nivel_prom:.2f} cm")
            col3.metric("Nivel Máximo (Pico)", f"{nivel_max:.2f} cm")
            col4.metric("Tasa de Cambio (1h)", f"{var_actual:+.2f} cm/h", delta_color="inverse")

            # --- Gráfico Principal con Volatilidad ---
            st.subheader("📈 Serie de Tiempo y Volatilidad Móvil (6h)")
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)

            ax1.plot(df["fecha"], df["nivel"], color="steelblue", linewidth=1)
            ax1.set_ylabel("Nivel (cm)")
            ax1.grid(True, linestyle="--", alpha=0.5)

            ax2.plot(df["fecha"], df["volatilidad_6h"], color="darkorange", linewidth=1)
            ax2.set_ylabel("Volatilidad (Std 6h)")
            ax2.set_xlabel("Fecha")
            ax2.grid(True, linestyle="--", alpha=0.5)

            plt.tight_layout()
            st.pyplot(fig)

            # --- MÓDULO 3: Patrón Diario ---
            st.markdown("---")
            st.subheader("🕒 Comportamiento Diario (Promedio por Hora)")
            df["hora"] = df["fecha"].dt.hour
            promedio_hora = df.groupby("hora")["nivel"].mean().reset_index()

            fig_hora, ax_h = plt.subplots(figsize=(10, 2.8))
            ax_h.plot(promedio_hora["hora"], promedio_hora["nivel"], marker="o", color="teal", linewidth=2)
            ax_h.set_xlabel("Hora del Día (0 - 23 hrs)")
            ax_h.set_ylabel("Nivel (cm)")
            ax_h.set_xticks(range(0, 24, 2))
            ax_h.grid(True, linestyle="--", alpha=0.5)
            st.pyplot(fig_hora)

            # --- MÓDULO 4: Ubicación y Galería de la Estación ---
            st.markdown("---")
            col_mapa, col_fotos = st.columns([1, 1])

            with col_mapa:
                st.subheader("📍 Ubicación Real de la Estación")
                st.map(pd.DataFrame({"lat": [LAT_DEFECTO], "lon": [LON_DEFECTO]}), zoom=12)
                st.caption("Coordenadas: Puerto Triunfo, Antioquia (5.9781, -74.7291)")

            with col_fotos:
                st.subheader("📷 Estación Real 18 — Quebrada Doradal (California)")
                # URL RAW exacta de tu repositorio en GitHub
                url_imagen_github = "https://raw.githubusercontent.com/YhefersonH/Cause-del-rio-estacion-18/main/Quebrada_Doradal_California_1.webp"
                st.image(url_imagen_github, caption="Estación Ultrasónica 18 - Quebrada Doradal (Sector California, Puerto Triunfo)", use_container_width=True)

            # --- Exportar Datos ---
            with st.expander("📄 Exportar datos procesados"):
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Descargar CSV", csv, file_name="estacion_18_quebrada_doradal.csv", mime="text/csv")
else:
    st.info("Usa el botón **🔍 Consultar** en la barra lateral para procesar la información.")
