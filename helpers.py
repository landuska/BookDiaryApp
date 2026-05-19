import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")
API_KEY = os.getenv('API_KEY')

def get_book_info(user_input: str) -> tuple | None:
    url = f"https://www.googleapis.com/books/v1/volumes?q={user_input}&key={API_KEY}"

    try:
        response = requests.get(url)
        response_json = response.json()

        if "items" in response_json:
            book_info = response_json["items"][0].get("volumeInfo", {})
            title = book_info.get("title", "Title not found")
            authors = book_info.get("authors", ["Author not found"])
            genre = book_info.get("categories", ["Genre not found"])
            images = book_info.get("imageLinks", {})
            cover_url = images.get("thumbnail", "Image not found")

            return title, authors, genre, cover_url

        return None

    except requests.exceptions.RequestException:
        return None

print(get_book_info("The Vegetarian"))