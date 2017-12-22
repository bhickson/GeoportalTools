Python script that takes a given directory containing XML files following the ISO 19139 schema and converts them to JSON files formatted to the GeoBlacklight schema. If the tosolr argument is given (True/False) the JSON string is posted to the solrURL specified in the script.

The output json file and a copy of the original XML (renamed to iso19139.xml) are written to a directory path derived from the fvn-1a hash (32 bit) of the dtaset title.The fvn-1a hash algorythm outputs a 10 digit number, so the directory structure will be split into 3,3,2,2. E.g. if the hash is 3285418445, the directory structure will be 328/541/84/45



OF NOTE:
 - If the tosolr argument is passed, the json string will be posted in an update request to the solr url specified in the solrURL variable
 - The list of collections (collections variable) which the records belongs to is derived from the existing directory structure where the xml file is held. E.g. If the XML file is in "./imagery/aerial photographs/USDA/NAIP/" the collection list in the json file will be [imagery, aerial photographs, USDA, NAIP].

 REFERENCES:
  - GeoBlacklight Schema: https://github.com/geoblacklight/geoblacklight/blob/master/schema/geoblacklight-schema.md
  - Logic of hashed directory structure: https://github.com/OpenGeoMetadata/metadatarepository/issues/3
