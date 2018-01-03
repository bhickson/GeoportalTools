ISO 19139 to JSON (Geoblacklight Schema) Translator
==================================================


Description
-----------
Python script that takes a given directory containing XML files following the ISO 19139 schema and converts them to JSON files formatted to the GeoBlacklight schema. If the tosolr argument is given (True/False) the JSON string is posted to the solr_loc specified in the script.

The output json file and a copy of the original XML (renamed to iso19139.xml) are written to a directory path derived from the fvn-1a hash (32 bit) of the dtaset title.The fvn-1a hash algorythm outputs a 10 digit number, so the directory structure will be split into 3,3,2,2. E.g. if the hash is 3285418445, the directory structure will be 328/541/84/45


Optional Arguments
------------------
    -o  --outdir         Output parent directory where processed files and folders will be created. Defaults to current directory
    -m  --mddir          Location of the CSV file containting metadata information. Defaults to current directory.
    -d  --datadir        Directory location where geospatial datasets reside. These datasets are used to determine the actual bounding box, dataset type, and other instrinsic info. Defaults to the current directory
    -r  --rights         Access rights - should be "Public" or "Restricted". Default is "Public".
    -i  --institution    Institution holding the dataset in their repository. Default is "UArizona".
    -v  --version        Geoblacklight schema version. Default is "1.0".
    -w  --workspace      Geoserver workspace where the dataset is held. Used for OGC services (wms, wcs, wfs). Default is UniversityLibrary
    -u  -mdurl           Prefix for the url where the full xml metadata record can be found. Assumes that the metadata will be held in an OpenGeoMetadata repository on github. Defaults to "https://raw.githubusercontent.com/OpenGeoMetadata/edu." + institution.lower()
    -t  -tosolr          True/False value indicating if the composed JSON should be posted to the url identified by the solr_loc variable. Default is "False".


Example
-------
	python ISO19139toGBLjson.py -o="./repositoryDirectory" -m="../Dataset_Metadata" -d="../DatasetCollections"

Of Note
-------
 - If POSTing constructed json file to solr, the solr_loc variable must be definied in the script
 - If the tosolr argument is passed, the json string will be POSTed in an update request to the solr collection location specified in the solr_loc variable
 - The geosever_loc variable must reflect the geoserver url where the dataset will be access from via WMS, WFS/WCS
 - The list of collections (collections variable) which the records belongs to is derived from the existing directory structure where the xml file is held. E.g. If the XML file is in "./imagery/aerial photographs/USDA/NAIP/" the collection list in the json file will be [imagery, aerial photographs, USDA, NAIP].
 - Script only supports building wms, wfs/wcs, and xml endpoints in dct_references
 - XML and JSON files are assumed to be held in a git hub repo on OpenGeoMetadata that follows the same exact structure of your outdir including a layers.json file.


Refernces
---------
  - GeoBlacklight Schema: https://github.com/geoblacklight/geoblacklight/blob/master/schema/geoblacklight-schema.md
  - Logic of hashed directory structure: https://github.com/OpenGeoMetadata/metadatarepository/issues/3
