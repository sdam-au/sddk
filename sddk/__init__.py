import warnings
warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)

import requests
import os
import json
import pandas as pd
import getpass
import matplotlib.pyplot as plt
import plotly
import kaleido
import geopandas as gpd
import shapely
import plotly.graph_objects as go
import sys
import io
from bs4 import BeautifulSoup
#import pyarrow.feather as feather


def test_package():
    print("here we are right now - May 26, 11:10")

###
# ORIGINAL VERSION OF THE PACKAGE, USING "conf"
# search below for cloudSession() class, containing some simplifications
####

def configure_session_and_url(shared_folder_name=None, owner=None): ### insert group folder name or leave empty for personal root
    '''
    interactively setup your sciencedata.dk homeurl, username and password
    in the case of shared folder, inquire for its owner as well
    check functionality and redirections
    '''
    ### set username and password
    username = input("sciencedata.dk username (format '123456@au.dk'): ")
    password = getpass.getpass("sciencedata.dk password: ")
    ### establish a request session
    s = requests.Session()
    s.auth = (username, password)
    sciencedata_homeurl_alternatives = ["https://sciencedata.dk/","https://silo1.sciencedata.dk/","https://silo2.sciencedata.dk/","https://silo3.sciencedata.dk/","https://silo4.sciencedata.dk/"]
    for sciencedata_homeurl_root in sciencedata_homeurl_alternatives:
        if s.get(sciencedata_homeurl_root + "files/").ok:
            root_folder_url = sciencedata_homeurl_root + "files/"
            ### SETTING FOR SHARED FOLDER - if their name is passed in: 
            if shared_folder_name != None:
                shared_folder_owner_url = root_folder_url + shared_folder_name + "/"
                if s.get(shared_folder_owner_url).ok: ### if you are owner of the shared folder 
                    root_folder_url = shared_folder_owner_url ### use the url as the endpoint
                    print("connection with shared folder established with you as its owner")
                else: # otherwise use endpoint for "shared with me"
                    if owner==None:
                        owner = input("\"" + shared_folder_name + "\" owner's username: ") ### in the case Vojtech is folder owner
                    shared_folder_member_url = sciencedata_homeurl_root + "sharingin/" + owner + "/" + shared_folder_name + "/" 
                    try:
                        redirection = s.get(shared_folder_member_url, allow_redirects=False).headers["Location"]
                        if redirection != None:
                            shared_folder_member_url = redirection + "/"
                    except:
                        pass
                    if s.get(shared_folder_member_url).ok:
                        root_folder_url = shared_folder_member_url
                        print("connection with shared folder established with you as its ordinary user")
                    else:
                        print("connection with shared folder failed")
        break
    print("endpoint variable has been configured to: " + root_folder_url)
    return (s, root_folder_url)

configure =  configure_session_and_url

def make_data_from_object(python_object, file_ending):
    '''
    process the object you want to write
    '''
    if isinstance(python_object, str):
            return (type(python_object), python_object.encode('utf-8'))
    if isinstance(python_object, pd.core.frame.DataFrame): ### if it is pandas dataframe
        if file_ending == "json":
            with open('temp.json', 'w', encoding='utf-8') as file:
                python_object.to_json(file, force_ascii=False)
            return (type(python_object), open("temp.json", "rb"))
        if file_ending == "geojson":
            if isinstance(python_object, gpd.geodataframe.GeoDataFrame):
                return (type(python_object), json.dumps(gdf_to_geojson(python_object)))
        if file_ending == "json":
            with open('temp.json', 'w', encoding='utf-8') as file:
                python_object.to_json(file, force_ascii=False)
            return (type(python_object), open("temp.json", "rb"))
        if file_ending == "feather":
            for column in python_object.columns: # to avoid problems with encoding, lets check that everything is utf-8
                try: 
                    python_object[column] = python_object[column].str.encode("utf-8")
                except: 
                    python_object[column] = python_object[column]  
            python_object.to_feather("temp.feather")
            return (type(python_object), open("temp.feather", "rb"))
        if file_ending == "csv":
            python_object.to_csv("temp.csv")
            return (type(python_object), open("temp.csv", 'rb'))
    if isinstance(python_object, dict):
        return (type(python_object), json.dumps(python_object))
    if isinstance(python_object, list):
        return (type(python_object), json.dumps(python_object))
    if isinstance(python_object, plt.Figure):
        if file_ending == "eps":
            python_object.savefig('temp.eps', dpi=python_object.dpi)
            return (type(python_object), open("temp.eps", 'rb'))
        else:
            python_object.savefig('temp.png', dpi=python_object.dpi)
            return (type(python_object), open("temp.png", 'rb'))
    if isinstance(python_object, plotly.graph_objs._figure.Figure):
        python_object.write_image("temp.png") 
        return (type(python_object), open("temp.png", 'rb'))
    else:
        print("The function does not support " + str(type(python_object)) + " type of objects. Change the format of your data.")



def gdf_to_geojson(gdf_input):
    # serialize geometry:
    gdf = gdf_input.copy()
    gdf["geometry"] = gdf["geometry"].apply(lambda x: eval(json.dumps(shapely.geometry.mapping(x))))
    # gdf into dict object in geojson structure:
    for col in gdf.columns:
        if list in [type(ins) for ins in gdf[col]]:
            gdf[col] = gdf[col].apply(lambda x: str(x))
    dict_list_object = [{"type" : "Feature", "geometry" : el["geometry"], "properties": {key:val for key, val in el.items() if key != 'geometry'}} for el in gdf.to_dict("records")]
    geojson_structure = {"type": "FeatureCollection", "features": dict_list_object}
    return geojson_structure

def check_path(path_and_filename, conf):
    while not conf[0].get(conf[1] + path_and_filename.rpartition("/")[0]).ok:
        path_and_filename = input("The path is not valid. Try different path and filename: ")
    if conf[0].get(conf[1] + path_and_filename.rpartition("/")[0]).ok:
        return path_and_filename
    else:
        print("Sorry, it is still not okay.")

def check_filename(path_and_filename, conf): 
    '''
    check whether there  exist a file with the same name
    '''
    if conf[0].get(conf[1] + path_and_filename).ok: ### if there already is a file with the same name
        print("A file with the same name (\"" + path_and_filename.rpartition("/")[2] + "\") already exists in this location.")
        approved_name = input("Press Enter to overwrite it or choose different path and filename: ")
        if len(approved_name) == 0: 
            approved_name = path_and_filename
    else:
        approved_name = path_and_filename           
    return approved_name

def write_file(path_and_filename, python_object, conf=None):
    '''
    write file to specified location
    '''
    if conf==None:
        shared_folder = input("Type shared folder name or press Enter to skip: ")
        if shared_folder != "":
            conf = configure_session_and_url(shared_folder)
        else:
            conf = configure_session_and_url()
    s = conf[0]
    sddk_url = conf[1]
    path_and_filename = check_path(path_and_filename, conf)
    approved_name = check_filename(path_and_filename, conf)
    file_ending = approved_name.rpartition(".")[2]
    data_processed = make_data_from_object(python_object, file_ending)
    try:
        if not approved_name.rpartition(".")[2] in ["txt", "json", "geojson", "csv", "png", "eps","feather"]:
            new_filename_ending = input("Unsupported file format. Type either \"txt\", \"csv\", \"json\", \"geojson\", \"feather\", \"eps\", or \"png\": ")
            approved_name = approved_name.rpartition(".")[0] + "." + new_filename_ending
            approved_name = check_filename(approved_name) ### check whether the file exists for the second time (the ending changed)
        s.put(sddk_url + approved_name, data=data_processed[1])
        try:
            os.remove("temp." + file_ending)
        except:
            pass
        print("Your " + str(data_processed[0]) + " object has been succefully written as \"" + sddk_url + approved_name + "\"")
    except:
        print("Something went wrong. Check path, filename and object.")


def read_file(path_and_filename, object_type, conf=None, public_folder=None):
    if isinstance(conf, str):
            print("reading file located in a public folder")
            conf = (requests.Session(), "https://sciencedata.dk/public/" + conf + "/")
    else:
        if conf==None:
            if "public/" in path_and_filename:
                print("reading a publicly shared file")
                conf = (requests.Session(), "")
            else:
                conf = configure_session_and_url()
    s = conf[0]
    sddk_url = conf[1]
    if "https" in path_and_filename:
        sddk_url = ""
    response = s.get(sddk_url + path_and_filename)
    if response.ok:
        try: 
            if object_type == "str":
                object_to_return = response.text
            if object_type == "df":
                if ".csv" in path_and_filename:
                    object_to_return = pd.read_csv(io.StringIO(response.text), index_col=0)
                elif ".json" in path_and_filename:
                    object_to_return = pd.DataFrame(response.json())
                elif ".feather" in path_and_filename:
                    object_to_return = pd.read_feather(io.BytesIO(response.content))
                    for column in object_to_return.columns:
                        try:
                            object_to_return[column] = object_to_return[column].str.decode("utf-8")
                        except:
                            object_to_return[column] = object_to_return[column]
                else:
                    object_to_return = pd.DataFrame(response.json())
            if object_type == "gdf":
                object_to_return = gpd.read_file(io.BytesIO(response.content), driver='GeoJSON')
            if object_type == "dict":
                object_to_return = json.loads(response.content)
            if object_type == "list":
                object_to_return = json.loads(response.content)
            return object_to_return
        except:
            print("file import failed")
    else:
        print("file has not been found; check filename and path.")

def list_filenames(directory="", filetype="", conf=None):
    if conf==None:
        conf = configure_session_and_url()
    resp = conf[0].get(conf[1] + directory)
    soup = BeautifulSoup(resp.content, "html.parser")
    if "." not in filetype:
        filetype = "." + filetype
    filenames = []
    for a in soup.find_all("a"):
            a_str = str(a.get_text())
            if filetype in a_str:
                    filenames.append(a_str)
    return filenames

class cloudSession:
    def __init__(self, provider=None, shared_folder_name=None, owner=None): ### insert group folder name or leave empty for personal root
        '''
        interactively setup your sciencedata.dk homeurl, username and password
        in the case of shared folder, inquire for its owner as well
        check functionality and redirections
        '''
        if ("sciencedata.dk" in str(provider)) or (provider == None):
                    ### set username and password
            username = input("Your ScienceData username (e.g. '123456@au.dk'): ")
            password = getpass.getpass("Your ScienceData password: ")
            ### establish a request session
            s = requests.Session()
            s.auth = (username, password)
            sciencedata_homeurl_alternatives = ["https://sciencedata.dk/","https://silo1.sciencedata.dk/","https://silo2.sciencedata.dk/","https://silo3.sciencedata.dk/","https://silo4.sciencedata.dk/"]
            for sciencedata_homeurl_root in sciencedata_homeurl_alternatives:
                if s.get(sciencedata_homeurl_root + "files/").ok:
                    root_folder_url = sciencedata_homeurl_root + "files/"
                    ### SETTING FOR SHARED FOLDER - if their name is passed in: 
                    if shared_folder_name != None:
                        shared_folder_owner_url = root_folder_url + shared_folder_name + "/"
                        if s.get(shared_folder_owner_url).ok: ### if you are owner of the shared folder 
                            root_folder_url = shared_folder_owner_url ### use the url as the endpoint
                            print("connection with shared folder established with you as its owner")
                        else: # otherwise use endpoint for "shared with me"
                            if owner==None:
                                owner = input("\"" + shared_folder_name + "\" owner's username: ") ### in the case Vojtech is folder owner
                            shared_folder_member_url = sciencedata_homeurl_root + "sharingin/" + owner + "/" + shared_folder_name + "/" 
                            try:
                                redirection = s.get(shared_folder_member_url, allow_redirects=False).headers["Location"]
                                if redirection != None:
                                    shared_folder_member_url = redirection + "/"
                            except:
                                pass
                            if s.get(shared_folder_member_url).ok:
                                root_folder_url = shared_folder_member_url
                                print("connection with shared folder established with you as its ordinary user")
                            else:
                                print("connection with shared folder failed")
                break
            print("endpoint variable has been configured to: " + root_folder_url)
        if "owncloud.cesnet.cz" in provider:
            user = input("Insert your Username code (a long string of characters and numbers): ")
            password = getpass.getpass("Insert your Password/Token: ")
            s = requests.Session() # create session
            s.auth = (user, password)
            root_folder_url = "https://owncloud.cesnet.cz/remote.php/dav/files/{0}/".format(user)
            if s.get(root_folder_url).ok:
                print("endpoint variable has been configured to: " + root_folder_url)
                
        self.s = s
        self.root_folder_url = root_folder_url
        
    def check_path(self, path_and_filename):
        while not self.s.get(self.root_folder_url + path_and_filename.rpartition("/")[0]).ok:
            path_and_filename = input("The path is not valid. Try different path and filename: ")
        if self.s.get(self.root_folder_url + path_and_filename.rpartition("/")[0]).ok:
            return path_and_filename
        else:
            print("Sorry, it is still not okay.")

    def check_filename(self, path_and_filename): 
        '''
        check whether there  exist a file with the same name
        '''
        if self.s.get(self.root_folder_url + path_and_filename).ok: ### if there already is a file with the same name
            print("A file with the same name (\"" + path_and_filename.rpartition("/")[2] + "\") already exists in this location.")
            approved_name = input("Press Enter to overwrite it or choose different path and filename: ")
            if len(approved_name) == 0: 
                approved_name = path_and_filename
        else:
            approved_name = path_and_filename           
        return approved_name
    
    def write_file(self, path_and_filename, python_object):
        '''
        write file to specified location
        '''
        s = self.s
        cloud_url = self.root_folder_url
        path_and_filename = self.check_path(path_and_filename)
        approved_name = self.check_filename(path_and_filename)
        file_ending = approved_name.rpartition(".")[2]
        data_processed = make_data_from_object(python_object, file_ending)
        try:
            if not approved_name.rpartition(".")[2] in ["txt", "json", "geojson", "csv", "png", "eps","feather"]:
                new_filename_ending = input("Unsupported file format. Type either \"txt\", \"csv\", \"json\", \"geojson\", \"feather\", \"eps\", or \"png\": ")
                approved_name = approved_name.rpartition(".")[0] + "." + new_filename_ending
                approved_name = self.check_filename(approved_name) ### check whether the file exists for the second time (the ending changed)
            s.put(cloud_url + approved_name, data=data_processed[1])
            try:
                os.remove("temp." + file_ending)
            except:
                pass
            print("Your " + str(data_processed[0]) + " object has been succefully written as \"" + cloud_url + approved_name + "\"")
        except:
            print("Something went wrong. Check path, filename and object.")


    def read_file(self, path_and_filename, object_type=None, public_folder=None):
        s = self.s
        cloud_url = self.root_folder_url
        if "https" in path_and_filename:
            cloud_url = ""
        if object_type==None:
            object_type="df"
        if public_folder != None:
            response = s.get("https://sciencedata.dk/public/" + public_folder + "/" + path_and_filename)
        elif "public/" in path_and_filename:
            response = s.get(path_and_filename)
        else:
            response = s.get(cloud_url + path_and_filename)
        if response.ok:
            try:
                if object_type == "str":
                    object_to_return = response.text
                if object_type == "df":
                    if ".csv" in path_and_filename:
                        object_to_return = pd.read_csv(io.StringIO(response.text), index_col=0)
                    elif ".json" in path_and_filename:
                        object_to_return = pd.DataFrame(response.json())
                    elif ".feather" in path_and_filename:
                        object_to_return = pd.read_feather(io.BytesIO(response.content))
                        for column in object_to_return.columns:
                            try:
                                object_to_return[column] = object_to_return[column].str.decode("utf-8")
                            except:
                                object_to_return[column] = object_to_return[column]
                    else:
                        object_to_return = pd.DataFrame(response.json())
                if object_type == "gdf":
                    object_to_return = gpd.read_file(io.BytesIO(response.content), driver='GeoJSON')
                if object_type == "dict":
                    object_to_return = json.loads(response.content)
                if object_type == "list":
                    object_to_return = json.loads(response.content)
                return object_to_return
            except:
                print("file import failed")
        else:
            print("file has not been found; check filename and path.")

    def list_filenames(self, directory="", filetype=""):
        resp = self.s.get(self.root_folder_url + directory)
        soup = BeautifulSoup(resp.content, "html.parser")
        if "." not in filetype:
            filetype = "." + filetype
        filenames = []
        for a in soup.find_all("a"):
                a_str = str(a.get_text())
                if filetype in a_str:
                        filenames.append(a_str)
        return filenames


