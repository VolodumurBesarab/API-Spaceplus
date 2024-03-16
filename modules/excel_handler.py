import os

import pandas as pd
import requests
from pandas import DataFrame

from modules.reports.reports_generator import ReportsGenerator
from modules.auth_manager import AuthManager
from modules.onedrive_manager import OneDriveManager


class ExcelHandler:
    def __init__(self):
        self.onedrive_manager = OneDriveManager()
        self.auth_manager = AuthManager()
        self.reports_generator = ReportsGenerator()

        self.endpoint = self.auth_manager.get_endpoint()
        self.access_token = self.auth_manager.get_access_token_default_scopes()
        self.one_drive_url = self.endpoint + "drive/root/children"
        self.headers = self.auth_manager.get_default_header(access_token=self.access_token)

    def read_excel(self, file_content, sheet_name):
        df = pd.read_excel(file_content, sheet_name=sheet_name)
        return df

    def fill_missing_values(self, df, column_name, default_value):
        df[column_name] = df[column_name].fillna(default_value)
        return df

    # def save_excel(self, df1, df2, output_excel_filename):
    #     # Створення нового Excel файлу
    #     wb = Workbook()
    #
    #     # Вибір або створення першої сторінки
    #     sheet1 = wb.active
    #     sheet1.title = 'Sheet1'
    #
    #     # Додавання даних з DataFrame df на першу сторінку
    #     for row in dataframe_to_rows(df1, index=False, header=True):
    #         sheet1.append(row)
    #
    #     # Створення другої сторінки
    #     sheet2 = wb.create_sheet(title='Sheet2')
    #
    #     # Додавання даних з DataFrame df2 на другу сторінку
    #     for row in dataframe_to_rows(df2, index=False, header=True):
    #         sheet2.append(row)
    #
    #     # Збереження Excel файлу з назвою 'new table.xlsx'
    #     wb.save(output_excel_filename)
    #
    #     print("Excel файл успішно збережено!")

    def get_file_path(self, file_name) -> str:
        save_path = "/tmp/" + file_name
        return save_path

    def get_exel_file(self, name: str):
        file_content = None
        print(os.path.exists(self.get_file_path(name)))
        if not os.path.exists(self.get_file_path(name)):
            one_drive_url = self.endpoint + "drive/root:/Holland/" + name
            exel_file = self.onedrive_manager.get_root_folder_json(one_drive_url=one_drive_url,
                                                                   headers=self.headers)

            if exel_file:
                file_url = exel_file['@microsoft.graph.downloadUrl']

                response = requests.get(url=file_url)

                if response.status_code == 200:
                    file_content = response.content

                    print("excel file download successful")
                    self.reports_generator.create_general_report(message="excel file download successful")
                else:
                    print("excel file not download")
        return file_content

    def create_file_on_data(self, file_content, file_name):
        save_path = self.get_file_path(file_name=file_name)
        with open(save_path, 'wb') as file:
            file.write(file_content)

    def create_lines_list(self):
        pass

    def set_otomoto_id_by_storage_id(self, df:  DataFrame, otomoto_id, storage_id, excel_file_path):
        row = df[df['номер на складі'] == storage_id]

        if not row.empty:
            current_otomoto_id = row.iloc[0]['ID otomoto']

            if pd.isna(current_otomoto_id):
                df.loc[df['номер на складі'] == storage_id, 'ID otomoto'] = str(otomoto_id)
        # df.to_excel('New tested file.xlsx', index=False)
        df.to_excel(excel_file_path, index=False, sheet_name="otomoto")
        return df

    def update_excel_from_success_report(self, current_day=None):
        self.onedrive_manager.download_file_to_tmp(path=f"/Holland/Reports/{current_day}/successfully.txt",
                                                   file_name="successfully.txt")

        self.onedrive_manager.download_file_to_tmp(path="/Holland/Final_exel_file 21-11-2023.xlsx",
                                                   file_name="Data_otomoto.xlsx")

        if os.path.isfile("/tmp/successfully.txt"):
            print("Файл 'successfully.txt' успішно завантажено.")
        else:
            print("Помилка: Файл 'successfully.txt' не було знайдено або не вдалося завантажити.")

        if os.path.isfile("/tmp/Data_otomoto.xlsx"):
            print("Файл 'Data_otomoto.xlsx' успішно завантажено.")
        else:
            print("Помилка: Файл 'Data_otomoto.xlsx' не було знайдено або не вдалося завантажити.")

        df = pd.read_excel("/tmp/Data_otomoto.xlsx", sheet_name="OtoMoto")
        with open("/tmp/successfully.txt", "r") as success_file:
            lines = success_file.readlines()

        otomoto_ids = {}

        for line in lines:
            if "del" in line:
                continue
            elif not line.strip():
                break
            parts = line.split(", ")
            storage_id = parts[0].strip()

            parts = line.split("ID: ")
            otomoto_id = parts[1].strip()

            if storage_id not in otomoto_ids:
                otomoto_ids[storage_id] = otomoto_id

            if "_" not in storage_id:
                try:
                    storage_id = int(storage_id)
                except Exception as e:
                    pass

            matching_rows = df.loc[(df['номер на складі'] == storage_id) & (df['наявність на складі'] == 1)]
            if len(matching_rows) == 0:
                print(f"storage_id {storage_id}")
            elif len(matching_rows) == 1:
                df.loc[(df['номер на складі'] == storage_id) & (df['наявність на складі'] == 1), 'ID otomoto'] = float(otomoto_id)
            else:
                print(f"Count of same id is {len(matching_rows)} ")
                print(matching_rows)
        new_excel_file = f"/tmp/Final_exel_file {self.onedrive_manager.current_day}.xlsx"
        # new_excel_file = f"/tmp/Volodumurs_tested_file1.xlsx"
        try:
            df.to_excel(new_excel_file, index=False, sheet_name="OtoMoto", engine='xlsxwriter')
        except Exception as e:
            print(e)
        self.onedrive_manager.upload_file_to_onedrive(file_path=new_excel_file)

# excelhandler = ExcelHandler()
# excelhandler.update_excel_from_success_report(current_day="Second start program reports")
