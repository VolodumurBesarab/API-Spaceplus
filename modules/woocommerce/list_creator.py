import json
import os.path
from typing import Tuple, List

import pandas as pd
from pandas import DataFrame, Series

from modules.excel_handler import ExcelHandler
from modules.onedrive_manager import OneDriveManager
from modules.otomoto.otomoto_manager import OtomotoManager
from modules.reports.reports_generator import ReportsGenerator

# EXCEL_FILE_NAME = r"otomoto.xlsx"
EXCEL_FILE_NAME = r"spaceplus_testing.xlsx"
SHEET_NAME = "Spaceplus"
ADVERTS_DICT_JSON = "adverts_dict_woocommerce.json"
ADVERTS_DICT_JSON_PATH = "/tmp/adverts_dict_woocommerce.json"


class ListCreator:
    def __init__(self):
        # otomoto_manager = OtomotoManager(excel_file_name="otomoto.xlsx", sheet_name=None)
        self.one_drive_manager = OneDriveManager()
        self.excel_handler = ExcelHandler()
        self.reports_generator = ReportsGenerator()

    def create_lists_of_produts(self, df1: DataFrame) -> tuple[list[DataFrame], list[DataFrame], list[DataFrame]]:
        in_stock = []
        out_of_stock = []
        invalid_quantity = []
        for index, row in df1.iterrows():
            if row['stock availability'] == 0 or row['stock availability'] == 2:
                out_of_stock.append(row)
            elif row['stock availability'] == 1:
                in_stock.append(row)
            else:
                invalid_quantity.append(row)
        return in_stock, out_of_stock, invalid_quantity

    def create_list_need_to_delete(self, out_of_stock: list[DataFrame], whole_table: DataFrame) -> list[DataFrame]:
        list_need_to_delete = []

        # if not os.path.exists(ADVERTS_DICT_JSON_PATH):
        print(f"/Holland/reports/{self.one_drive_manager.get_current_day()}/{ADVERTS_DICT_JSON}")
        self.one_drive_manager.download_file_to_tmp(
            path=f"/Holland/reports/{self.one_drive_manager.get_current_day()}/{ADVERTS_DICT_JSON}",
            file_name=ADVERTS_DICT_JSON)

        with open(ADVERTS_DICT_JSON_PATH, 'r') as json_file:
            adverts_dict: dict = json.load(json_file)

        for item in out_of_stock:
            in_stock_id = str(item['stock number'])
            if in_stock_id in adverts_dict.keys():
                if any((whole_table['stock number'].astype(str) == in_stock_id) & (
                        whole_table['stock availability'] == 1)):
                    continue
                list_need_to_delete.append(item)
        return list_need_to_delete

    def create_list_need_to_create(self, in_stock: list[DataFrame]) -> tuple[list[DataFrame], list[DataFrame]]:
        list_check_need_to_edit = []
        list_ready_to_create = []
        with open(ADVERTS_DICT_JSON_PATH, 'r') as json_file:
            adverts_dict: dict = json.load(json_file)

        for item in in_stock:
            in_stock_id = str(item["stock number"])
            if in_stock_id in adverts_dict.keys():
                list_check_need_to_edit.append(item)
            else:
                list_ready_to_create.append(item)
        return list_check_need_to_edit, list_ready_to_create

    def get_excel(self) -> DataFrame:
        df1 = None
        if not self.one_drive_manager.is_current_day_folder_created():
            self.one_drive_manager.create_current_day_folder()

        if not self.one_drive_manager.is_list_folder_created():
            self.one_drive_manager.create_lists_folder()

        file_content = self.excel_handler.get_exel_file(EXCEL_FILE_NAME)

        self.excel_handler.create_file_on_data(file_content=file_content, file_name=EXCEL_FILE_NAME)

        main_excel_file_path = self.excel_handler.get_file_path(file_name=EXCEL_FILE_NAME)
        df1 = pd.read_excel(io=main_excel_file_path, sheet_name=SHEET_NAME)
        return df1

    def create_lists(self, df: DataFrame):
        in_stock, out_of_stock, invalid_quantity = self.create_lists_of_produts(df1=df1)
        list_need_to_delete = self.create_list_need_to_delete(out_of_stock=out_of_stock, whole_table=df1)
        list_check_need_to_edit, list_ready_to_create = self.create_list_need_to_create(in_stock=in_stock)

        ready_to_create_path = "/tmp/ready_to_create_otomoto.txt"
        invalid_quantity_path = "/tmp/invalid_quantity_otomoto.txt"
        list_need_to_delete_path = "/tmp/list_need_to_delete_otomoto.txt"

        self.one_drive_manager.upload_file_to_onedrive(path_after_current_day="Lists", file_path=ready_to_create_path)
        self.reports_generator.create_general_report(message=f"{ready_to_create_path} created successfully")

        self.one_drive_manager.upload_file_to_onedrive(path_after_current_day="Lists", file_path=invalid_quantity_path)
        self.reports_generator.create_general_report(message=f"{invalid_quantity_path} created successfully")

        self.one_drive_manager.upload_file_to_onedrive(path_after_current_day="Lists", file_path=list_need_to_delete_path)
        self.reports_generator.create_general_report(message=f"{list_need_to_delete_path} created successfully")

# list_creator = ListCreator()
# list_creator.create_lists()
