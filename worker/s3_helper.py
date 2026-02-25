import requests
import tempfile
import os


def download_file_from_url(url):
    try:
        response = requests.get(url, stream=True)

        if response.status_code != 200:
            raise Exception(f"Failed to download file: {response.status_code}")

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pptx")
        temp_file_path = temp_file.name

        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return temp_file_path

    except Exception as e:
        raise Exception(f"Download error: {e}")