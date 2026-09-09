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

LAT_DEFECTO = 5.9781
LON_DEFECTO = -74.7291

API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

st.set_page_config(page_title="Estación 18 — Quebrada Doradal", page_icon="🌊", layout="wide")

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

# Sidebar
st.sidebar.header("Parámetros de consulta")
nombre_estudiante = st.sidebar.text_input("Nombre del estudiante", "Yheferson Henao")
codigo_estacion = st.sidebar.text_input("Código de estación", "18")
fecha_desde = st.sidebar.date_input("Desde", pd.to_datetime("2026-09-02")).strftime("%Y-%m-%d")
fecha_hasta = st.sidebar.date_input("Hasta", pd.to_datetime("2026-09-08")).strftime("%Y-%m-%d")
consultar = st.sidebar.button("🔍 Consultar", type="primary")

st.title("🌊 Monitoreo del Nivel del Río — Estación 18")
st.caption(f"Estudiante: **{nombre_estudiante}** · Ubicación: **Quebrada Doradal (Puerto Triunfo)**")

if consultar:
    with st.spinner("Conectando con CORNARE..."):
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

            nivel_actual = df["nivel"].iloc[-1]
            nivel_max = df["nivel"].max()
            nivel_min = df["nivel"].min()
            nivel_prom = df["nivel"].mean()

            # 1. Semáforo
            st.markdown("### 🚨 Estado Actual del Río")
            if nivel_actual < 98.0:
                st.success(f"🟢 **NIVEL NORMAL**: El río está en **{nivel_actual:.1f} cm** (Sin riesgo).")
            elif 98.0 <= nivel_actual < 105.0:
                st.warning(f"🟡 **ALERTA AMARILLA**: El río subió a **{nivel_actual:.1f} cm**.")
            else:
                st.error(f"🔴 **ALERTA ROJA**: Riesgo de creciente con **{nivel_actual:.1f} cm**.")

            # 2. Métricas fáciles de entender
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Mediciones tomadas", f"{len(df):,}")
            col2.metric("Nivel Promedio", f"{nivel_prom:.1f} cm")
            col3.metric("Nivel Mínimo", f"{nivel_min:.1f} cm")
            col4.metric("Nivel Máximo (Pico)", f"{nivel_max:.1f} cm")

            st.markdown("---")

            # 3. Gráficas sencillas
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.subheader("📈 ¿Cómo cambió el nivel con los días?")
                st.line_chart(df.set_index("fecha")["nivel"], height=250)

            with col_g2:
                st.subheader("📊 ¿En qué nivel estuvo casi siempre?")
                fig_hist, ax_h = plt.subplots(figsize=(5, 3))
                ax_h.hist(df["nivel"], bins=15, color="skyblue", edgecolor="steelblue")
                ax_h.set_xlabel("Nivel (cm)")
                ax_h.set_ylabel("Cantidad de veces")
                ax_h.grid(True, linestyle="--", alpha=0.4)
                st.pyplot(fig_hist)

            st.markdown("---")

            # 4. Patrón por hora
            st.subheader("🕒 ¿A qué hora del día sube o baja el agua?")
            df["hora"] = df["fecha"].dt.hour
            promedio_hora = df.groupby("hora")["nivel"].mean().reset_index()

            fig_hora, ax_p = plt.subplots(figsize=(10, 2.5))
            ax_p.plot(promedio_hora["hora"], promedio_hora["nivel"], marker="o", color="teal", linewidth=2)
            ax_p.set_xlabel("Hora del Día (0 a 23 hrs)")
            ax_p.set_ylabel("Nivel Promedio (cm)")
            ax_p.set_xticks(range(0, 24, 2))
            ax_p.grid(True, linestyle="--", alpha=0.5)
            st.pyplot(fig_hora)

            st.info("💡 **Dato clave:** En las mañanas (6:00 AM a 12:00 PM) el río alcanza su nivel más bajo y en la tarde recupera su altura habitual.")

            # 5. Ubicación y Foto
            st.markdown("---")
            col_mapa, col_fotos = st.columns([1, 1])

            with col_mapa:
                st.subheader("📍 Ubicación en el Mapa")
                st.map(pd.DataFrame({"lat": [LAT_DEFECTO], "lon": [LON_DEFECTO]}), zoom=12)
                st.caption("Puerto Triunfo, Antioquia (Sector California)")

            with col_fotos:
                st.subheader("📷 Estación de Monitoreo")
                url_oficial = "https://marco.cornare.gov.co/media/estaciones/Quebrada_Doradal_California_1.webp"
                st.image(url_oficial, caption="Sensor ultrasónico en Quebrada Doradal", use_container_width=True)

            # 6. Descarga
            with st.expander("📄 Ver y descargar la tabla de datos"):
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Descargar datos (CSV)", csv, file_name="estacion_18_quebrada_doradal.csv", mime="text/csv")
else:
    st.info("Presiona el botón **🔍 Consultar** en la barra lateral para ver los datos.")
