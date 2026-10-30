#!/usr/bin/python3

# Author: SomoIT <somoit@somoit.net>

import requests
import json
import html2text
import os
import re
from bs4 import BeautifulSoup
import struct

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

def get_png_dimensions(url):
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    image_data = response.content

    if image_data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError("File is not a valid PNG: " + url)

    width, height = struct.unpack(">II", image_data[16:24])

    return width, height

def upload_drawio_image(url, document_id):
    """
    Download a BookStack Draw.io image into Outline
    as a real attachment, preserving the original PNG.
    """

    data = {
        "url": url,
        "documentId": document_id
    }

    response = requests.post(
        config_data['OUTLINE_BASE_URL'] + "/api/attachments.createFromUrl",
        headers=headers,
        json=data,
        timeout=120
    )

    if response.status_code != 200:
        error_data = response.json()
        raise Exception(
            "Draw.io upload failed: {}".format(
                error_data.get('message', response.text)
            )
        )

    return response.json()['data']

def html_to_markdown(html, document_id=None):
    soup = BeautifulSoup(html, "html.parser")
    drawio_images = []

    for img in soup.find_all("img"):
        src = img.get("src")

        if not src or "/drawio/" not in src.lower():
            continue

        if not document_id:
            continue

        print("          Uploading Draw.io diagram: " + src)

        width, height = get_png_dimensions(src)

        attachment = upload_drawio_image(src, document_id)

        # Create exact Markdown ourselves
        markdown_image = (
            f'![]({attachment["url"]} '
            f'"source=diagrams.net ={width}x{height}")'
        )

        # Replace image with unique placeholder
        placeholder = f"DRAWIO_PLACEHOLDER_{len(drawio_images)}"

        img.replace_with(placeholder)

        drawio_images.append((placeholder, markdown_image))

    h = html2text.HTML2Text()
    h.ignore_links = False

    markdown = h.handle(str(soup))

    # Restore exact Draw.io Markdown
    for placeholder, markdown_image in drawio_images:
        markdown = markdown.replace(placeholder, markdown_image)

    markdown = re.sub(
        r'(https?://[^\s)]*?)-\s+([^/\s)]*)',
        r'\1-\2',
        markdown
    )

    return markdown.replace("%00", "%5BNULL%5D")


def update_document(document_id, text):
    data = {
        "id": document_id,
        "text": text
    }

    response = requests.post(
        config_data['OUTLINE_BASE_URL'] + "/api/documents.update",
        headers=headers,
        json=data
    )

    if response.status_code != 200:
        error_data = response.json()
        print(
            "Document update failed: {}".format(
                error_data.get('message', response.text)
            )
        )
        exit(1)

    return response.json()['data']

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
                outline_page = create_document(
                    bookstack_page['name'],
                    "",
                    outline_shelf['id'],
                    outline_book['id']
                )

                markdown = html_to_markdown(
                    bookstack_page['html'],
                    outline_page['id']
                )

                update_document(outline_page['id'], markdown)
                print(f"(Page)        {Colors.BRIGHT_BLUE}- {bookstack_page['name']}{Colors.RESET}")

            for bookstack_chapter in bookstack_book['chapters']:
                outline_chapter = create_document(bookstack_chapter['name'],"",outline_shelf['id'],outline_book['id'])
                print(f"(Chapter)     {Colors.YELLOW}+ {bookstack_chapter['name']}{Colors.RESET}")

                for bookstack_chapter_page in bookstack_chapter['pages']:
                    print(f"(Page)          {Colors.BRIGHT_BLUE}- {bookstack_chapter_page['name']}{Colors.RESET}" + has_null(bookstack_chapter_page['html']))
                    outline_chapter_page = create_document(
                        bookstack_chapter_page['name'],
                        "",
                        outline_shelf['id'],
                        outline_chapter['id']
                    )

                    markdown = html_to_markdown(
                        bookstack_chapter_page['html'],
                        outline_chapter_page['id']
                    )

                    update_document(
                        outline_chapter_page['id'],
                        markdown
                    )

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
