Takes a given structured csv (csvfile variable) file and converts all rows with fully filled values to an xml metadata file following the ISO 19139 geospatial metadata schema.

This conversion was written for metadata that will be held in a data repository and follows criteria outlined in the

OF NOTE:
   Fill out the appropriate distributor contact info in the dist_contact dictionary variable.
   The new file name (filename) created is derived from the value of the "Title" filed in the csv
   PURL values are assigned based on the file name (filename) and PURL prefix (purl_prefix) values

 
Script takes arguments for the iso xml template location, csv file of metadata location, and a directory where actual geospatial datasets reside


e.g. ISOtoISO19139.py --xmltemplate="" --csvfile="" --datadir="" 
