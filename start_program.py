import requests

from modules.auth_manager import AuthManager
from modules.excel_handler import ExcelHandler
from modules.onedrive_manager import OneDriveManager

CONSUMER_KEY_WC = 'ck_0b8082bdc3a97be4a1e846593cc7a680b158109c'
CONSUMER_SECRET_WC = 'cs_ab5acc886e4ef248439b1fe708756674b821f02b'
WC_URL = 'https://spaceplus.com.pl/wp-json/wc/v3/'

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

        "Step 1: Find Site Id by Site Name"
        site_id1 = "spacelpus.sharepoint.com,c2babb4d-6ad3-4b18-a4c8-7366095d82f4,8c6031b4-1201-423f-bb24-f913fb141d81"
        site_id2 = "spacelpus-my.sharepoint.com,11befae9-0831-409a-83f8-5b32a2f05c83,ab7ba235-20df-4df4-88fd-d8d7cf277d53"

        "Step 2: Find Drive Id by Document Library name"
        drive_id1 = 'b!Tbu6wtNqGEukyHNmCV2C9LQxYIwBEj9CuyT5E_sUHYHL2RIQsYQDSK4f_qlK2qlS'
        drive_id2 = 'b!6fq-ETEImkCD-FsyovBcgzWie6vfIPRNiP3Y188nfVNklHx9RhlARoA2_keutH84'
        "Write your requests here"
        # test_url = f"https://graph.microsoft.com/v1.0/sites/{site_id1}/drives"
        # response = requests.get(test_url, headers=headers)
        # print(response.json())

        test_url2 = f"https://graph.microsoft.com/v1.0/sites/{site_id2}/drives"
        response = requests.get(test_url2, headers=headers)
        print(response.json())

        # root_folder_onedrive = self.onedrive_manager.get_root_folder_json(one_drive_url=one_drive_url, headers=headers)
        #
        # file_content = self.excel_handler.get_exel_file(root_folder_onedrive=root_folder_onedrive, name=excel_file_name)
        #
        # # Робота з Excel-файлами
        # df1 = self.excel_handler.read_excel(file_content, sheet_name='Sheet1')
        # print(df1)
        # df2 = self.excel_handler.read_excel(file_content, sheet_name='Sheet2')
        # print(df2)
        # df2 = self.excel_handler.fill_missing_values(df2, 'write here', '400$')
        # print(df2)
        #
        # self.excel_handler.save_excel(df1, df2, output_excel_filename=excel_file_name)
        #
        # upload_url = endpoint + "drive/items/root:/sklad.xlsx:/content"
        # excel_file_path = 'sklad.xlsx'
        # self.onedrive_manager.upload_excel_to_onedrive(access_token=access_token,
        #                                                file_path=excel_file_path,
        #                                                upload_url=upload_url)
        #

        """
        Ця частина працює, а може не, хто знає
        """

        response = requests.get(url=endpoint + "drive/items/01GK3VGRXOWQGPB72LHVB2WIIN642U4NKK/children",
                                headers=headers)
        photo_id_list = []
        if response.status_code == 200:
            nl_folder_contents = response.json()
            searched_folder_id = None

            # Знайти папку 'CP06C' у списку вмісту папки 'root/NL'
            for item in nl_folder_contents['value']:
                if item['name'] == 'CP06C' and item['folder']:
                    searched_folder_id = item['id']
                    break

            if searched_folder_id:
                # Отримати вміст папки 'CP06C'
                response_cp06c = requests.get(
                    f"https://graph.microsoft.com/v1.0/users/andrzej.besarab@spacelpus.onmicrosoft.com/drive/items/{searched_folder_id}/children",
                    headers=headers
                )
                # https://graph.microsoft.com/v1.0/sites/{site-id}/drives/{drive-id}/items/{item-id}/invite
                if response_cp06c.status_code == 200:
                    cp06c_folder_contents = response_cp06c.json()
                    for item in cp06c_folder_contents['value']:
                        if item['file']:
                            photo_id_list.append(item['id'])
                else:
                    print(f"Сталася помилка при отриманні вмісту папки CP06C: {response_cp06c.text}")
            else:
                print("Папка CP06C не знайдена у папці root/NL")
        else:
            print(f"Сталася помилка при отриманні вмісту папки root/NL: {response.text}")
        print(photo_id_list)

        item_id_zal = "01GK3VGRQXMBTZ5QJPXRA3EVRMXIKZCKZG"

        create_link_payload = {
            "type": "view",
            "scope": "anonymous",
            "retainInheritedPermissions": False
        }
        post_headers = {
            'Authorization': access_token,
            'Content-Type': 'application/json'
        }

        for item_id in photo_id_list:
            create_link_url = endpoint + f"drive/items/{item_id}/createLink"

            create_link_response = requests.post(url=create_link_url, headers=post_headers, json=create_link_payload)

            if create_link_response.status_code == 200:
                create_link_response_json = create_link_response.json()
                created_link = create_link_response_json["link"]["webUrl"]
                print(created_link)


        # woocommerce спроба підключення

        # from urllib.parse import urlencode
        #
        # params = {
        #     "key_id": 1,
        #     "user_id": 123,
        #     "consumer_key": "ck_0b8082bdc3a97be4a1e846593cc7a680b158109c",
        #     "consumer_secret": "cs_ab5acc886e4ef248439b1fe708756674b821f02b",
        #     "key_permissions": "read_write"
        # }
        #
        # store_url = 'https://spaceplus.com.pl'
        # endpoint = '/wc-auth/v1/authorize'
        # params = {
        #     "app_name": "Api-Spaceplus",
        #     "scope": "read_write",
        #     "user_id": 123,
        #     "return_url": "https://allegro.pl",
        #     "callback_url": "https://allegro.pl/"
        # }
        # query_string = urlencode(params)
        #
        # print("%s%s?%s" % (store_url, endpoint, query_string))

    # Приклад запиту для перевірки підключення


    def check_connection(self):
        Woocommerceendpoint = 'products'
        response = requests.get(
            f'{WC_URL}{Woocommerceendpoint}',
            auth=(CONSUMER_KEY_WC, CONSUMER_SECRET_WC)
        )
        if response.status_code == 200:
            print('Підключення до WooCommerce API успішне!')
        else:
            print('Підключення не вдалось. Перевірте ключі та URL.')

    def import_product(self, product_data):
        Woocommerceendpoint = 'products'
        response = requests.post(
            f'{WC_URL}{Woocommerceendpoint}',
            auth=(CONSUMER_KEY_WC, CONSUMER_SECRET_WC),
            json=product_data
        )
        return response.json()

    # # Приклад виклику функції для імпорту товару
    # if __name__ == '__main__':
    #     new_product_data = {
    #         "name": "Новий товар",
    #         "type": "simple",
    #         "regular_price": "10.00",
    #         "description": "Це новий товар",
    #         "short_description": "Новий товар для тестування",
    #         "categories": [{"id": 1}],
    #         "images": [{"src": "https://static4.winylownia.pl/pol_pl_PLACEBO-Placebo-LP-60305_1.jpg"}]
    #     }
    #
    #     response = import_product(new_product_data)
    #     print('Відповідь API:', response)