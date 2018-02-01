import os, json, csv, requests, argparse
"""
import warnings
warnings.filterwarnings("ignore")"""

parser = argparse.ArgumentParser(description="Search through a given directory for all json files named"
                                             " geoblacklight.json and validate their contents against the schema.")
parser.add_argument("-d", "--directory", type=str, help="Location of the directory to crawl", required=True)

args = parser.parse_args()
reposdir = args.directory
if not os.path.exists(reposdir):
    print("Invalid directory given. Exiting")
    exit()


repos = {}
givendir = os.path.dirname(reposdir)
if givendir.startswith("edu."):
    repos[givendir] = reposdir
else:
    for dir in os.listdir(reposdir):
        if dir.startswith("edu."):
            dirpath = os.path.join(reposdir,dir)
            if os.path.isdir(dirpath):
                repos[dir] = dirpath

gblschema = [
        "layer_slug_s",
        "dc_identifier_s",
        "dc_title_s",
        "dc_description_s",
        "dc_rights_s",
        "dct_provenance_s",
        "dct_references_s",
        "layer_id_s",
        "dct_isPartOf_sm",
        "layer_geom_type_s",
        "layer_modified_dt",
        "dc_format_s",
        "dc_language_s",
        "dc_type_s",
        "dc_publisher_s",
        "dc_creator_sm",
        "dc_subject_sm",
        "dct_issued_s",
        "dct_temporal_sm",
        "dct_spatial_sm",
        "solr_geom",
        "solr_year_i",
        "geoblacklight_version",
        ]

def checkURL(url):
    #print(url)
    request = requests.get(url, verify=False)
    try:
        response = request.status_code
        if response == 200:
            return True
        else:
            return False
    except:
        return False

def checkJSON(f):
    enc = 'utf-8'
    try:

        with open(f) as jf:
            jdict = json.load(jf)
            return(jdict)
    except:
        with open(f, 'r', encoding=enc) as jf:
            try:
                jdict = json.load(jf)
                return(jdict)
            except:
                data = jf.read()
                title = data.split("layer_slug_s")[1].split(",")[0]
                print("UNABLE TO PARSE JSON FILE", title, "at", f)
                return False



for repo, directory in repos.items():
    print("STARTING", repo, "REPOSITORY")
    csvpath = reposdir + "/" + repo + ".csv"

    filecount = 0
    invalidcount = 0

    # OPEN CSV OF REPO EVALUATION FOR WRITING
    with open(csvpath, 'w', newline='', encoding='utf8') as outfile:
        wr = csv.writer(outfile, quoting=csv.QUOTE_ALL)

        wr.writerow(
            ["File Path", "Title", "Parseable", "Missing Keys", "Invalid Keys", "Failed URLs", "Publisher Issue", "Creator Issue",
             "Access Issue", "Date Issue"])

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file == "geoblacklight.json":
                    filecount += 1
                    fileinfo = []
                    problem = False
                    parseable = "True"
                    fpath = os.path.join(root,file)
                    json_dict = checkJSON(fpath)
                    if not json_dict:
                        parseable = "False"
                        problem = True
                    else:
                        # CHECK TO SEE IF THERE ARE ANY KEYS IN THE FILE NOT IN THE DICTIONARY gblschema
                        missingkeys = []
                        for key in gblschema:
                            if key not in json_dict:
                                missingkeys.append(key)
                                problem = True

                        unknownkeys = []
                        for key in json_dict.keys():
                            if key not in gblschema:
                                unknownkeys.append(key)
                                problem = True

                        try:
                            title = json_dict["dc_title_s"]
                            references = json.loads(json_dict["dct_references_s"])
                            publisher = json_dict["dc_publisher_s"]
                            date = json_dict["solr_year_i"]
                            creators = json_dict["dc_creator_sm"]
                            access = json_dict["dc_rights_s"]
                        except KeyError:
                            pass

                        pubissue = dateissue = creatorissue = accessissue = "Valid"

                        urlfails = []
                        if json_dict["dc_rights_s"].lower() != "restricted":
                            for k,v in references.items():
                                continue # Remove this line to see if each url exists. May cause port overload
                                if checkURL(v):
                                    urlfails.append(v)

                        try:
                            date = int(date)
                        except:
                            dateissue = "Invalid date: " + date

                        if access.lower() != "public" and access.lower() != "restricted":
                            accessissue = "Invalid Value: " + access

                        illegalchars = ["?"]

                        for char in illegalchars:
                            if char in publisher:
                                pubissue = "Illegal Char: " + char
                            if len(publisher) == 1:
                                pubissue = "Empty"
                            for value in creators:
                                if char in value:
                                    creatorissue = "Illegal Char " + char
                            if len(creators) < 1:
                                creatorissue = "Empty"

                    if pubissue != "Valid" or dateissue != "Valid" or creatorissue != "Valid" or accessissue != "Valid":
                        problem = True

                    if problem == True:
                        invalidcount += 1
                        fileinfo.append(fpath[len(reposdir):])
                        title = title
                        fileinfo.append(title)
                        fileinfo.append(parseable)
                        fileinfo.append(missingkeys)
                        fileinfo.append(unknownkeys)
                        fileinfo.append(urlfails)
                        fileinfo.append(pubissue)
                        fileinfo.append(creatorissue)
                        fileinfo.append(accessissue)
                        fileinfo.append(dateissue)
                        #print(fileinfo)
                        wr.writerow(fileinfo)


    print("FINISHED", repo)
    print("\tNUMBER OF RECORDS:", filecount)
    print("\tINVALID RECORDS:", invalidcount)