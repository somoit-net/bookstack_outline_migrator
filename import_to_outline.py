#!/usr/bin/python3

# Author: SomoIT <somoit@somoit.net>

import requests
import json
import html2text
import os

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    BRIGHT_BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

def read_config(file_path):
    global config_data
    config_data = {}

    try:
        with open(file_path, 'r') as configfile:
            for line in configfile:
                if line.strip() and not line.startswith('#'):
                     key, value = line.strip().split('=', 1)
                     config_data[key] = value
    except FileNotFoundError:
        print("Error reading config file (" + file_path + ")")
        exit(1)
    except ValueError:
        print("Invalid config file syntax (" + line.replace("\n","") + ")")
        exit(1)




def html_to_markdown (html):
    h = html2text.HTML2Text()
    h.ignore_links = False  # Set to True to ignore links
    return h.handle(html).replace("%00","%5BNULL%5D")

def has_null (text):
    if "%00" in text:
        return "*"
    else:
        return ""

def check_outline_connection ():

    data = {
        "limit": 5
    }

    response = requests.post(config_data['OUTLINE_BASE_URL'] + "/api/collections.list", headers=headers, json=data)

    if response.status_code != 200:
        error_data = json.loads (response.content.decode("UTF-8"))
        print("Error - Connection check to Outline API failed (" + error_data['message'] +")")
        print()
        exit()

    print("Ok - Checked connection to Outline API")



def create_collection (name, description):

    data = {
        "name": name,
        "description": description
    }

    response = requests.post(config_data['OUTLINE_BASE_URL'] + "/api/collections.create", headers=headers, json=data)
    if response.status_code != 200:
        error_data = json.loads (response.content.decode("UTF-8"))
        print("{} - {} ({})".format(error_data['status'],error_data['error'],error_data['message']))
        exit()

    return response.json()['data']

def create_document (name, html, collection_id, parent_document_id):

    if parent_document_id == None:
        data = {
            "title": name,
            "text": html,
            "collectionId": collection_id,
            "publish": True
        }
    else:
        data = {
            "title": name,
            "text": html,
            "collectionId": collection_id,
            "parentDocumentId": parent_document_id,
            "publish": True
        }

    response = requests.post(config_data['OUTLINE_BASE_URL'] + "/api/documents.create", headers=headers, json=data)
    if response.status_code != 200:
        error_data = json.loads (response.content.decode("UTF-8"))
        print("/api/documents.create - error {} - {} ({})".format(error_data['status'],error_data['error'],error_data['message']))
        exit()

    return response.json()['data']


def read_export_file (file):
    try:
        with open(file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Error reading bookstack export file (" + file + ")")
        exit(1)

def import_data():

    print("\nImporting data to Outline...\n\n")

    export_data = read_export_file(config_data['BOOKSTACK_EXPORT_FILENAME'])

    for bookstack_shelf in export_data:
        print()
        outline_shelf = create_collection(bookstack_shelf['name'],bookstack_shelf['description'])
        print()
        print(f"(Shelf)   {Colors.RED}[[ {bookstack_shelf['name']} ]]{Colors.RESET}")
        for bookstack_book in bookstack_shelf['books']:
            print(f"(Book)      {Colors.GREEN}[ {bookstack_book['name']} ]{Colors.RESET}")
            outline_book = create_document(bookstack_book['name'],bookstack_book['description'],outline_shelf['id'],None)
            for bookstack_page in bookstack_book['pages']:
                outline_page = create_document(bookstack_page['name'],html_to_markdown(bookstack_page['html']),outline_shelf['id'],outline_book['id'])
                print(f"(Page)        {Colors.BRIGHT_BLUE}- {bookstack_page['name']}{Colors.RESET}")

            for bookstack_chapter in bookstack_book['chapters']:
                outline_chapter = create_document(bookstack_chapter['name'],"",outline_shelf['id'],outline_book['id'])
                print(f"(Chapter)     {Colors.YELLOW}+ {bookstack_chapter['name']}{Colors.RESET}")

                for bookstack_chapter_page in bookstack_chapter['pages']:
                    print(f"(Page)          {Colors.BRIGHT_BLUE}- {bookstack_chapter_page['name']}{Colors.RESET}" + has_null(bookstack_chapter_page['html']))
                    outline_chapter_page = create_document(bookstack_chapter_page['name'],html_to_markdown(bookstack_chapter_page['html']),outline_shelf['id'],outline_chapter['id'])

    print("Import finished")

if __name__ == "__main__":

    config_file = os.path.dirname(os.path.abspath(__file__)) + "/config.txt"
    config_data = {}
    read_config(config_file)

    headers = {
        "Authorization": f"Bearer {config_data['OUTLINE_API_TOKEN']}",
        "Content-Type": "application/json"
    }

    check_outline_connection()
    import_data()
