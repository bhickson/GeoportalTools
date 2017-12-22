# Ben Hickson
# December 21, 2017

# FUNCTION: Takes a given structured csv (line XX) file and converts all rows with fully filled values to an xml
# metadata file following the ISO 19139 geospatial metadata schema.

# PURPOSE: This conversion was written for metadata that will be held in a data repository and follows criteria outlined in the

# CUSTOMIZATIONS OF NOTE:
#   Fill out the appropriate distributor contact info in the dist_contact dictionary variable.
#   The new file name (filename) created is derived from the value of the "Title" filed in the csv
#   PURL values are assigned based on the file name (filename) and PURL prefix (purl_prefix) values

import csv, os, argparse
from osgeo import osr, ogr, gdal
from datetime import datetime
from lxml import etree as ET
from xml.dom import minidom as md

parser = argparse.ArgumentParser(description="Convert rows of geospatial metadata values held in a csv file to xml"
                                             " following the ISO 19139 schema.")
parser.add_argument("-x", "--xmltemplate", type=str, help="LOCATION OF THE ISO 19139 XML TEMPLATE FILE. IF NOT"
                                                          " SPECIFIED, THE FILE IS ASSUMED TO BE IN THE SAME DIRECTORY"
                                                          " AS THE SCRIPT.")
parser.add_argument("-c", "--csvfile", type=str, help="LOCATION OF THE CSV FILE CONTAINING METADATA INFORMATION. IF NOT"
                                                      " SPECFIIED, THE FILE IS ASSUMED TO BE IN THE SAME DIRECTORY AS"
                                                      " THE SCRIPT.")
parser.add_argument("-d", "--datadir", type=str, help="DIRECTORY LOCATION WHERE GEOSPATIAL DATASETS IDENTIFIED IN THE"
                                                      " CSV FILE RESIDE. IF NOT SPECFIIED, PARENT DIRECTORY OF CSV FILE"
                                                      " IS USED.")
def checkpath(path):
    if not os.path.exists(path):
        print("ERROR: Dataset or directory \"" + path + "\"cannot be found.")
        exit()

# WRITE THE XML OBJECT TO FILE
def writeToFile(xmlObj, f):
    roughstring = ET.tostring(xmlObj)
    xmlfromstring = ET.fromstring(pretty_print(roughstring))

    tRoot = xmlfromstring.find(".")

    newTree = ET.ElementTree(xmlfromstring)
    outdir = parentdir
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    outfile = outdir + "\\" + f + ".xml"
    if os.path.exists(outfile):
        os.remove(outfile)
    newTree.write(outfile, encoding="UTF-8")

# REMOVE LEADING AND TRAILING WHITESPACES
def rltw(text):
    if text[0] == " ":
        text = text[1:]
    if text[-1] == "":
        text = text[:-1]
    return text

# FORMAT DATE. DATE SHOULD BE EITHER SINGLE DATE IN YYYY-MM-DD OR SET OF DATES SEPARATED BY "TO"
def formatDate(text):
    dates = {}

    def isoDateFormat(d):
        for k, v in d.items():
            if len(v) == 4:
                if k == "beg_date":
                    d[k] = v + "-01-01"
                else:
                    d[k] = v + "-12-31"

            elif "-" not in text or len(text) != 10:
                print("Formatting issue with date " + d[k] + ". Dates should be formatted YYYY-MM-DD")
                exit()

            # ALL DATES SHOULD BE 10 CHARACTERS AT THIS POINT
            d[k] += "T00:00:00"

        return d

    if "to" in text:
        dates["beg_date"] = text.split("to")[0].replace(" ", "")
        dates["end_date"] = text.split("to")[1].replace(" ", "")
    else:
        dates["instant_date"] = text

    dates = isoDateFormat(dates)

    return dates

# VIA USER CAPOOTI STACKEXCHANGE: HTTPS://GIS.STACKEXCHANGE.COM/A/7615
def getEPSGCode(file_path):
    prj = file_path[:-3] + "prj"
    prj_file = open(prj, 'r')
    prj_txt = prj_file.read()
    srs = osr.SpatialReference()
    srs.ImportFromESRI([prj_txt])
    srs.AutoIdentifyEPSG()
    return srs.GetAuthorityCode(None)

# VIA USER LUKE ON STACKEXCHANGE: HTTPS://GIS.STACKEXCHANGE.COM/A/57837
def getRasterExtent(rasterDS):
    # RETURN LIST OF CORNER COORDINATES FROM A GEOTRANSFORM
    def GetExtent(gt, cols, rows):
        ext = []
        xarr = [0, cols]
        yarr = [0, rows]

        for px in xarr:
            for py in yarr:
                x = gt[0] + (px * gt[1]) + (py * gt[2])
                y = gt[3] + (px * gt[4]) + (py * gt[5])
                ext.append([x, y])
                print(x, y)
            yarr.reverse()
        return ext

    # REPROJECT A LIST OF X,Y COORDINATES.
    def ReprojectCoords(coords, src_srs, tgt_srs):


        trans_coords = []
        transform = osr.CoordinateTransformation(src_srs, tgt_srs)
        for x, y in coords:
            x, y, z = transform.TransformPoint(x, y)
            trans_coords.append([x, y])
        return trans_coords

    ds = gdal.Open(rasterDS)

    gt = ds.GetGeoTransform()
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    ext = GetExtent(gt, cols, rows)

    src_srs = osr.SpatialReference()
    src_srs.ImportFromWkt(ds.GetProjection())
    tg = osr.SpatialReference()
    tgt_srs = src_srs.CloneGeogCS()

    geo_ext = ReprojectCoords(ext, src_srs, tgt_srs)
    print("new extent:", geo_ext)
    xvalues = (geo_ext[0][0], geo_ext[1][0], geo_ext[2][0], geo_ext[3][0])
    yvalues = (geo_ext[0][1], geo_ext[1][1], geo_ext[2][1], geo_ext[3][1])
    xmin = min(xvalues)
    xmax = max(xvalues)
    ymin = min(yvalues)
    ymax = max(yvalues)
    coordsdict = {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax}

    return coordsdict

# GET EXTENT (BOUNDING BOX) OF VECTOR DATASET
def getVectorExtent(vectorDS):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dsOpen = driver.Open(vectorDS, 0)
    extentTuple = dsOpen.GetLayer().GetExtent()  # returns (-180.0, 180.0, -78.7329013, 83.6664731)
    extent = {"xmin": extentTuple[0], "xmax": extentTuple[1], "ymin": extentTuple[2], "ymax": extentTuple[3]}
    return extent

# GET TYPE OF DATASET LAYER AND IF VECTOR, NUMBER OF FEATURES
def getLayerInfo(ds):
    """
    ISO geometric object types
        complex: set of geometric primitives such that their boundaries can be represented as a union of other primitives (polygon)
        composite: connected set of curves, solids or surfaces (polyline)
        curve: bounded, 1-dimensional geometric primitive, representing the continuous image of a line
        point: zero-dimensional geometric primitive, representing a position but not having an extent (point)
        solid: bounded, connected 3-dimensional geometric primitive, representing the continuous image of a region of space
        surface: bounded, connected 2-dimensional geometric primitive, representing the continuous image of a region of a plane (raster)
    """
    layer_info = {}

    if dataset_type == "raster":
        layer_info["Type"] = "surface"
    elif dataset_type == "vector":
        shapefile = ogr.Open(ds)
        layer = shapefile.GetLayer()
        feature = layer.GetNextFeature()
        geometry = feature.GetGeometryRef().GetGeometryName()

        if geometry == "POINT":
            layer_info["Type"] = "point"
        elif geometry == "LINESTRING":
            layer_info["Type"] = "composite"
        elif geometry == "POLYGON":
            layer_info["Type"] = "complex"
        else:
            print("ERROR: UNKNOWN DATA TYPE " + geometry + ". Should be one of POINT, LINESTRING, or POLYGON")

        layer_info["Number of Features"] = str(len(layer))

    return layer_info

# CREATE GMD ELEMENT WITH GMX CODELIST VALUES
def setGMXCodeElemAttributes(element, codeValue, element_name):
    codelistlocation = r"http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#" + element_name

    subelement = ET.SubElement(element, "{" + namespaces["gmd"] + "}" + element_name)
    subelement.set("codeList", codelistlocation)
    subelement.set("codeListValue", codeValue)
    subelement.set("codeSpace", "ISOTC211/19115")
    subelement.text = codeValue

# CREATE SINGLE gco:Characterstring ELEMENT
def createCharacterElem(element, string):
    char_string_elem = ET.SubElement(element, "{" + namespaces["gco"] + "}CharacterString")
    char_string_elem.text = string

# CREATE SUBTREE OF CONTACT INFO
def createContactTree(parent_elem, contact_dict, role):
    ci_responseaprty_elem = ET.SubElement(parent_elem, "{" + namespaces["gmd"] + "}CI_ResponsibleParty")
    indivname_elem = ET.SubElement(ci_responseaprty_elem, "{" + namespaces["gmd"] + "}individualName")
    orgname_elem = ET.SubElement(ci_responseaprty_elem, "{" + namespaces["gmd"] + "}organizationName")
    createCharacterElem(indivname_elem, contact_dict["Individual Name"])
    createCharacterElem(orgname_elem, contact_dict["Organization Name"])

    contactinfo_elem = ET.SubElement(ci_responseaprty_elem, "{" + namespaces["gmd"] + "}contactInfo")
    address_elem = ET.SubElement(contactinfo_elem, "{" + namespaces["gmd"] + "}address")
    ci_address_elem = ET.SubElement(address_elem, "{" + namespaces["gmd"] + "}CI_Address")
    delivpoint_elem = ET.SubElement(ci_address_elem, "{" + namespaces["gmd"] + "}deliveryPoint")
    createCharacterElem(delivpoint_elem, contact_dict["Street Address"])
    city_elem = ET.SubElement(ci_address_elem, "{" + namespaces["gmd"] + "}city")
    createCharacterElem(city_elem, contact_dict["City"])
    adminarea_elem = ET.SubElement(ci_address_elem, "{" + namespaces["gmd"] + "}administrativeArea")
    createCharacterElem(adminarea_elem, contact_dict["Admin Area"])
    postalcode_elem = ET.SubElement(ci_address_elem, "{" + namespaces["gmd"] + "}postalCode")
    createCharacterElem(postalcode_elem, contact_dict["Postal Code"])
    country_elem = ET.SubElement(ci_address_elem, "{" + namespaces["gmd"] + "}country")
    setGMXCodeElemAttributes(country_elem, contact_dict["Country"], "CountryCode")
    emailaddr_elem = ET.SubElement(ci_address_elem, "{" + namespaces["gmd"] + "}electronicMailAddress")
    createCharacterElem(emailaddr_elem, contact_dict["EMail Address"])

    role_elem = ET.SubElement(ci_responseaprty_elem, "{" + namespaces["gmd"] + "}role")
    setGMXCodeElemAttributes(role_elem, role, "CI_RoleCode")

# MAIN FUNCTION TO CRETE XML ELEMENTS BASED ON PATH LIST
def createElements(element_path):
    parent = iso_troot

    for elem in element_path:
        # FIND ALL ELEMENTS MATCHING NAME UNDER PARENT
        elements = parent.findall(elem, namespaces)

        # CHECK TO MAKE SURE IF ONLY ONE ELEMENT EXISTS. SET element TO THAT ELEMENT
        if len(elements) == 1:
            element = parent.find(elem, namespaces)

        # CREATE ELEMENT IF IT DOESN"T EXIST
        if len(elements) == 0:
            ns = namespaces[elem.split(":")[0]]
            element = ET.SubElement(parent, "{" + ns + "}" + elem.split(":")[1])

        # THE FOLLOWING IF STATEMENTS PROVIDE DIFFERENT FUNCTIONALITY BASED ON WHATEVER PATH WAS PASSED TO FUNCTION

        # SET METADATA LANGUAGE ELEMENT
        if element_path[0] == "gmd:language":
            codelistlocation = r"http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#LanguageCode"
            languagecode_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}" + "LanguageCode")
            languagecode_elem.set("codeList", codelistlocation)
            languagecode_elem.set("codeListValue", language)
            languagecode_elem.set("codeSpace", "ISO639-2")
            languagecode_elem.text = language

        # SET HIERARCHY ELEMENT
        elif element_path[0] == "gmd:hierarchyLevel":
            setGMXCodeElemAttributes(element, "dataset", "MD_ScopeCode")

        # CREATE CONTACT TREE
        elif elem == "gmd:contact":
            createContactTree(element, metadata_contact, "pointOfContact")

        # SET METADATA MODIFIED DATE
        elif elem == "gco:Date" and parent.tag == "{" + namespaces["gmd"] + "}dateStamp":
            currentdate = datetime.now()
            formatted_date = currentdate.strftime('%Y-%m-%dT%H:%M:%S')  # 2017-05-31T11:35:23
            element.text = formatted_date

        # CREATE CITATION SUBTREE UNDER identificationInfo ELEMENT
        elif elem == "gmd:CI_Citation":
            def createOrganizationElement(ele, val, type):
                cited_reponse_party_elem = ET.SubElement(ele,
                                                         "{" + namespaces["gmd"] + "}citedResponsibleParty")
                cirespon_party_elem = ET.SubElement(cited_reponse_party_elem,
                                                    "{" + namespaces["gmd"] + "}CI_ResponsibleParty")
                org_name_elem = ET.SubElement(cirespon_party_elem, "{" + namespaces["gmd"] + "}organisationName")
                createCharacterElem(org_name_elem, val)
                setGMXCodeElemAttributes(cirespon_party_elem, type, "CI_RoleCode")

            # CREATE TITLE ELEMENT
            title_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}title")
            createCharacterElem(title_elem, title)

            # CREATE PUBLICATION DATE
            parentdate_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}date")
            cidate_elem = ET.SubElement(parentdate_elem, "{" + namespaces["gmd"] + "}CI_Date")
            date_elem = ET.SubElement(cidate_elem, "{" + namespaces["gmd"] + "}date")
            pubdate_elem = ET.SubElement(date_elem, "{" + namespaces["gco"] + "}Date")
            pubdate_elem.text = publicationDate
            date_type_elem = ET.SubElement(cidate_elem, "{" + namespaces["gmd"] + "}dateType")
            setGMXCodeElemAttributes(date_type_elem, "publication", "CI_DateTypeCode")

            # CREATE PUBLISHER ELEMENTS
            createOrganizationElement(element, publisher, "publisher")

            # CREATE ORIGINATOR ELEMENTS
            for originator in originators:
                createOrganizationElement(element, originator, "originator")

            # CREATE PRESENTATION FORM ELEMENT
            presentationform_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}presentationForm")
            setGMXCodeElemAttributes(presentationform_elem, presentation_form_code, "CI_PresentationFormCode")

        # SET DATASET CONSTRAINTS. ACCESS AND USAGE CONTRAINTS ARE GROUPED INTO OTHER CONTRAINTS
        elif elem == "gmd:otherConstraints":
            createCharacterElem(element, isoconst_text)

        elif elem == "gmd:MD_DataIdentification" and element_path[-1] == "gmd:MD_DataIdentification":
            # SET LANGUAGE VALUE
            language_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}language")
            setGMXCodeElemAttributes(language_elem, language, "LanguageCode")

            # SET ABSTRACT VALUE
            abstract_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}abstract")
            createCharacterElem(abstract_elem, abstract)

            # SET MD PROGRESS VALUE
            status_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}status")
            setGMXCodeElemAttributes(status_elem, metadata_progress, "MD_ProgressCode")

            # SET MD MAINTENANCE FREQUENCY INFO
            resourcemaint_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}resourceMaintenance")
            md_maintinfo_elem = ET.SubElement(resourcemaint_elem, "{" + namespaces["gmd"] + "}MD_MaintenanceInformation")
            mainandupdatefreq_elem = ET.SubElement(md_maintinfo_elem, "{" + namespaces["gmd"] + "}maintenanceAndUpdateFrequency")
            setGMXCodeElemAttributes(mainandupdatefreq_elem, maintenance_requency_code, "MD_MaintenanceFrequencyCode")

            # SET KEYWORD ELEMENTS
            for type, list in keywordArray.items():
                descriptive_keywords_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}descriptiveKeywords")
                md_keywords_elem = ET.SubElement(descriptive_keywords_elem, "{" + namespaces["gmd"] + "}MD_Keywords")
                for value in list:
                    keyword_elem = ET.SubElement(md_keywords_elem, "{" + namespaces["gmd"] + "}keyword")
                    createCharacterElem(keyword_elem, rltw(value))
                type_elem = ET.SubElement(md_keywords_elem, "{" + namespaces["gmd"] + "}type")
                if "theme" in type:
                    keywordType = "theme"
                elif "place" in type:
                    keywordType = "place"
                setGMXCodeElemAttributes(type_elem, keywordType, "MD_KeywordTypeCode")

                thesaurusname_elem = ET.SubElement(md_keywords_elem, "{" + namespaces["gmd"] + "}thesaurusName")
                cicitation_elem = ET.SubElement(thesaurusname_elem, "{" + namespaces["gmd"] + "}CI_Citation")
                thesetitle_elem = ET.SubElement(cicitation_elem, "{" + namespaces["gmd"] + "}title")
                if "LCSH" in type:
                    thesaurus = "LCSH"
                elif "GEOnet" in type:
                    thesaurus = "GEOnet"
                else:
                    thesaurus = "None"
                createCharacterElem(thesetitle_elem, thesaurus)

            # ISO 19115 SUBJECT KEY VALUES
            for topic in themeKey_ISOTopics:
                topiccategory_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}topicCategory")
                mdtopiccategory_elem = ET.SubElement(topiccategory_elem, "{" + namespaces["gmd"] + "}MD_TopicCategoryCode")
                mdtopiccategory_elem.text = topic

            # SPATIAL REPRESENTATION TYPE (vector, grid, tin,  textTable, steroModel, video officially supported)
            spatialrepresentationtype_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}spatialRepresentationType")
            setGMXCodeElemAttributes(spatialrepresentationtype_elem, spatial_representation_type_code, "MD_SpatialRepresentationTypeCode")

            # SET SPATIAL EXTENT
            spatial_extent_parent_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}extent")
            ex_extent_elem = ET.SubElement(spatial_extent_parent_elem, "{" + namespaces["gmd"] + "}EX_Extent")
            geographicelem_elem = ET.SubElement(ex_extent_elem, "{" + namespaces["gmd"] + "}geographicElement")
            bounding_box_elem = ET.SubElement(geographicelem_elem, "{" + namespaces["gmd"] + "}EX_GeographicBoundingBox")

            def setSpatialBoundsValues(bounds, value):
                bounds_elem = ET.SubElement(bounding_box_elem, "{" + namespaces["gmd"] + "}" + bounds)
                decimal_elem = ET.SubElement(bounds_elem, "{gco}Decimal")
                decimal_elem.text = value

            setSpatialBoundsValues("westBoundLongitude", str(ds_extent["xmin"]))
            setSpatialBoundsValues("eastBoundLongitude", str(ds_extent["xmax"]))
            setSpatialBoundsValues("southBoundLatitude", str(ds_extent["ymin"]))
            setSpatialBoundsValues("northBoundLatitude", str(ds_extent["ymax"]))

            # SET TEMPORAL EXTENT
            temporal_extent_parent_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}extent")
            ex_extent_elem = ET.SubElement(temporal_extent_parent_elem, "{" + namespaces["gmd"] + "}EX_Extent")
            temporalelement_elem = ET.SubElement(ex_extent_elem, "{" + namespaces["gmd"] + "}temporalElement")
            ex_temporalextent_elem = ET.SubElement(temporalelement_elem, "{" + namespaces["gmd"] + "}EX_TemporalExtent")
            textent_elem = ET.SubElement(ex_temporalextent_elem, "{" + namespaces["gmd"] + "}extent")
            if "beg_date" in dateOfContent:
                time_perd_elem = ET.SubElement(textent_elem, "{" + namespaces["gml"] + "}TimePeriod")
                beg_pos_elem = ET.SubElement(time_perd_elem, "{" + namespaces["gml"] + "}beginPosition")
                end_pos_elem = ET.SubElement(time_perd_elem, "{" + namespaces["gml"] + "}endPosition")
                beg_pos_elem.text = dateOfContent["beg_date"]
                end_pos_elem.text = dateOfContent["end_date"]
            elif "instant_date" in dateOfContent:
                time_inst_elem = ET.SubElement(textent_elem, "{" + namespaces["gml"] + "}TimeInstant")
                tim_pos_elem = ET.SubElement(time_inst_elem, "{" + namespaces["gml"] + "}timePosition")
                instant_date = dateOfContent["instant_date"]
                tim_pos_elem.text = instant_date

        # SET SPATIAL REPRESENTATION INFO FOR VECTOR DATASET
        elif elem == "gmd:MD_GeometricObjects":
            geometricobjtype_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}geometricObjectType")
            setGMXCodeElemAttributes(geometricobjtype_elem, objecttype, "MD_GeometricObjectTypeCode")

            geometricobjcount_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}geometricObjectCount")
            integer_elem = ET.SubElement(geometricobjcount_elem, "{" + namespaces["gco"] + "}Integer")
            integer_elem.text = numobjects

        # SET SPATIAL REPRESENTATION INFO FOR RASTER DATASET
        elif elem == "gmd:MD_Georectified":
            numberdimensions_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}numberOfDimensions")
            integer_elem = ET.SubElement(numberdimensions_elem, "{" + namespaces["gco"] + "}Integer")
            integer_elem.text = len(dimension)

            for k, v in dimensions.items():
                axisdimensionproperties_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}axisDimensionProperties")
                md_dimension_elem = ET.SubElement(axisdimensionproperties_elem, "{" + namespaces["gmd"] + "}MD_Dimension")
                dimensionname_elem = ET.SubElement(md_dimension_elem, "{" + namespaces["gmd"] + "}dimensionName")
                dimnametypecode_elem = ET.SubElement(dimensionname_elem, "{" + namespaces["gmd"] + "}MD_DimensionNameTypeCode")
                dimnametypecode_elem.text = v
                dimensionsize_elem = ET.SubElement(axisdimensionproperties_elem, "{" + namespaces["gmd"] + "}MD_Dimension")
                integer_elem = ET.SubElement(dimensionsize_elem, "{" + namespaces["gco"] + "}Integer")
                integer_elem.text = 1

            cellgeometry_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}cellGeometry")
            setGMXCodeElemAttributes(cellgeometry_elem, "area", "MD_CellGeometryCode")

        # CREATE DISTRIBUTOR INFO
        elif elem == "gmd:MD_Distributor":
            distribcontact_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}distributorContact")
            createContactTree(distribcontact_elem, dist_contact, "distributor")

            distribformat_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}distributorFormat")
            md_format_elem = ET.SubElement(distribformat_elem, "{" + namespaces["gmd"] + "}MD_Format")
            formatname_elem = ET.SubElement(md_format_elem, "{" + namespaces["gmd"] + "}name")
            createCharacterElem(formatname_elem, distformat)
            version_elem = ET.SubElement(md_format_elem, "{" + namespaces["gmd"] + "}version")
            createCharacterElem(version_elem, "Unknown")

            distribtransfer_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}distributorTransferOptions")
            MD_DigitalTransferOptions = ET.SubElement(distribtransfer_elem, "{" + namespaces["gmd"] + "}MD_DigitalTransferOptions")
            online_elem = ET.SubElement(MD_DigitalTransferOptions, "{" + namespaces["gmd"] + "}onLine")
            ci_onlineres_elem = ET.SubElement(online_elem, "{" + namespaces["gmd"] + "}CI_OnlineResource")
            linkage_elem = ET.SubElement(ci_onlineres_elem, "{" + namespaces["gmd"] + "}linkage")
            url_elem = ET.SubElement(linkage_elem, "{" + namespaces["gco"] + "}URL")
            url_elem.text = purl

        # SET URI ELEMENT
        elif elem == "gmd:dataSetURI":
            createCharacterElem(element, purl)

        # SET PROJECTION CODE AND CODE SPACE (EPSG)
        elif elem == "gmd:RS_Identifier":
            code_elem = ET.SubElement(parent, "{" + namespaces["gmd"] + "}code")
            createCharacterElem(code_elem,referenceSystemCode)
            codespace_elem = ET.SubElement(parent, "{" + namespaces["gmd"] + "}codeSpace")
            createCharacterElem(codespace_elem, referenceSystemCodeSpace)
            version_elem = ET.SubElement(parent, "{" + namespaces["gmd"] + "}version")
            createCharacterElem(version_elem, referenceSystemVersion)

        # CREATE LINEAGE ELEMENT IDENTIFYING THE OPERATION PERFORMED IN THIS SCRIPT
        elif elem == "gmd:LI_Lineage":
            processstep_elem = ET.SubElement(element, "{" + namespaces["gmd"] + "}processStep")
            li_processstep_elem = ET.SubElement(processstep_elem, "{" + namespaces["gmd"] + "}LI_ProcessStep")
            description_elem = ET.SubElement(li_processstep_elem, "{" + namespaces["gmd"] + "}description")
            process_description = "Metadata for this dataset has been updated or modified as part of an ingest into " + \
                                  metadata_contact["Organization Name"] + " geospatial data repository. As part of this" \
                                                                          " process the dataset was renamed from " +\
                                  datasetname.split(".")[0] + " to " + filename + "."
            createCharacterElem(description_elem, process_description)
            datetime_elem = ET.SubElement(li_processstep_elem, "{" + namespaces["gmd"] + "}dateTime")
            gcodatetime_elem = ET.SubElement(datetime_elem, "{" + namespaces["gco"] + "}DateTime")
            currentdate = datetime.now()
            formatted_date = currentdate.strftime('%Y-%m-%dT%H:%M:%S')  # 2017-05-31T11:35:23
            gcodatetime_elem.text = formatted_date

        parent = element

# SIMPLE VALIDATION OF CSV ROW VALUES. BASED ON CSV TEMPLATE
def validateRow(row, num):
    if all(v == "" for v in row.values()):  # is it a fully empty row?
        exit()
    for k,v in row.items():
        if k != "Metadata Fields" and k != "Feature and Attribute Definitions" and len(v)== 0:
            print("ERROR: Empty values in row " + str(num) + ". Exiting")
            exit()


isotemplate = checkpath(vars(parser.parse_args())["xmltemplate"]) if None else "./ISO_Template.xml"
csvfile = checkpath(vars(parser.parse_args())["csvfile"]) if None else "./metadata.csv"
datasetdirectory = vars(parser.parse_args())["datadir"]

# CRAWL DATA DIRECTORY AND CREATE DICTIONARY OF FILES AND FILE PATHS FOR SHP AND TIF FILES
if datasetdirectory != None:
    dsfiles = {}
    checkpath(datasetdirectory)
    # SEARCH DIRECTORY AND TRY TO MATCH DATA SET NAME IN CSV
    for root, dirs, files in os.walk(datasetdirectory):
        for dsf in files:
            if dsf.endswith(".shp") or dsf.endswith(".tif"):
                dsf_path = os.path.join(root, dsf)
                dsfiles[dsf] = dsf_path

# Distributor Info
dist_contact = {"Individual Name": "Geospatial Data Manager",
                "Organization Name": "The University of Arizona Libraries",
                "Street Address": "1510 E University Blvd",
                "City": "Tucson",
                "Admin Area": "Arizona",
                "Postal Code": "85716",
                "Country": "US",
                "EMail Address": "LBRY-uageoportal@email.arizona.edu"}

metadata_contact = dist_contact

# PURL prefix
purl_prefix = r"http://dx.doi.org/10.2458/azu_geo_"

# METADATA SCHEMA INFORMATION
mdstandardname = "ISO 19139 Geographic Information - Metadata - Implementation Specification"
mdstandardversion = "2007"

# GET PARENT DIRECTORY OF THE CSV FILE
parentdir = os.path.abspath(os.path.join(csvfile, os.pardir))

# SET THE XML NAMESPACES AND REGISTER THEM
gmd = "http://www.isotc211.org/2005/gmd"
gml = "http://www.opengis.net/gml"
gco = "http://www.isotc211.org/2005/gco"
gts = "http://www.isotc211.org/2005/gts"

namespaces = {'gmd': gmd,
              'gml': gml,
              'gco': gco,
              'gts': gts}

ET.register_namespace("gmd", gmd)
ET.register_namespace("gml", gml)
ET.register_namespace("gco", gco)
ET.register_namespace("gts", gts)

# PRETTY FORMAT THE XML FILE
pretty_print = lambda f: '\n'.join([line for line in md.parseString(f).toprettyxml().split('\n') if line.strip()])

# ISO 19115 TOPIC CATEGORIES
isoTopicCategories = ["farming", "biota", "boundaries", "climatologyMeteorologyAtmosphere",
                      "economy", "elevation", "environment", "geoscientificInformation",
                      "health", "imageryBaseMapsEarthCover", "intelligenceMilitary",
                      "inlandWaters", "location", "oceans", "planningCadastre", "society",
                      "structure", "transportation", "utilitiesCommunication"]
# XML ELEMENT PATHS
mdlanguage_iso = ["gmd:language"]

mdhierarchylevel_iso = ["gmd:hierarchyLevel"]

mdcontact_iso = ["gmd:contact"]

cicitation_iso = ["gmd:identificationInfo",
                  "gmd:MD_DataIdentification",
                  "gmd:citation",
                  "gmd:CI_Citation"]

constraints_iso = ["gmd:identificationInfo",
                   "gmd:MD_DataIdentification",
                   "gmd:resourceConstraints",
                   "gmd:MD_LegalConstraints",
                   "gmd:otherConstraints"]

identificationinfo_iso = ["gmd:identificationInfo",
                          "gmd:MD_DataIdentification"]

uri_iso = ["gmd:dataSetURI"]


mddatestamp_iso = ["gmd:dateStamp",
                   "gco:Date"]

refsys_iso = ["gmd:referenceSystemInfo",
              "gmd:MD_ReferenceSystem",
              "gmd:referenceSystemIdentifier",
              "gmd:RS_Identifier"]

vectorspatialrepinfo_iso = ["gmd:spatialRepresentationInfo",
                            "gmd:MD_VectorSpatialRepresentation",
                            "gmd:geometricObjects",
                            "gmd:MD_GeometricObjects"]

rasterspatialrepinfo_iso = ["gmd:spatialRepresentationInfo",
                            "gmd:MD_Georectified"]


distributorinfo_iso = ["gmd:distributionInfo",
                       "gmd:MD_Distribution",
                       "gmd:distributor",
                       "gmd:MD_Distributor"]

dataquality_iso = ["gmd:dataQualityInfo",
                   "gmd:DQ_DataQuality",
                   "gmd:lineage",
                   "gmd:LI_Lineage"]

# OPEN CSV FOR READING
with open(csvfile) as f:
    reader = csv.DictReader(f)
    rowcount = 0
    # ITERATE ROWS. ALL ROWS THAT AREN'T FIELD IDENTIFIERS, VALUE SPECIFIERS, OR EXAMPLES ARE SKIPPED
    for row in reader:
        rowcount +=1
        if row['Metadata Fields'] != 'Metadata Fields' and row['Metadata Fields'] != 'Values' and row['Metadata Fields'] != 'Example':
            validateRow(row, rowcount)
            datasetname = row["Dataset Name"]
            # LOCATE THE ACTUAL DATASET PATH BASED ON FILE NAME. IF A DIRECTORY IS SPECIFIED, MATCH TO A FILE IN THAT
            #   DIRECTORY. IF NOT, USE PARENT DIRECTORY OF CSV FILE
            if datasetdirectory != None:
                ds_path = dsfiles[datasetname]
            else:
                ds_path = parentdir + "\\" + datasetname
                if not os.path.exists(ds_path):
                    print("ERROR: Dataset cannot be found. Not in the same directory at CSV.")
                    exit()

            if datasetname.endswith(".shp"):
                dataset_type = "vector"
            elif datasetname.endswith(".tif"):
                dataset_type = "raster"
            else:
                print("ERROR: Unknown Dataset Type for" + datasetname + ". Should be shp or tif). Exiting.")
                exit()

            title = row['Title']  # DONE Field Value

            #  IF DATE IS A SPAN, SHOULD BE INDICATED WITH 'TO' (E.G. 2013 TO 2015)
            title_parse = title.split(",")
            # THE NEW FILE NAME THAT WILL BE CREATED WILL BE BASED ON THE TITLE VALUE AND
            #   FOLLOWS PLACE_THEME_DATE FORMAT.
            #   E.G. FOR THE TITLE "Rivers, Arizona, 1993", THE FILE NAME WOULD BE Arizona_Rivers_1993
            filename = title_parse[1] + "_" + title_parse[0] + "_" + title_parse[2]
            for character in filename:
                if character.lower() not in "abcdefghijklmnopqrstuvwxyz0123456789_":
                    filename = filename.replace(character, "")

            abstract = row['Abstract']
            # IF MULTIPLE ORIGINATORS, THEY'LL BE SEPARATED BY COMMAS
            originators = row['Originator(s)'].split(",")
            collection = row['Collection/Series Identification']
            if collection != "":
                collection.split(",")
            publisher = row['Publisher']
            publicationDate = formatDate(row['Publication Date'])["instant_date"]
            dateOfContent = formatDate(row['Date of Content'])
            accessConstraint = row['Access Constraints']
            useConstraint = row['Use Constraints']
            isoconst_text = accessConstraint + "    |    " + useConstraint

            def processKeywordList(keylist):
                newlist =[]
                for item in keylist:
                    item = rltw(item)
                    newlist.append(item)
                return newlist

            themeKeywords_LCSH = row['Theme Keywords (LCSH)'].split(",")
            themeKey_Free = row["Theme Keyword (Free Text)"].split(",")
            placeKeywords_GEOnet = row['Place Keywords (GEOnet)'].split(",")
            placeKeywords_LCSH = row['Place Keywords (LCSH)'].split(",")
            keywordArray = {"themeLCSH": themeKeywords_LCSH, "themeFree": themeKey_Free, "placeGEOnet":placeKeywords_GEOnet, "placeLCSH": placeKeywords_LCSH}

            themeKey_ISOTopics = row['Topic Categories (ISO 19115)'].replace(" ","").split(",")
            for themeCode in themeKey_ISOTopics:
                if themeCode not in isoTopicCategories:
                    print(
                        "ERROR: Theme Keyword \'" + themeCode + "\' is invalid. Must be one of " + r"https://www2.usgs.gov/science/about/thesaurus-full.php?thcode=15")
                    exit()
            # ATTRIBUTES WILL BE A LIST OF ATTRIBUTES ASSIGNED WITH = AND SEPARATED BY COMMAS
            #  e.g. zip5=US Zipcode, muKey=Geologic Key Code
            # NOT CURRENTLY SUPPORTED FOR ISO
            attributeDefinitions = row['Feature and Attribute Definitions'].split(",") if len(row['Feature and Attribute Definitions']) > 0 else []

            for featureDef in attributeDefinitions:
                    attribute = rltw(featureDef.split("=")[0])
                    attributeDef = rltw(featureDef.split("=")[1])

            if dataset_type == "vector":
                ds_extent = getVectorExtent(ds_path)
                layerinfo = getLayerInfo(ds_path)
                objecttype = layerinfo["Type"]
                numobjects = layerinfo["Number of Features"]
                spatial_representation_type_code = "vector"
                spatialrepinfo_iso = vectorspatialrepinfo_iso
                distformat = "Shapefile"
            elif dataset_type == "raster":
                ds_extent = getRasterExtent(ds_path)
                # NOTE: ONLY SUPPORTING MAX OF 4 DIMENSIONS HERE (X,Y,Z,TIME) WITH SINGLE DIMENSION SIZE FOR EACH.
                #   MORE COMPLEX DIMENSION TYPES HERE: http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml
                num_dimensions = ""
                dimension_size = 1
                dimensions = {}
                for dimension in range(1, num_dimensions + 1):
                    if dimension == 1:
                        dimensions[dimension] = "row"
                    elif dimension == 2:
                        dimensions[dimension] = "column"
                    elif dimension == 3:
                        dimensions[dimension] = "vertical"
                    elif dimension == 4:
                        dimensions[dimension] = "time"
                spatial_representation_type_code = "grid"
                spatialrepinfo_iso = rasterspatialrepinfo_iso
                distformat = "GEOTiff"

            referenceSystemCode = getEPSGCode(ds_path)
            referenceSystemCodeSpace = "EPSG"
            referenceSystemVersion = "9.2"

            currentTime = datetime.now()

            presentation_form_code = "mapDigital"
            metadata_progress = "completed"
            maintenance_requency_code = "notPlanned"

            language = "eng"

            purl = purl_prefix + filename.lower()

            scope_code = "dataset"

            iso_tree = ET.parse(isotemplate)
            iso_troot = iso_tree.getroot()

            createElements(mdlanguage_iso)
            createElements(mdhierarchylevel_iso)
            createElements(mdcontact_iso)
            createElements(mddatestamp_iso)
            createElements(cicitation_iso)
            createElements(constraints_iso)
            createElements(identificationinfo_iso)
            createElements(spatialrepinfo_iso)
            createElements(refsys_iso)
            createElements(distributorinfo_iso)
            createElements(dataquality_iso)
            createElements(uri_iso)

            # WRITE NEW XML TREE TO FILE
            writeToFile(iso_tree, filename)
            print("Finished with ", filename)