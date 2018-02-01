Geoblacklight Validator
============================

Description
-----------
Python script that takes a given directory (assumed to be clone or download of OpenGeoMetadata) and crawls it for files matching name "geoblacklight.json". Found files are parsed (checked for validity) and then the schema is tested.  Currently tests for existence of all declared schema values and the existence of any unknown values (e.g. misspellings like dct_refrences_s). This will cause custom values (e.g. 'georss_polygon_s',  'nyu_addl_format_sm') to get flag.  Also test for valid date in solr_year_i, and missing or illegal characters (e.g. ?) in dc_creator_sm and dc_publisher_s.

Any files flagged as having problems are written to a CSV detailing flagging.


Mandatory Argument
------------------
    -d  --directory         Location of the data directory to crawl

	
Example
-------
python GeoblacklightValidator.py --directory="~/OpenGeoMetadata"

Sample Output
-------------

| File Path                                           | Title                                                        | Parseable | Missing Keys        | Invalid Keys                   | Failed URLs | Publisher Issue | Creator Issue | Access Issue | Date Issue |
|-----------------------------------------------------|--------------------------------------------------------------|-----------|---------------------|--------------------------------|-------------|-----------------|---------------|--------------|------------|
| edu.stanford.purl\bb\033\gt\0615\geoblacklight.json | Important Farmland, San Luis Obispo County, California, 1996 | True      | ['dct_isPartOf_sm'] | ['stanford_rights_metadata_s'] | []          | Valid           | Valid         | Valid        | Valid      |
| edu.stanford.purl\bb\099\zb\1450\geoblacklight.json | Department Boundary: Haute-Garonne, France, 2010             | True      | ['dct_isPartOf_sm'] | ['stanford_rights_metadata_s'] | []          | Valid           | Valid         | Valid        | Valid      |


References
----------
Geoblacklight schema 1.0: 

[https://github.com/geoblacklight/geoblacklight/blob/master/schema/geoblacklight-schema.md](https://github.com/geoblacklight/geoblacklight/blob/master/schema/geoblacklight-schema.md)