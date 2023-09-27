from imgurpython import ImgurClient

from modules.auth_manager import AuthManager

class ImagesApi:
    def __init__(self):
        self.auth_manager = AuthManager()
    def start(self):
        imgur_client_id = self.auth_manager.get_imgur_client_id()
        imgur_client_secret = self.auth_manager.get_imgur_client_secret()

        # Шлях до фото на вашому локальному комп'ютері
        image_path = 'C:\\Users\\vladi\\OneDrive\\Desktop\\1.jpg'

        # Функція для завантаження фото на Imgur і отримання URL
        def upload_image_to_imgur(image_path):
            client = ImgurClient(imgur_client_id, imgur_client_secret)

            # Завантаження фото
            uploaded_image = client.upload_from_path(image_path, anon=True)

            # Отримання URL завантаженого фото
            image_url = uploaded_image['link']

            return image_url

        # Завантаження фото і отримання URL
        imgur_image_url = upload_image_to_imgur(image_path)

        # Виведення URL
        print("URL фото на Imgur:", imgur_image_url)