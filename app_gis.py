import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
import zipfile
import tempfile
import os

st.set_page_config(
    page_title="Web GIS App",
    layout="wide"
)
st.title("Web GIS Application")
st.write("Upload Left and Right layers, then perform Spatial Join or Attribute Join.")

st.sidebar.header("Upload Files")
###*************************************************
###إضافة رفع الملفين داخل التطبيق
left_file = st.sidebar.file_uploader(
    "Upload Left Layer (Shapefile ZIP)",
    type=["zip"]
)

right_file = st.sidebar.file_uploader(
    "Upload Right Layer (GeoJSON)",
    type=["geojson", "json"]
)
###تحديد نوع الربط 
join_option = st.sidebar.selectbox(
    "Select Join Type",
    ["Spatial Join", "Attribute Join"]
)

st.write("Selected Join Type:", join_option)

###*************************************************
### إضافة دوال قراءة الملفات وقراءتها داخل التطبيق
def read_shapefile_from_zip(uploaded_file):
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, uploaded_file.name)

    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    for file_name in os.listdir(temp_dir):
        if file_name.endswith(".shp"):
            shp_path = os.path.join(temp_dir, file_name)
            return gpd.read_file(shp_path)

    return None


def read_geojson_file(uploaded_file):
    temp_dir = tempfile.mkdtemp()
    geojson_path = os.path.join(temp_dir, uploaded_file.name)

    with open(geojson_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return gpd.read_file(geojson_path)

left_layer = None
right_layer = None

if left_file is not None:
    left_layer = read_shapefile_from_zip(left_file)

if right_file is not None:
    right_layer = read_geojson_file(right_file)
###**********************************************
##توحيد نظام الإحداثيات داخل التطبيق
if left_layer is not None and right_layer is not None:
    if left_layer.crs != right_layer.crs:
        right_layer = right_layer.to_crs(left_layer.crs)
if left_layer is not None and right_layer is not None:
    st.write("Left CRS:", left_layer.crs)
    st.write("Right CRS:", right_layer.crs)

###**********************************************
##عرض أول 5 صفوف من الملفين داخل التطبيق
if left_layer is not None and right_layer is not None:
    st.subheader("Preview of Uploaded Data")

    col1, col2 = st.columns(2)

    with col1:
        st.write("Left Layer - First 5 Rows")
        st.dataframe(left_layer.head())

    with col2:
        st.write("Right Layer - First 5 Rows")
        st.dataframe(right_layer.head())

###**********************************************
##عرض خرائط الملفين داخل التطبيق
def create_map(gdf, color):
    gdf_4326 = gdf.to_crs(epsg=4326)

    bounds = gdf_4326.total_bounds
    center_y = (bounds[1] + bounds[3]) / 2
    center_x = (bounds[0] + bounds[2]) / 2

    my_map = folium.Map(location=[center_y, center_x], zoom_start=8)

    folium.GeoJson(
        gdf_4326,
        style_function=lambda x: {
            "color": color,
            "weight": 2,
            "fillOpacity": 0.2
        }
    ).add_to(my_map)

    return my_map

if left_layer is not None and right_layer is not None:
    st.subheader("Maps of Uploaded Layers")

    col_map1, col_map2 = st.columns(2)

    with col_map1:
        st.write("Left Layer Map")
        left_map = create_map(left_layer, "green")
        st_folium(left_map, width=500, height=350)

    with col_map2:
        st.write("Right Layer Map")
        right_map = create_map(right_layer, "blue")
        st_folium(right_map, width=500, height=350)
##########*********************************
##تنفيذ الربط المكاني داخل التطبيق + عرض الخريطة 
if left_layer is not None and right_layer is not None:
    if join_option == "Spatial Join":
        spatial_result = gpd.sjoin(
            left_layer,
            right_layer,
            how="inner",
            predicate="intersects"
        )

        st.subheader("Spatial Join Result")
        st.write("Number of output records:", spatial_result.shape[0])
        st.dataframe(spatial_result.head())
        st.subheader("Spatial Join Map")

        result_map = create_map(spatial_result, "red")
        st_folium(result_map, width=900, height=450)
        spatial_output_file = "spatial_result.geojson"
        spatial_result.to_file(spatial_output_file, driver="GeoJSON")

        with open(spatial_output_file, "rb") as file:
            st.download_button(
                label="Download Spatial Join Result as GeoJSON",
                data=file,
                file_name="spatial_result.geojson",
                mime="application/geo+json"
            )
###******************************************************
##تنفيذ الربط الوصفي  داخل التطبيق + عرض الخريطة 

    if join_option == "Attribute Join":
        spatial_temp = gpd.sjoin(
            left_layer,
            right_layer,
            how="inner",
            predicate="intersects"
        )

        attribute_table = spatial_temp[[
            "ID_2",
            "NAME_2",
            "F_CODE_DES",
            "HYC_DESCRI"
        ]].copy()

        attribute_table = attribute_table.rename(columns={
            "ID_2": "gov_id",
            "NAME_2": "governorate_name",
            "F_CODE_DES": "source_type",
            "HYC_DESCRI": "source_description"
        })

        attribute_table_clean = attribute_table.drop_duplicates()

        attribute_result = pd.merge(
            left_layer,
            attribute_table_clean,
            left_on="ID_2",
            right_on="gov_id",
            how="inner"
        )

        attribute_result = gpd.GeoDataFrame(
            attribute_result,
            geometry="geometry",
            crs=left_layer.crs
        )

        st.subheader("Attribute Join Result")
        st.write("Number of output records:", attribute_result.shape[0])


        st.dataframe(attribute_result.head())
        st.subheader("Attribute Join Map")

        attribute_map = create_map(attribute_result, "purple")
        st_folium(attribute_map, width=900, height=450)

        output_file = "attribute_result.geojson"
        attribute_result.to_file(output_file, driver="GeoJSON")

        with open(output_file, "rb") as file:
            st.download_button(
                label="Download Attribute Join Result as GeoJSON",
                data=file,
                file_name="attribute_result.geojson",
                mime="application/geo+json"
            )