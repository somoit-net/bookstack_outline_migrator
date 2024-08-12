#!/usr/bin/python3

# Author: SomoIT <somoit@somoit.net>

import requests
import json
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

def check_bookstack_connection ():
    response = requests.get(f"{config_data['BOOKSTACK_BASE_URL']}/api/shelves", headers=headers)
    if response.status_code != 200:
        error_data = json.loads (response.content.decode("UTF-8"))
        print("Error - Connection check to Outline API failed (" + error_data['error']['message'] +")")
        print()
        exit()
    print("Ok - Checked connection to Bookstack API")

def get_all_shelves():
    response = requests.get(f"{config_data['BOOKSTACK_BASE_URL']}/api/shelves", headers=headers)
    return response.json()['data']

def get_shelf(shelf_id):
    response = requests.get(f"{config_data['BOOKSTACK_BASE_URL']}/api/shelves/{shelf_id}", headers=headers)
    return response.json()

def get_book(book_id):
    response = requests.get(f"{config_data['BOOKSTACK_BASE_URL']}/api/books/{book_id}", headers=headers)
    return response.json()

def get_page_content(page_id):
    response = requests.get(f"{config_data['BOOKSTACK_BASE_URL']}/api/pages/{page_id}", headers=headers)
    return response.json()

def export_data():

    print("\nExporting data from bookstack...\n\n")

    # Export Shelves
    shelves = get_all_shelves()
    shelves_data = []
    for shelf_item in shelves:
        shelf = get_shelf(str(shelf_item['id']))
        shelf_data = {
            "id": shelf['id'],
            "name": shelf['name'],
            "description": shelf.get('description', ''),
            "books": []
        }
        print()
        print(f"(Shelf)   {Colors.RED}[[ {shelf_data['name']} ]]{Colors.RESET}")

        for book_reference in shelf['books']:
            book = get_book(book_reference['id'])
            book_data = {
                "id": book['id'],
                "name": book['name'],
                "description": book.get('description', ''),
                "chapters": [],
                "pages": []
            }
            print(f"(Book)      {Colors.GREEN}[ {book_data['name']} ]{Colors.RESET}")

            chapters = [item for item in book['contents'] if item["type"] == "chapter"]
            for chapter in chapters:
                chapter_data = {
                    "id": chapter['id'],
                    "name": chapter['name'],
                    "description": chapter.get('description', ''),
                    "pages": []
                }
                print(f"(Chapter)     {Colors.YELLOW}+ {chapter_data['name']}{Colors.RESET}")

                for page in chapter['pages']:
                    page_with_content = get_page_content(page['id'])
                    chapter_data['pages'].append(page_with_content)
                    print(f"(Page)          {Colors.BRIGHT_BLUE}- {page['name']}{Colors.RESET}")

                book_data["chapters"].append(chapter_data)

            pages = [item for item in book['contents'] if item["type"] == "page"]


            for page in pages:
                page_with_content = get_page_content(page['id'])
                book_data['pages'].append(page_with_content)
                print(f"(Page)        {Colors.BRIGHT_BLUE}- {page['name']}{Colors.RESET}")

            shelf_data["books"].append(book_data)

        shelves_data.append(shelf_data)

    with open(config_data['BOOKSTACK_EXPORT_FILENAME'], "w") as f:
        json.dump(shelves_data, f, indent=4)

    print("Export finished (" + config_data['BOOKSTACK_EXPORT_FILENAME'] + ")")


if __name__ == "__main__":
    config_file = os.path.dirname(os.path.abspath(__file__)) + "/config.txt"
    config_data = {}
    read_config(config_file)
    headers = {
        "Authorization": f"Token {config_data['BOOKSTACK_API_TOKEN_ID']}:{config_data['BOOKSTACK_API_TOKEN_SECRET']}",
        "Content-Type": "application/json"
    }
    check_bookstack_connection()
    export_data()
