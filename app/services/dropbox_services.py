import requests
import json


class DropBox:
    
    def __init__(self, token: str) -> None:
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"
        }

    def search_file_or_folders(self, name: str):
        # Searches for files and folders.
        url = "https://api.dropboxapi.com/2/files/search_v2"
        data = {"query": name}
        r = requests.post(url, headers=self.headers, data=json.dumps(data))
        print(r.json())
        return r.json()
    
    def cusrsor_search_file_or_folders(self, cursor: str):
        #  search/continue_v2 (using cursor)
        url = "https://api.dropboxapi.com/2/files/search/continue_v2"
        data = {"cursor": cursor}
        r = requests.post(url, headers=self.headers, data=json.dumps(data))
        print(r.json())
    
    def create_folder(self, path: str):
        #Create a folder at a given path.
        url = "https://api.dropboxapi.com/2/files/create_folder_v2"
        data = {"path": path, "autorename": False}
        r = requests.post(url, headers=self.headers, data=json.dumps(data))
        print(r.json())
        return r.json()
    
    def copy_s3_to_dropbox(self, path: str, s3_url: str):
        url = "https://api.dropboxapi.com/2/files/save_url"
        data = json.dumps({"path": f"{path} {path}" ,"url": s3_url})
        r = requests.post(url, headers=self.headers, data=data)
        print(r.json())
