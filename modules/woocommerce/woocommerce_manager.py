import json
import math
import os
import re

import boto3
import requests
from pandas import DataFrame
from requests import Response

from dotenv import load_dotenv

from modules.images.s3_link_generator import S3LinkGenerator
from modules.one_drive_photo_manager import OneDrivePhotoManager
from modules.onedrive_manager import OneDriveManager
from modules.reports.reports_generator import ReportsGenerator
from modules.woocommerce.list_creator import ListCreator

load_dotenv()

PARTS_CATEGORY_DICT_WOOCOMMERCE = {
                       "Bagażniki dachowe > Bez relingów": "without-roof-rails",
                       "Bagażniki dachowe > Na relingi": "for-roof-rails",
                       "Boksy dachowe": "roof-boxes",
                       "Części i akcesoria": "car-equipment-and-accessories-other",
                       "Uchwyty na narty i snowboardy": "ski-handles",
                       "Uchwyty rowerowe, Uchwyty rowerowe > Na dach": "for-the-roof",
                       "Uchwyty rowerowe, Uchwyty rowerowe > Na hak": "for-tow-hook",
                       "Uchwyty rowerowe, Uchwyty rowerowe > Na klapę": "for-trunk-lid"
                       }

SHIPPING_DICT_WOOCOMMERCE = {
                       }

class WoocommerceManager:
    def __init__(self):
        self.one_drive_photo_manager = OneDrivePhotoManager()
        self.reports_generator = ReportsGenerator()
        self.one_drive_manager = OneDriveManager()
        self.list_creator = ListCreator()
        try:
            self.CONSUMER_KEY_WC = os.getenv("CONSUMER_KEY_WC")
            self.CONSUMER_SECRET_WC = os.getenv("CONSUMER_SECRET_WC")
            self.WC_URL = os.getenv("WC_URL")
        except:
            self.CONSUMER_KEY_WC = os.getenv("CONSUMER_KEY_WC")
            self.CONSUMER_SECRET_WC = os.getenv("CONSUMER_SECRET_WC")
            self.WC_URL = os.getenv("WC_URL")
            print("add env to lambda")

    def get_database(self):
        woocommerce_endpoint = 'products'
        url = f'{self.WC_URL}{woocommerce_endpoint}'
        auth = (self.CONSUMER_KEY_WC, self.CONSUMER_SECRET_WC)
        woocommerce_data_base = None

        response = requests.get(url=url, auth=auth)
        if response.status_code == 200:
            woocommerce_data_base = self.create_database_in_onedrive(response=response)
        else:
            print('Підключення не вдалось. Перевірте ключі та URL.')

        return woocommerce_data_base

    def create_database_in_onedrive(self, response: Response):
        adverts_data = response.json()
        adverts = {}
        for advert in adverts_data:
            pattern = re.compile(r'\|(.+?)\|')

            description = advert["description"]
            match = pattern.search(description)

            if match:
                # print(advert["id"], match.group(1))
                adverts[match.group(1)] = advert["id"]
            else:
                message = f"{advert['id']} have not id 'номер на складі'"
                print(message)
                # self.reports_generator.create_general_report(message=message)
        return adverts

    def save_database_woocommerce_on_onedrive(self, woocommerce_data_base):
        adverts_dict_json_path = "/tmp/adverts_dict_woocommerce.json"
        with open(adverts_dict_json_path, "w", encoding="utf-8") as file:
            json.dump(woocommerce_data_base, file, ensure_ascii=False, indent=4)

        self.one_drive_manager.upload_file_to_onedrive(file_path=adverts_dict_json_path)

    def create_df_from_ready_to_create(self, df: DataFrame):
        with open('/tmp/ready_to_create_otomoto.txt', 'r') as file:
            lines = file.readlines()

        in_stock_numbers = []
        for line in lines:
            in_stock_numbers.append(line.strip())

        df1 = df[
            (df['stock number'].astype(str).isin(in_stock_numbers)) & (df['stock availability'] == 1)].reset_index(
            drop=True)
        return df1

    def post_adverts(self, list_ready_to_create: DataFrame):
        # limit = 50
        # for index, row in enumerate(list_ready_to_create.iterrows()):
        #     if index >= limit:
        #         break
        for index, row in list_ready_to_create.iterrows():
            product_id = str(row.get("stock number"))
            # update list
            try:
                parts_category = PARTS_CATEGORY_DICT_WOOCOMMERCE[str(row.get("type")).strip()]
            except Exception as e:
                self.reports_generator.create_general_report(f"{row.get('stock number')} Cant find {str(row.get('type')).strip()} in dictionary. {e}")
                break

            manufacturer = row.get("manufacturer")
            if manufacturer is None or math.isnan(manufacturer):
                manufacturer = "oryginalny"

            description = f"|{product_id}| " + str(row.get("description"))

            # manufacturer_id = row.get("manufacturer_id")
            # if isinstance(manufacturer_id, (int, float)):
            #     manufacturer_code = None
            # elif manufacturer_id == 0 or manufacturer_id == "" or manufacturer_id is None:
            #     manufacturer_code = None
            # else:
            #     manufacturer_code = row.get("manufacturer_id")

            # s3_link_generator = S3LinkGenerator()
            # s3_link_generator.generate_public_urls()

            parent_folder_id = self.one_drive_photo_manager.get_stock_photos_folder_id()
            folder_id = self.one_drive_photo_manager.find_folder_by_name(parent_folder_id=parent_folder_id,
                                                                         folder_name=str(product_id))

            path_to_save_photos = self.one_drive_photo_manager.download_files_from_folder(folder_id=folder_id,
                                                                                          folder_name=str(product_id))

            s3_link_generator = S3LinkGenerator()
            photos_url_list = s3_link_generator.generate_public_urls(path_to_save_photos=path_to_save_photos)
            if not photos_url_list:
                self.reports_generator.create_general_report(message=f"advert {product_id} folder with photos not found or it is empty")
                break

            images = s3_link_generator.convert_urls_to_woocommerce_format(urls=photos_url_list)

            try:
                shipping = SHIPPING_DICT_WOOCOMMERCE[str(row.get("delivery")).strip()]
            except Exception as e:
                self.reports_generator.create_general_report(f"{row.get('stock number')} Cant find {str(row.get('delivery')).strip()} in dictionary. {e}")
                break

            advert_dict = {
                "product_id": product_id,
                "title": row.get("title"),
                "description": description,
                "price": row.get("price"),
                "new_used": row.get("new_used"),
                "manufacturer": manufacturer,
                "parts-category": parts_category,
                "images": images,
                "shipping": shipping

                # "product_id": 51111_1,
                # "title" : "New product 4",
                # "description": "Smell like long big mouse",
                # "price" : "52.99",
                # "new_used": "Nowy",
                # "manufacturer": "Oryginalny",
                # "parts_category": [{"id": 51}, {"id": 61}],
                # "images" : None,
                # "shipping" : ("small", 55),
                }
            advert_json = json.dumps(advert_dict)

            client = boto3.client('lambda')
            response = client.invoke(
                FunctionName='create-advert-woocommerce',
                InvocationType='Event',
                Payload=advert_json,
            )
            print(response["StatusCode"], row.get("номер на складі"))
            self.reports_generator.create_general_report(message=f"{response['StatusCode'], row.get('номер на складі')}")
        pass

    def create_all_adverts(self):
        df1 = self.list_creator.get_excel()
        self.list_creator.create_lists(df=df1)
        all_adverts_from_ready_to_create: DataFrame = self.create_df_from_ready_to_create(df=df1)
        self.reports_generator.create_general_report(
            message=f"adverts to create: {len(all_adverts_from_ready_to_create)}")

        self.post_adverts(list_ready_to_create=all_adverts_from_ready_to_create)
        pass



# woocommerce_manager = WoocommerceManager()
# data_base = woocommerce_manager.get_database()
# woocommerce_manager.save_database_woocommerce_on_onedrive(woocommerce_data_base=data_base)
