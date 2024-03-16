import os
from datetime import datetime

import pandas as pd
import requests
from pandas import DataFrame

from modules.auth_manager import AuthManager

DATETIME = datetime.now().strftime("%d-%m-%Y")


class OneDriveManager:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.access_token = self.auth_manager.get_access_token_default_scopes()
        self.endpoint = self.auth_manager.get_endpoint()
        self.default_header = self.auth_manager.get_default_header(access_token=self.access_token)
        self.current_day = DATETIME

    def get_current_day(self) -> DATETIME:
        return DATETIME

    def upload_file_to_onedrive(self, file_path, current_day=DATETIME, path_after_current_day=None, onedrive_path=None):
        uploading_file_name = os.path.basename(file_path)

        # looks bad, refactor
        if onedrive_path is not None:
            upload_url = self.endpoint + f"drive/items/root:/{onedrive_path}/{uploading_file_name}:/content"
        else:
            if path_after_current_day is None:
                upload_url = self.endpoint + f"drive/items/root:/Holland/reports/{current_day}/{uploading_file_name}:/content"
            else:
                upload_url = self.endpoint + f"drive/items/root:/Holland/reports/{current_day}/{path_after_current_day}/{uploading_file_name}:/content"

        access_token = self.access_token
        headers_octet_stream = {
            'Authorization': access_token,
            'Content-Type': 'application/octet-stream',
        }

        with open(file_path, 'rb') as upload:
            media_content = upload.read()

        response = requests.put(url=upload_url, headers=headers_octet_stream, data=media_content)
        if response.status_code == 201 or response.status_code == 200:
            print(f"File {uploading_file_name} download to OneDrive!")
        else:
            print(f"Сталася помилка при завантаженні файлу на OneDrive!. {response.text}")
        return response

    def upload_list_to_onedrive(self, uploaded_list: list[DataFrame], uploaded_list_path: str):
        column_name = "номер на складі"
        uploaded_list_values = []

        if uploaded_list:
            for df_check in uploaded_list:
                uploaded_list_values.append(df_check[column_name])

        df_uploaded_list_values = pd.DataFrame({column_name: uploaded_list_values})
        df_uploaded_list_values.to_csv(uploaded_list_path, index=False)
        self.upload_file_to_onedrive(file_path=uploaded_list_path, path_after_current_day="Lists")

    def download_basic_reports_to_tmp(self):
        folder_path = "/tmp/text_reports"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        onedrive_path = f"Holland/reports/{self.current_day}/Base reports"
        url = self.endpoint + f"drive/items/root:/{onedrive_path}:/children"
        response = requests.get(url,
                                headers=self.auth_manager.get_default_header(access_token=self.access_token))
        response_json = response.json()
        if "value" in response_json and response_json["value"]:
            for item in response_json["value"]:
                if "basic_report" in item["name"]:
                    download_url = item['@microsoft.graph.downloadUrl']
                    local_file_path = f"{folder_path}/{item['name']}"
                    response = requests.get(download_url)

                    if response.status_code == 200:
                        with open(local_file_path, 'wb') as file:
                            file.write(response.content)
                    else:
                        print(f"Error with download basic report. HTTP status code: {response.status_code}")

    def get_root_folder_json(self, one_drive_url, headers):
        result = requests.get(url=one_drive_url, headers=headers)
        return result.json()

    def get_item_id(self, name, path_in_onedrive="/Holland/reports"):
        url = self.endpoint + f"drive/root:{path_in_onedrive}:/children"
        response = requests.get(url=url, headers=self.default_header)

        data = response.json()
        for item in data["value"]:
            if item["name"] == name:
                return item["id"]

    def download_file_to_tmp(self, path, file_name, is_report=False):
        if is_report:
            download_url = self.endpoint + f"drive/items/{path}/content"
        else:
            download_url = self.endpoint + f"drive/items/root:{path}:/content"
        response = requests.get(download_url,
                                headers=self.auth_manager.get_default_header(access_token=self.access_token))

        if response.status_code == 200:
            if is_report:
                folder_path = "/tmp/text_reports"
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                with open(f"{folder_path}/{file_name}", "wb") as f:
                    f.write(response.content)
            else:
                with open(f"/tmp/{file_name}", "wb") as f:
                    f.write(response.content)
        else:
            print(f"Помилка при завантаженні файлу {file_name}: {response.status_code} - {response.text}")

    def download_reports_to_tmp(self, current_day=DATETIME):
        upload_url = self.endpoint + f"drive/items/root:/Holland/reports/{current_day}:/children"
        response = requests.get(url=upload_url,
                                headers=self.default_header)
        if response.status_code == 200:
            files = response.json().get("value", [])
            for file in files:
                if "basic_report" in file.get("name", "").lower():
                    file_name = file.get("name")
                    file_id = file.get("id")
                    # download_url = self.endpoint + f"drive/items/{file_id}/content"
                    self.download_file_to_tmp(path=file_id, file_name=file_name, is_report=True)
        else:
            print(f"Error in download_reports_to_tmp {response.status_code} - {response.text}")


    def is_list_folder_created(self, current_day=DATETIME) -> bool:
        upload_url = self.endpoint + f"drive/items/root:/Holland/reports/{current_day}:/children"
        response = requests.get(url=upload_url,
                                headers=self.default_header)
        if response.status_code == 200:
            items = response.json().get('value', [])
            return any(item['name'] == 'Lists' and item['folder'] is not None for item in items)
        else:
            return False

    def is_current_day_folder_created(self, current_day=DATETIME):
        upload_url = self.endpoint + f"drive/items/root:/Holland/reports:/children"
        response = requests.get(url=upload_url,
                                headers=self.default_header)
        if response.status_code == 200:
            items = response.json().get('value', [])
            return any(item['name'] == current_day and item['folder'] is not None for item in items)
        else:
            return response.json()

    def create_current_day_folder(self, current_day=DATETIME):
        create_url = self.endpoint + f"drive/items/root:/Holland/reports:children"
        payload = {
            "name": current_day,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        response = requests.post(url=create_url, headers=self.default_header, json=payload)
        return response.json()

    def create_lists_folder(self, current_day=DATETIME):
        create_url = self.endpoint + f"drive/items/root:/Holland/reports/{current_day}:children"
        payload = {
            "name": "Lists",
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        response = requests.post(url=create_url, headers=self.default_header, json=payload)
        return response.json()

# onedrivemanager = OneDriveManager()
# onedrivemanager.get_item_id(name="09-11-2023")
# download_excel_url = onedrivemanager.endpoint + f"drive/items/root:/Holland/Volodumurs_tested_file.xlsx:/content"
# onedrivemanager.download_file_to_tmp(download_url=download_excel_url, file_name="Volodumurs_tested_file.xlsx")
