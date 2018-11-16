import os
import requests
import geopandas as gpd
from sqlalchemy import *
from geoalchemy2 import Geometry, WKTElement

def checkInput(message, mandatory=True, directory_exists=True):
    import os
    value = input(message) or "None"
    if value is "None" and mandatory:
        print(f"Invalid input : '{value}'. Please reenter")
        value = checkInput(message, mandatory)
    elif directory_exists and not os.path.exists(value):
        print(f"Unable to find file '{value}'. Please re-enter.")
        value = checkInput(message, mandatory)
    
    return value


def postToGeoserver(target_url, authentication, xml, head={'Content-Type': 'text/xml'}):
    r = requests.post(target_url, headers=head, auth=authentication, data=xml)
    print(r.text)
    return r


def checkInput(message, mandatory=True, directory_exists=True):
    value = input(message) or "None"
    if value is "None" and mandatory:
        print(f"Invalid input : '{value}'. Please reenter")
        value = checkInput(message, mandatory)
    elif directory_exists and not os.path.exists(value):
        print(f"Unable to find file '{value}'. Please re-enter.")
        value = checkInput(message, mandatory)
    
    return value


def postToGeoserver(target_url, authentication, xml, head={'Content-Type': 'text/xml'}):
    r = requests.post(target_url, headers=head, auth=authentication, data=xml)
    print(r.text)
    return r

def publishTiffLayer(filename, workspace, epsgCode, credentials, headers):
    coverage_xml = f"""
    <coverage>
        <name>{filename}</name>
        <nativeName>{filename}</nativeName>
        <namespace>{workspace}</namespace>
        <title>{filename}</title>
        <nativeCrs>EPSG:{epsgCode}</nativeCrs>
        <srs>EPSG:{epsgCode}</srs>
        <enabled>True</enabled>
        <store class="coverageStore">{workspace}:{filename}</store>
        <recalculate>nativebbox,latlonbbox</recalculate>
    </coverage>
    """

    create_tif_layer_url = f"https://geo.library.arizona.edu/geoserver/rest/workspaces/{workspace}/coveragestores/{filename}/coverages.xml"

    postToGeoserver(create_tif_layer_url, credentials, coverage_xml, head=headers)

def createGeoTiffDataStore(filename, workspace, file_location, credentials, headers):
    # Create GeoTIFF store
    store_create_xml = f"""
    <coverageStore>
       <name>{filename}</name>
       <workspace>{workspace}</workspace>
       <enabled>true</enabled>
       <url>file://{file_location}</url>
       <type>GeoTIFF</type>
       <recalculate>nativebbox,latlonbbox</recalculate>
    </coverageStore>
    """

    create_store_url = f"https://geo.library.arizona.edu/geoserver/rest/workspaces/{workspace}/coveragestores"
    postToGeoserver(url=create_store_url, authentication=credentials, xml=store_create_xml, head=headers)

def postVectorLayer(filename, epsgCode, gs_postgis_store, gs_workspace, credentials, headers):
    # define your XML string that you want to send to the server
    create_ds_layer_xml = f"""
    <featureType>
        <nativeName>{filename.lower()}</nativeName>
        <name>{filename}</name>
        <nativeSrs>EPSG:{epsgCode}</nativeSrs>
        <srs>EPSG:{epsgCode}</srs>
        <enabled>true</enabled>
        <store class="dataStore">
            <name>{gs_postgis_store}</name>
        </store>
    </featureType>
    """

    create_layer_in_store_url = "https://geo.library.arizona.edu/geoserver/rest/workspaces/{}/datastores/{}/featuretypes".format(gs_workspace, gs_postgis_store)

    # Sent request to Geoserver REST API to Publish layer from the PostgreSQL data store
    postToGeoserver(create_layer_in_store_url, credentials, create_ds_layer_xml, head=headers)
    
    
def sendFileToPostGIS(vector_file, password, access_rights):
    print(f"Reading in file {vector_file}...")
    df = gpd.read_file(vector_file)
    
    # CREATE POSTGRESQL TABLE NAME. SAME AS FILE WITHOUT EXTENSION (LOWERCASE IMPORTANT)
    table_name = os.path.basename(vector_file).split(".")[0].lower()

    # GET GEOMETRY TYPE IN UPPERCASE
    geom_type = df.geometry.iloc[0].geom_type.upper()
    # GET EPSG CODE
    try:
        epsg_code = int(df.crs.get('init').split(":")[1])
    except:
        print("Unable to get get epsg code of geodataframe: Found CRS : {}\nExiting.".format(df.crs))
        raise ValueError
        
    df['geom'] = df['geometry'].apply(lambda x: WKTElement(x.wkt, srid=epsg_code))
    df.drop("geometry", 1, inplace=True)

    print("writing to postgres as table {}...".format(table_name))
    engine = create_engine('postgresql://manager:' + password + '@geo.library.arizona.edu:5440/UAL_geoData')
    df.to_sql(table_name.lower(), engine, schema=access_rights, if_exists='replace', index=True, index_label="OBJECTID", dtype={"geom": Geometry(geom_type, srid=epsg_code)})   
    
    return epsg_code