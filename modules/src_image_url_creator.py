import pandas as pd

from modules.excel_handler import ExcelHandler
from modules.images.s3_link_generator import S3LinkGenerator
from modules.one_drive_photo_manager import OneDrivePhotoManager
from modules.reports.reports_generator import ReportsGenerator


class SrcImageUrlCreator:
    def __init__(self):
        self.one_drive_photo_manager = OneDrivePhotoManager()
        self.file_name = "Otomoto.xlsx"
        self.excel_handler = ExcelHandler()
        self.s3_link_generator = S3LinkGenerator()
        self.reports_generator = ReportsGenerator()

    def create_list(self, df1) -> list:
        in_stock = []
        for index, row in df1.iterrows():
            if row['наявність на складі'] == 1 or row['наявність на складі'] == "1":
                # convert to str
                in_stock.append(str(row['номер на складі']))
        return in_stock

    def get_string_need_format(self, lists_of_ids:list[str]) -> str:
        result = ""
        for advert_id in lists_of_ids:
            result = result + f"{advert_id}|"
        result = result[:-1]
        return result

    def generate_links(self):
        file_content = self.excel_handler.get_exel_file(self.file_name)
        # create file
        self.excel_handler.create_file_on_data(file_content=file_content, file_name=self.file_name)
        # self.excel_handler.create_file_on_data(file_content=file_content, file_name="Excel working data table.xlsx")

        main_excel_file_path = self.excel_handler.get_file_path(file_name=self.file_name)

        df1 = pd.read_excel(io=main_excel_file_path, sheet_name="olx ua")  # file to read

        # this function return list of folders
        lists_of_ids = self.create_list(df1=df1)

        print(lists_of_ids)

        test_id_1 = "30501"
        test_id_2 = "30506"
        test_lists_of_ids = [test_id_1, test_id_2]

        for product_id in test_lists_of_ids:

            parent_folder_id = self.one_drive_photo_manager.get_stock_photos_folder_id()
            folder_id = self.one_drive_photo_manager.find_folder_by_name(parent_folder_id=parent_folder_id,
                                                                         folder_name=str(product_id))

            path_to_save_photos = self.one_drive_photo_manager.download_files_from_folder(folder_id=folder_id,
                                                                                          folder_name=str(product_id))

            print(path_to_save_photos)
            photos_url_list = self.s3_link_generator.generate_public_urls(path_to_save_photos=path_to_save_photos)

            if photos_url_list is None or photos_url_list == []:
                # return f"Error: can't find folder {product_id}, or folder is empty"
                self.reports_generator.create_general_report(message="Error: can't find folder {product_id}, or folder is empty")

            formatted_photos_url_list = self.get_string_need_format(photos_url_list)

            self.reports_generator.create_general_report(message=f"Advert id {product_id}: {formatted_photos_url_list}")
            print(f"Advert id {product_id}: {formatted_photos_url_list}")

# src_image_url_creator = SrcImageUrlCreator()
# src_image_url_creator.generate_links()
