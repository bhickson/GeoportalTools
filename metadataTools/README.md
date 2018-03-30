CSV to ISO 19139 XML Builder
============================

Description
-----------
Python script that takes a given structured csv file (metadata.csv) and converts all rows with fully filled values to an xml metadata file following the ISO 19139 geospatial metadata schema.  Each XML file is built from the ISO19139_template.xml file.

This conversion was written for metadata that will be held in a data repository and follows criteria outlined in the by the OpenGeoportal Metadata Working Group General Best Practices document (draft).


Optional Arguments
------------------
    -x  --xmltemplate    Location of the XML template file. Defaults to current directory.
    -c  --csvfile        Location of the csv file where metadata values are held. Defaults to current directory.
    -d  --datadir        Location of the data directory where actual datasets are held. This directory will be crawled and the names of all .shp (vector) and .tif (raster) files matched to the "Dataset Name" column in the csv file. This is mandatory as certain intrincic characteristic of the data (e.g. projection, extent, number of bands or number of features) are derived from the actual dataset itself.
	-r  --rename         True/False value indicating if the input datset (shp or tif should be copied and renamed to a folder RenamedDatasets in the parent dir of --csvfile argument. Default is False

	
Example
-------
python CSVtoISO19139.py --xmltemplate="./xmltemplate.xml" --csvfile="./mymetadata.csv" --datadir="../mydata" --rename=True


Important items of Note
-----------------------
 - Fill out the appropriate distributor contact info in the dist_contact dictionary variable.
 - The new file name (filename) created is derived from the value of the "Title" column in the filled in the csv and constructed following a theme_location_date schema.
 - PURL values are assigned based on the file name (filename) and PURL prefix (purl_prefix) values. This will be dependent on institutional workflows for PURL generation.
