import json

import requests

from modules.auth_manager import AuthManager
from modules.excel_handler import ExcelHandler
from modules.one_drive_photo_manager import OneDrivePhotoManager
from modules.onedrive_manager import OneDriveManager


class StartProgram:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.excel_handler = ExcelHandler()
        self.onedrive_manager = OneDriveManager()

    def start(self):
        endpoint = self.auth_manager.get_endpoint()
        access_token = self.auth_manager.get_access_token_default_scopes()
        one_drive_url = self.auth_manager.get_endpoint() + "drive/root/children"
        headers = self.auth_manager.get_default_header(access_token=access_token)
        excel_file_name = "sklad.xlsx"

        self.one_drive_photo_manager = OneDrivePhotoManager(endpoint=endpoint,headers=headers, access_token=access_token)

        root_folder_onedrive = self.onedrive_manager.get_root_folder_json(one_drive_url=one_drive_url, headers=headers)

        file_content = self.excel_handler.get_exel_file(root_folder_onedrive=root_folder_onedrive, name=excel_file_name)

        # Робота з Excel-файлами
        df1 = self.excel_handler.read_excel(file_content, sheet_name='Sheet1')
        print(df1)
        df2 = self.excel_handler.read_excel(file_content, sheet_name='Sheet2')
        print(df2)
        df2 = self.excel_handler.fill_missing_values(df2, 'write here', '400$')
        print(df2)

        self.excel_handler.save_excel(df1, df2, output_excel_filename=excel_file_name)

        upload_url = endpoint + "drive/items/root:/sklad.xlsx:/content"
        excel_file_path = 'sklad.xlsx'
        self.onedrive_manager.upload_excel_to_onedrive(access_token=access_token,
                                                       file_path=excel_file_path,
                                                       upload_url=upload_url)


        """
        Ця частина працює, а може не, хто знає
        """

        self.one_drive_photo_manager.get_photos("CP06C")

