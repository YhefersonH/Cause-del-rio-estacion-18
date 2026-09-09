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
            
            # Cambio en la última hora
            df["variacion_1h"] = df["nivel"].diff(60)
            var_actual = df["variacion_1h"].iloc[-1] if len(df) > 60 else 0.0

            # 1. Semáforo
            st.markdown("### 🚨 Estado Actual del Río")
            if nivel_actual < 98.0:
                st.success(f"🟢 **NIVEL NORMAL**: El río está en **{nivel_actual:.1f} cm** (Sin riesgo de desbordamiento).")
            elif 98.0 <= nivel_actual < 105.0:
                st.warning(f"🟡 **ALERTA AMARILLA**: El río subió a **{nivel_actual:.1f} cm** (Monitoreo continuo).")
            elif 105.0 <= nivel_actual < 115.0:
                st.warning(f"🟠 **ALERTA NARANJA**: El río alcanzó **{nivel_actual:.1f} cm** (Preparación para evacuación).")
            else:
                st.error(f"🔴 **ALERTA ROJA**: Riesgo alto de creciente con **{nivel_actual:.1f} cm** (Evacuación inmediata).")

            # Tabla explicativa integrada dentro de la página
            with st.expander("ℹ️ Ver significado de los niveles de riesgo hidrológico"):
                st.markdown("""
                | Estado | Nivel (cm) | Significado Físico | Acción Recomendada |
                | :--- | :--- | :--- | :--- |
                | 🟢 **Normal** | < 98 cm | Cauce en flujo habitual, sin presión sobre riberas. | Condiciones seguras. |
                | 🟡 **Prevención** | 98 - 105 cm | Aumento por lluvias moderadas en la cuenca alta. | Monitoreo activo del comite de riesgo. |
                | 🟠 **Alerta** | 105 - 115 cm | Cauce lleno, próximo a puntos de desbordamiento. | Alistamiento preventivo para evacuación. |
                | 🔴 **Emergencia** | > 115 cm | Desbordamiento activo sobre sectores bajos. | Evacuación inmediata hacia zonas altas. |
                """)

            # 2. Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Lecturas Tomadas", f"{len(df):,}")
            col2.metric("Nivel Promedio", f"{nivel_prom:.1f} cm")
            col3.metric("Nivel Mínimo / Máximo", f"{nivel_min:.1f} / {nivel_max:.1f} cm")
            col4.metric("Tendencia (Última hora)", f"{var_actual:+.1f} cm/h", delta_color="inverse")

            st.markdown("---")

            # 3. Gráficas sencillas
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.subheader("📈 Comportamiento en los Días Analizados")
                st.line_chart(df.set_index("fecha")["nivel"], height=250)

            with col_g2:
                st.subheader("📊 Frecuencia de Niveles (Histograma)")
                fig_hist, ax_h = plt.subplots(figsize=(5, 3))
                ax_h.hist(df["nivel"], bins=15, color="skyblue", edgecolor="steelblue")
                ax_h.set_xlabel("Nivel (cm)")
                ax_h.set_ylabel("Frecuencia (Horas)")
                ax_h.grid(True, linestyle="--", alpha=0.4)
                st.pyplot(fig_hist)

            st.markdown("---")

            # 4. Patrón por hora explicado
            st.subheader("🕒 ¿A qué hora sube o baja el río?")
            df["hora"] = df["fecha"].dt.hour
            promedio_hora = df.groupby("hora")["nivel"].mean().reset_index()

            fig_hora, ax_p = plt.subplots(figsize=(10, 2.5))
            ax_p.plot(promedio_hora["hora"], promedio_hora["nivel"], marker="o", color="teal", linewidth=2)
            ax_p.set_xlabel("Hora del Día (0 a 23 hrs)")
            ax_p.set_ylabel("Nivel Promedio (cm)")
            ax_p.set_xticks(range(0, 24, 2))
            ax_p.grid(True, linestyle="--", alpha=0.5)
            st.pyplot(fig_hora)

            col_inf1, col_inf2 = st.columns(2)
            with col_inf1:
                st.info("📉 **Bajada Matutina (6 AM - 12 PM):** El nivel baja hasta su punto mínimo debido a la falta de precipitaciones durante la madrugada en la montaña.")
            with col_inf2:
                st.info("📈 **Recuperación Vespertina (12 PM - 6 PM):** El río vuelve a subir impulsado por las lluvias de la tarde en la cuenca alta.")

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
