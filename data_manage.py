from models import User, Book, Author, Community, UserBooks, UserCommunities, db
from sqlalchemy.exc import IntegrityError
from datetime import date
from typing import Type

class DataManager():


# *********************** USER ***************************


    def add_user(self, name: str, password: str) -> None:
        existing_user = db.session.query(User).filter_by(name=name).first()
        if existing_user:
            raise ValueError(f"User with username '{name}' already exists.")
        try:
            new_user = User(name=name)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise


    def user_authorisation(self, name: str, password: str) -> None:
        user = db.session.query(User).filter_by(name=name).first()

        if user and user.check_password(password):
            return user

        raise ValueError(f"Invalid username or password, please, try again.")


# *********************** BOOK  ***************************


    def add_book(self, book: Book) -> None:
        try:
            db.session.add(book)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"Book {book} was already added to the user's library.")
        except Exception:
            db.session.rollback()
            raise


    def add_book_to_user(self, user_id: int, book_id: int) -> None:
        existing_book_by_user = db.session.query(UserBooks).filter_by(user_id=user_id,book_id=book_id).first()

        if existing_book_by_user:
            raise ValueError(f"This book is already in your library.")

        try:
            new_book_by_user = UserBooks(
                user_id=user_id,
                book_id=book_id
            )
            db.session.add(new_book_by_user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise


    def get_books_by_user(self, user_id: int):
        user = db.session.get(User, user_id)
        if user:
            return user.list_of_reading_books
        return []


    def update_user_book(self,
                                user_id: int,
                                book_id: int,
                                new_status: str = None,
                                new_rating: float = None,
                                new_note: str = None) -> None:
        book = db.session.get(UserBooks, (user_id, book_id))
        if book:
            try:
                if new_status is not None:
                    book.status = new_status
                if new_rating is not None:
                    book.rating = new_rating
                if new_note is not None:
                    book.note = new_note
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
        else:
            raise ValueError(f"User {user_id} or Book {book_id} is not found.")


# *********************** AUTHOR ***************************


    def add_author(self, name: str, birth_date: date = None, death_date: date = None) -> None:
        existing_author = db.session.query(Author).filter_by(author_name=name).first()
        if existing_author:
            raise ValueError(f"Author with name '{name}' already exists.")
        try:
            new_author = Author(author_name=name, birth_date=birth_date, death_date=death_date)
            db.session.add(new_author)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise


    def get_authors_by_user(self, user_id: int):
        user_books = db.session.query(UserBooks).filter_by(user_id=user_id).all()
        if user_books:
            authors = set()
            for pair in user_books:
                if pair.reading_book and pair.reading_book.author_of_book:
                    authors.add(pair.reading_book.author_of_book)
            return list(authors)
        return []


    def get_books_by_author(self, author_id: int):
        author = db.session.get(Author, author_id)
        if author:
            return author.books
        return []


# *********************** COMMUNITY ***************************


    def create_community(self, name: str) -> None:
        existing_community = db.session.query(Community).filter_by(community_name=name).first()
        if existing_community:
            raise ValueError(f"Community with name '{name}' already exists.")
        try:
            new_community = Community(community_name=name)
            db.session.add(new_community)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise


    def add_user_to_community(self, user_id: int, community_id: int) -> None:
        try:
            new_user_community_pair = UserCommunities(user_id=user_id, community_id=community_id)
            db.session.add(new_user_community_pair)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"User is already added to community {community_id}.")
        except Exception:
            db.session.rollback()
            raise


    def get_communities_by_user(self, user_id: int):
        user = db.session.get(User, user_id)
        if user:
            return user.list_of_communities_of_user
        return []


    def remove_user_from_community(self, user_id: int, community_id: int) -> None:
        user_community_pair = db.session.get(UserCommunities, (user_id, community_id))
        if user_community_pair:
            try:
                db.session.delete(user_community_pair)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
        else:
            raise ValueError("User is not a member of this community.")


# *********************** GENERAL ***************************


    def get_entities(self, model: Type[db.Model]):
        return db.session.query(model).all()


    def get_entity_by_multiple_fields(self, model: Type[db.Model], **kwargs):
        return db.session.query(model).filter_by(**kwargs).first()


    def get_entity_by_id(self, model: Type[db.Model], id: int):
        return db.session.get(model, id)


    def delete(self, entity) -> None:
        try:
            db.session.delete(entity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

