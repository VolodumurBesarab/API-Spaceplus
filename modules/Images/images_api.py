from imgurpython import ImgurClient

CLIENT_ID = 'f82bcb68847441a'
CLIENT_SECRET = 'd3870caebcf64e7cc4ab0d180204d25b292dc3b6'

class ImagesApi:
    # Ваші дані з облікового запису Imgur
    client_id = 'f82bcb68847441a'
    client_secret = 'd3870caebcf64e7cc4ab0d180204d25b292dc3b6'
    # завантаження фото з onedrive

    # Шлях до фото на вашому локальному комп'ютері
    image_path = 'C:\\Users\\vladi\\OneDrive\\Desktop\\1.jpg'

    # Функція для завантаження фото на Imgur і отримання URL
    def upload_image_to_imgur(image_path):
        client = ImgurClient(CLIENT_ID, CLIENT_SECRET)

        # Завантаження фото
        uploaded_image = client.upload_from_path(image_path, anon=True)

        # Отримання URL завантаженого фото
        image_url = uploaded_image['link']

        return image_url

    # Завантаження фото і отримання URL
    imgur_image_url = upload_image_to_imgur(image_path)

    # Виведення URL
    print("URL фото на Imgur:", imgur_image_url)