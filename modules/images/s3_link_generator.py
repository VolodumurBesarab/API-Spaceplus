import os

import boto3


S3_BUCKET_NAME = "prod-spaceplus-automation"
S3 = boto3.client("s3")

class S3LinkGenerator:
    def _get_files_in_folder(self, folder_path):
        file_list = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_list.append(os.path.join(root, file))
        # file_names = [os.path.basename(file_path) for file_path in file_list]
        sorted_file_list = sorted(file_list, key=lambda x: os.path.basename(x))
        return sorted_file_list #, file_names

    def upload_file_to_s3(self, file_path, rows_to_skip, rows_to_read):
        # file_name = f"{os.path.basename(file_path)} {rows_to_skip}-{rows_to_skip + rows_to_read}"
        # S3.upload_file(file_path, S3_BUCKET_NAME, file_name)
        if rows_to_skip is None and rows_to_read is None:
            file_name = os.path.basename(file_path)
        else:
            base_name, extension = os.path.splitext(file_path)
            new_file_path = f"{base_name} {rows_to_skip + 1}-{rows_to_skip + rows_to_read}{extension}"
            file_name = os.path.basename(new_file_path)
        S3.upload_file(file_path, S3_BUCKET_NAME, file_name)
        pass

    def _get_list_and_upload_photos(self, path_to_save_photos: str):
        # s3_object_key = None
        file_list = self._get_files_in_folder(path_to_save_photos)
        s3 = boto3.client("s3")

        for file_path in file_list:
            file_name = os.path.basename(file_path)
            s3.upload_file(file_path, S3_BUCKET_NAME, file_name)
            try:
                s3.head_object(Bucket=S3_BUCKET_NAME, Key=file_name)
            except Exception as e:
                print(f"Помилка: {e}. Файл {file_name} не був знайдений на S3.")

        return file_list

    def _del_photos(self):
        pass

    def convert_urls_to_woocommerce_format(self, urls: list[str]) -> list[dict[str, str]]:
        return [{"src": url} for url in urls]

    def generate_public_urls(self, path_to_save_photos: str) -> list[str]:
        file_list = self._get_list_and_upload_photos(path_to_save_photos=path_to_save_photos)

        public_urls = []

        for file_path in file_list:
            s3_object_key = os.path.basename(file_path)
            url_with_params = S3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": S3_BUCKET_NAME,
                        "Key": s3_object_key},
                ExpiresIn=3600
            )
            url, params = url_with_params.split('?', 1)
            public_urls.append(url)
            # need create logs
        return public_urls
