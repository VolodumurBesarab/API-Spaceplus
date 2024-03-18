import json
import math
from datetime import datetime
import os
from datetime import date

import boto3
import pandas as pd
from pandas import DataFrame

from modules.reports.reports_generator import ReportsGenerator
from modules.images.s3_link_generator import S3LinkGenerator
from modules.otomoto.otomoto_api import OtomotoApi
from modules.auth_manager import AuthManager
from modules.excel_handler import ExcelHandler
from modules.onedrive_manager import OneDriveManager

ROWS_TO_SKIP = None
ROWS_TO_READ = None
DATETIME = datetime.now().strftime("%d-%m-%Y %H-%M-%S")
# REPORT_FILE_PATH = f"/tmp/reports/general_report {DATETIME}.txt"
# EXCEL_FILE_PATH = f"/tmp/New tested file {ROWS_TO_SKIP+1}-{ROWS_TO_READ+ROWS_TO_SKIP}.xlsx"
EXCEL_FILE_PATH = f"/tmp/Excel working data table.xlsx"
PARTS_CATEGORY_DICT = {
                       "Bagażniki dachowe > Bez relingów": "without-roof-rails",
                       "Bagażniki dachowe > Na relingi": "for-roof-rails",
                       "Boksy dachowe": "roof-boxes",
                       "Części i akcesoria": "car-equipment-and-accessories-other",
                       "Uchwyty na narty i snowboardy": "ski-handles",
                       "Uchwyty rowerowe, Uchwyty rowerowe > Na dach": "for-the-roof",
                       "Uchwyty rowerowe, Uchwyty rowerowe > Na hak": "for-tow-hook",
                       "Uchwyty rowerowe, Uchwyty rowerowe > Na klapę": "for-trunk-lid"
                       }


class OtomotoManager:
    def __init__(self, excel_file_name, sheet_name):
        self.df2 = None
        self.working_data_table = None
        self.df1 = None
        # self.first_126_values = None
        self.file_name = excel_file_name
        self.sheet_name = sheet_name
        self.excel_handler = ExcelHandler()
        self.otomoto_api = OtomotoApi()
        self.one_drive_manager = OneDriveManager()
        self.s3_link_generator = S3LinkGenerator()
        self.auth_manager = AuthManager()
        self.reports_generator = ReportsGenerator()

    def create_lists_of_produts(self, df1) -> tuple[list[DataFrame], list[DataFrame], list[DataFrame]]:
        in_stock = []
        out_of_stock = []
        invalid_quantity = []
        for index, row in df1.iterrows():
            if row['наявність на складі'] == 0 or row['наявність на складі'] == 2:
                out_of_stock.append(row)
            elif row['наявність на складі'] == 1:
                in_stock.append(row)
            else:
                invalid_quantity.append(row)
        return in_stock, out_of_stock, invalid_quantity

    def _convert_adverts_to_dict(self, list_ready_to_create: list[DataFrame]) -> list[dict]:
        advert_dict = {}
        list_of_adverts_dict = []
        for row in list_ready_to_create:
            for column_name, value in row.items():
                advert_dict.update({column_name: value})
            list_of_adverts_dict.append(advert_dict)
            advert_dict = {}
        return list_of_adverts_dict

    def set_char_by_number_in_stock(self, number_in_stock: str, char):
        file_path = "/tmp/ready_to_create.txt"
        if not os.path.isfile(file_path):
            self.one_drive_manager.download_file_to_tmp(
                path=f"/Holland/reports/{self.one_drive_manager.current_day}/Lists/ready_to_create.txt",
                file_name="ready_to_create.txt")

        with open(file_path, "r") as file:
            lines = file.readlines()

        with open(file_path, "w") as file:
            for line in lines:
                if number_in_stock in line:
                    line = line.rstrip('\n ') + char + '\n'
                file.write(line)

    def _create_report(self, list_created_adverts_id, list_of_errors, is_unexpected: bool):
        try:
            reports_folder = os.path.join(os.getcwd(), "reports")

            if not os.path.exists(reports_folder):
                os.makedirs(reports_folder)

            if not is_unexpected:
                full_path = os.path.join(reports_folder, f"basic_report{date.today()}.txt")
            else:
                full_path = os.path.join(reports_folder, f"unexpected report{date.today()}.txt")

            with open(full_path, 'w') as file:
                file.write("List of created ads:\n")
                for product_id, advert_id in list_created_adverts_id:
                    file.write(f"Stock number: {product_id}, ID created ads: {advert_id}\n")

                file.write("\nError List:\n")
                for product_id, error_message in list_of_errors:
                    file.write(f"Stock number: {product_id}, Error message: {error_message}\n")

            print(f"Репорт збережено у файлі {full_path}")
            with open(full_path, 'r') as file:
                report_contents = file.read()
                print(report_contents)
        except Exception as e:
            print(f"Сталася помилка при створенні звіту: {e}")

    def _post_adverts(self, list_ready_to_create: DataFrame):
        for index, row in list_ready_to_create.iterrows():

            # update list
            parts_type = str(row.get("type"))
            try:
                parts_category = PARTS_CATEGORY_DICT[parts_type.strip()]
            except Exception as e:
                print(e)
                self.reports_generator.create_general_report(f"{row.get('номер на складі')} Cant find {parts_type} in dictionary. {e}")
                break

            manufacturer = row.get("manufacturer")
            if manufacturer is None or math.isnan(manufacturer):
                manufacturer = "oryginalny"

            description = f"|{str(row.get('номер на складі'))}| " + str(row.get("description"))

            manufacturer_id = row.get("manufacturer_id")
            if isinstance(manufacturer_id, (int, float)):
                manufacturer_code = None
            elif manufacturer_id == 0 or manufacturer_id == "" or manufacturer_id is None:
                manufacturer_code = None
            else:
                manufacturer_code = row.get("manufacturer_id")

            advert_dict = {
                "product_id": row.get("номер на складі"),
                "title": row.get("title"),
                "description": description,
                "price": row.get("price"),
                "new_used": row.get("new_used"),
                "manufacturer": manufacturer,
                "parts-category": parts_category,
                "manufacturer_code": manufacturer_code
            }
            advert_json = json.dumps(advert_dict)

            client = boto3.client('lambda')
            response = client.invoke(
                FunctionName='prod-spaceplus-create-advert',
                InvocationType='Event',
                Payload=advert_json,
            )
            print(response["StatusCode"], row.get("номер на складі"))
            self.reports_generator.create_general_report(message=f"{response['StatusCode'], row.get('номер на складі')}")

    def create_list_need_to_create(self, in_stock: list[DataFrame]) -> tuple[list[DataFrame], list[DataFrame]]:
        list_check_need_to_edit = []
        list_ready_to_create = []
        with open('/tmp/adverts_dict_otomoto.json', 'r') as json_file:
            adverts_dict: dict = json.load(json_file)

        for item in in_stock:
            in_stock_id = str(item["номер на складі"])
            if in_stock_id in adverts_dict.keys():
                list_check_need_to_edit.append(item)
            else:
                list_ready_to_create.append(item)
        return list_check_need_to_edit, list_ready_to_create

    def create_list_need_to_delete(self, out_of_stock: list[DataFrame], whole_table: DataFrame) -> list[DataFrame]:
        list_need_to_delete = []
        with open('/tmp/adverts_dict_otomoto.json', 'r') as json_file:
            adverts_dict: dict = json.load(json_file)

        for item in out_of_stock:
            in_stock_id = str(item['номер на складі'])
            if in_stock_id in adverts_dict.keys():
                if any((whole_table['номер на складі'].astype(str) == in_stock_id) & (
                        whole_table['наявність на складі'] == 1)):
                    continue
                list_need_to_delete.append(item)
        return list_need_to_delete

    def read_selected_rows_from_excel(self, file_path, rows_to_skip: int, rows_to_read: int):
        if rows_to_skip > 0:
            working_data_table = pd.read_excel(file_path, skiprows=range(1, rows_to_skip), nrows=rows_to_read)
        else:
            working_data_table = pd.read_excel(file_path, nrows=rows_to_read)
        return working_data_table

    def find_current_line_in_json(self, json_file_path, current_line: str):
        try:
            with open(json_file_path, 'r') as json_file:
                data = json.load(json_file)

            for key, value in data.items():
                if str(current_line) == str(key):
                    return value

        except Exception as e:
            print(f'Cant find in json: {e}')

    def delete_adverts(self) -> bool:
        is_deleted = False
        # if not os.path.exists("/tmp/list_need_to_delete.txt"):
        #     self.one_drive_manager.download_file_to_tmp(
        #         path=f"/Holland/reports/{self.one_drive_manager.current_day}/Lists/list_need_to_delete.txt",
        #         file_name="list_need_to_delete.txt")

        # if not os.path.exists("/tmp/adverts_dict.json"):
        #     self.one_drive_manager.download_file_to_tmp(
        #         path=f"/Holland/reports/{self.one_drive_manager.current_day}/adverts_dict.json",
        #         file_name="adverts_dict.jsons")

        deleted_report_path = "/tmp/deleted_report.txt"
        if not os.path.exists(deleted_report_path):
            with open(deleted_report_path, 'w') as file:
                file.writelines("Deleted report")

        with open("/tmp/list_need_to_delete.txt", "r") as otomoto_id_del:
            lines = otomoto_id_del.readlines()

        updated_lines = []

        for line in lines:
            current_line = line.strip()
            otomoto_id = self.find_current_line_in_json(json_file_path="/tmp/adverts_dict_otomoto.json",
                                                        current_line=current_line)
            response = self.otomoto_api.delete_advert(in_stock_id=current_line, otomoto_id=otomoto_id)
            print(f"{response.status_code} : {current_line}")
            self.reports_generator.create_general_report(message=f"Deleted status code: {response.status_code}, {current_line}")

            with open(deleted_report_path, 'r') as file:
                deleted_report_path_lines = file.readlines()

            if response.status_code == 204:
                is_deleted = True
                deleted_report_path_lines.append(f"{current_line}, {otomoto_id}, successfully deleted")
                updated_lines.append(f"{current_line} +\n")
            else:
                deleted_report_path_lines.append(f"{current_line}, {otomoto_id}, not deleted")
                updated_lines.append(f"{current_line} -\n")

        self.one_drive_manager.upload_file_to_onedrive(file_path=deleted_report_path)

        return is_deleted

    def create_lists(self):
        if not self.one_drive_manager.is_current_day_folder_created():
            self.one_drive_manager.create_current_day_folder()

        if not self.one_drive_manager.is_list_folder_created():
            self.one_drive_manager.create_lists_folder()

            self.otomoto_api.get_database()

            file_content = self.excel_handler.get_exel_file(self.file_name)
            # create file
            self.excel_handler.create_file_on_data(file_content=file_content, file_name=self.file_name)
            self.excel_handler.create_file_on_data(file_content=file_content, file_name="Excel working data table.xlsx")

            main_excel_file_path = self.excel_handler.get_file_path(file_name=self.file_name)
            self.df1 = pd.read_excel(main_excel_file_path)  # file to read

            in_stock, out_of_stock, invalid_quantity = self.create_lists_of_produts(self.df1)
            list_need_to_delete = self.create_list_need_to_delete(out_of_stock=out_of_stock, whole_table=self.df1)
            list_check_need_to_edit, list_ready_to_create = self.create_list_need_to_create(in_stock)

            ready_to_create_path = "/tmp/ready_to_create_otomoto.txt"
            invalid_quantity_path = "/tmp/invalid_quantity_otomoto.txt"
            list_need_to_delete_path = "/tmp/list_need_to_delete_otomoto.txt"
            column_name = "номер на складі"

            self.one_drive_manager.upload_list_to_onedrive(uploaded_list=list_ready_to_create,
                                                           uploaded_list_path=ready_to_create_path,
                                                           column_name=column_name)
            self.one_drive_manager.upload_list_to_onedrive(uploaded_list=invalid_quantity,
                                                           uploaded_list_path=invalid_quantity_path,
                                                           column_name=column_name)
            self.one_drive_manager.upload_list_to_onedrive(uploaded_list=list_need_to_delete,
                                                           uploaded_list_path=list_need_to_delete_path,
                                                           column_name=column_name)
        else:
            self.one_drive_manager.download_file_to_tmp(
                path=f"/Holland/reports/{self.one_drive_manager.current_day}/Lists/ready_to_create.txt",
                file_name="ready_to_create.txt")
            self.one_drive_manager.download_file_to_tmp(
                path=f"/Holland/reports/{self.one_drive_manager.get_current_day()}/Lists/list_need_to_delete.txt",
                file_name="list_need_to_delete.txt")
            self.one_drive_manager.download_file_to_tmp(
                path=f"/Holland/reports/{self.one_drive_manager.current_day}//tmp/adverts_dict_otomoto.json",
                file_name="/tmp/adverts_dict_otomoto.json")

    def create_df_from_ready_to_create(self, df: DataFrame, adverts_create_in_one_time=20) -> DataFrame:
        with open('/tmp/ready_to_create.txt', 'r') as file:
            lines = file.readlines()

        in_stock_numbers = []
        for line in lines:
            in_stock_numbers.append(line.strip())

        df1 = df[
            (df['номер на складі'].astype(str).isin(in_stock_numbers)) & (df['наявність на складі'] == 1)].reset_index(
            drop=True)
        return df1

    def create_all_adverts(self):
        if not self.one_drive_manager.is_list_folder_created():
            file_content = self.excel_handler.get_exel_file(self.file_name)
            # create file
            self.excel_handler.create_file_on_data(file_content=file_content, file_name=self.file_name)
            self.excel_handler.create_file_on_data(file_content=file_content, file_name="Excel working data table.xlsx")

            main_excel_file_path = self.excel_handler.get_file_path(file_name=self.file_name)

            df1 = pd.read_excel(main_excel_file_path)  # file to read

            self.create_lists()

            all_adverts_from_ready_to_create = self.create_df_from_ready_to_create(df1)

            print(f"adverts to create:", len(all_adverts_from_ready_to_create))
            self.reports_generator.create_general_report(message=f"adverts to create: {len(all_adverts_from_ready_to_create)}")

            self._post_adverts(list_ready_to_create=all_adverts_from_ready_to_create)

            self.delete_adverts()
        else:
            self.create_reports_from_base()
        print("Working is done")
        return self

    def convert_text_to_dict(self, successfully_file_path: str) -> dict:
        with open(successfully_file_path, "r") as success_file:
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
                otomoto_ids[str(storage_id)] = str(otomoto_id)
            else:
                print(F"Cant add {storage_id} : {otomoto_id} to dict")
        return otomoto_ids

    def merge_and_save_one_drive_dict(self, successfully_file_path, json_file_path):
        successfully_file_dict = self.convert_text_to_dict(successfully_file_path=successfully_file_path)
        with open(json_file_path, "r") as json_file:
            data = json.load(json_file)
        merged_dict = {**successfully_file_dict, **data}
        with open(json_file_path, "w") as output_file:
            json.dump(merged_dict, output_file)

    def create_reports_from_base(self):
        self.one_drive_manager.download_basic_reports_to_tmp()

        folder_path = "/tmp/text_reports"

        successfully_lines = []
        error_lines = []

        for filename in os.listdir(folder_path):
            if filename.endswith(".txt"):
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    for line in lines:
                        if "successfully" in line:
                            successfully_lines.append(line)
                        elif "Error:" in line:
                            error_lines.append(line)
                        elif "Unexpected" in line:
                            error_lines.append(line)

        successfully_file_path = "/tmp/successfully.txt"
        with open(successfully_file_path, 'w') as success_file:
            success_file.writelines(successfully_lines)
        self.one_drive_manager.upload_file_to_onedrive(file_path=successfully_file_path)

        errors_file_path = "/tmp/errors.txt"
        with open(errors_file_path, 'w') as error_file:
            error_file.writelines(error_lines)
        self.one_drive_manager.upload_file_to_onedrive(file_path=errors_file_path)

        # json_file_path = "/tmp/adverts_dict.json"
        # self.merge_and_save_one_drive_dict(successfully_file_path=successfully_file_path, json_file_path=json_file_path)
        # self.one_drive_manager.upload_file_to_onedrive(file_path=json_file_path, onedrive_path="/Holland/API-Spaceplus")
