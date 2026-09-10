import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN VISUAL INSTITUCIONAL
st.set_page_config(
    page_title="Stock Ganadero Santa Fe",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Sistema de Información Geoespacial Ganadero")
st.markdown("### Provincia de Santa Fe — Monitoreo Avanzado de Stock")

# 2. CARGA DE ARCHIVOS CON CACHE OPTIMIZADO
@st.cache_data
def cargar_geometria(ruta_geojson):
    return gpd.read_file(ruta_geojson)

@st.cache_data
def cargar_datos_ganaderos(ruta_csv):
    # Configuración blindada: lee los ceros a la izquierda, el punto y coma y la codificación de Windows
    return pd.read_csv(ruta_csv, dtype={"CODIGO": str}, encoding="latin-1", sep=";")

try:
    gdf_base = cargar_geometria("datos/departamentos_base.geojson")
    df_ganado = cargar_datos_ganaderos("datos/Tabla_ganadera.csv")
except Exception as e:
    st.error(f"Error al cargar los archivos: {e}")
    st.stop()

# 3. FILTROS DE SELECCIÓN MÚLTIPLE EN EL PANEL LATERAL
st.sidebar.header("Filtros Avanzados")
st.sidebar.markdown("*Mantenga presionado o seleccione varias opciones para combinar los datos.*")

# Listas de opciones únicas directamente de tu base de datos de 1378 filas
actividades_disponibles = sorted(df_ganado["actividad"].unique().tolist())
categorias_disponibles = sorted(df_ganado["categoria"].unique().tolist())

# Reemplazamos selectbox por multiselect para habilitar la multi-selección moderna
actividades_sel = st.sidebar.multiselect(
    "1. Seleccione las Actividades:",
    options=actividades_disponibles,
    default=actividades_disponibles # Por defecto vienen todas seleccionadas
)

# El filtro de categorías se adapta dinámicamente según las actividades seleccionadas
if actividades_sel:
    df_temporal = df_ganado[df_ganado["actividad"].isin(actividades_sel)]
    categorias_dinamicas = sorted(df_temporal["categoria"].unique().tolist())
else:
    categorias_dinamicas = categorias_disponibles

categorias_sel = st.sidebar.multiselect(
    "2. Seleccione las Categorías:",
    options=categorias_dinamicas,
    default=categorias_dinamicas
)

# 4. PROCESAMIENTO MÚLTIPLE EN LA MEMORIA DEL SERVIDOR
if not actividades_sel or not categorias_sel:
    st.warning("⚠️ Por favor, seleccione al menos una Actividad y una Categoría en el panel izquierdo.")
    st.stop()

# Filtrado por listas usando .isin()
df_procesado = df_ganado[
    (df_ganado["actividad"].isin(actividades_sel)) & 
    (df_ganado["categoria"].isin(categorias_sel))
]

# Sumarización automática agrupando por código de departamento
df_final_mapa = df_procesado.groupby("CODIGO")["cantidad"].sum().reset_index()

# Acoplamiento geográfico exacto con los polígonos de QGIS
gdf_mapa = gdf_base.merge(df_final_mapa, on="CODIGO", how="left").fillna(0)

# 5. PANEL DE MÉTRICAS DINÁMICAS
total_provincial = int(gdf_mapa["cantidad"].sum())
depto_max = gdf_mapa.loc[gdf_mapa["cantidad"].idxmax()] if total_provincial > 0 else None

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Stock Provincial Combinado (Cabezas)", value=f"{total_provincial:,}")
with col2:
    if depto_max is not None:
        st.metric(label="Departamento Líder en Selección", value=f"{depto_max['NOMBRE']}", delta=f"{int(depto_max['cantidad']):,} cabezas")
    else:
        st.metric(label="Departamento Líder", value="Sin datos")

# 6. RENDERIZADO DEL MAPA INTERACTIVO (FOLIUM)
st.markdown("---")

m = folium.Map(location=[-31.6, -60.7], zoom_start=7, tiles="cartodbpositron")

# Capa de gradiente cromático
folium.Choropleth(
    geo_data=gdf_mapa,
    name="Datos Ganaderos",
    data=gdf_mapa,
    columns=["CODIGO", "cantidad"],
    key_on="feature.properties.CODIGO",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.4,
    legend_name="Cantidad de Cabezas",
    highlight=True
).add_to(m)

# Capa de interacción con el usuario (Tooltips flotantes)
folium.GeoJson(
    gdf_mapa,
    style_function=lambda x: {'fillColor': '#ffffff00', 'color': '#00000000'},
    tooltip=folium.GeoJsonTooltip(
        fields=["NOMBRE", "cantidad"],
        aliases=["Departamento:", "Stock Seleccionado:"],
        localize=True
    )
).add_to(m)

# Despliegue a pantalla completa adaptada a la web institucional
st_folium(m, use_container_width=True, height=600)
