import os

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")
API_KEY = os.getenv('API_KEY')


def is_valid_book(info: dict) -> bool:
    """
    Determines whether a book entry from the Google Books API is valid.

    This function filters out non-relevant or low-quality entries such as:
    magazines, journals, newsletters, reference materials, and similar content
    that is not considered a standard book.

    Args:
        info (dict): A dictionary containing book metadata from Google Books API.

    Returns:
        bool: True if the book is valid, False if it should be filtered out.
    """

    title = info.get("title", "").lower()
    categories = " ".join(info.get("categories") or []).lower()

    banned = ["magazine", "journal", "newsletter", "gazette", "reference", "annotation", "periodical"]

    return not any(b in title or b in categories for b in banned)


def get_books_info(user_input: str) -> list[dict] | None:
    """
    Fetches a list of books from the Google Books API based on user input.

    The function searches for books matching the given query, filters out
    irrelevant content (e.g., magazines or journals), and returns a structured
    list of book dictionaries.

    Args:
        user_input (str): Search term provided by the user (title or author).

    Returns:
        list[dict] | None: A list of book dictionaries containing:
            - isbn (str)
            - description (str)
            - title (str)
            - author (str)
            - genre (str)
            - cover_url (str)
        Returns None if no results are found or if a request error occurs.
    """

    params = {
        "q": user_input,
        "maxResults": 5,
        "orderBy": "relevance",
        "printType": "books",
        "key": API_KEY
    }

    url = f"https://www.googleapis.com/books/v1/volumes"

    try:
        response = requests.get(
            url=url,
            params=params
        )

        response.raise_for_status()
        response_json = response.json()
        items = response_json.get("items", [])

        if not items:
            return None

        books = []

        for item in items:
            isbn = ""
            author = ""
            genre = ""

            book_info = item.get("volumeInfo", {})

            if not is_valid_book(book_info):
                continue

            isbn_list = book_info.get("industryIdentifiers", [])
            description = book_info.get("description", "")
            title = book_info.get("title", "")
            authors_list = book_info.get("authors", [])
            genre_list = book_info.get("categories", [])
            images = book_info.get("imageLinks", {})
            cover_url = images.get("thumbnail", "")

            if isbn_list:
                isbn = isbn_list[0].get("identifier")

            if genre_list:
                genre = genre_list[0]

            if authors_list:
                author = authors_list[0]

            books.append({
                "isbn": isbn,
                "description": description,
                "title": title,
                "author": author,
                "genre": genre,
                "cover_url": cover_url
            })

        return books

    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        return None
