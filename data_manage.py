from models import User, Book, Author, Community, UserBooks, UserCommunities, db
from sqlalchemy.exc import IntegrityError
from datetime import date
from typing import Type, Optional, List

class DataManager:
    """A data manager class handling CRUD operations for the application's business logic.

    Provides an interface to manage users, books, authors, and communities using SQLAlchemy.
    """


# *********************** USER ***************************


    def add_user(self,name: str, password: str) -> None:
        """Registers a new user in the system.

        Args:
            name: The unique username.
            password: The raw password (to be hashed within the User model).

        Raises:
            ValueError: If a user with the given username already exists.
            Exception: If any database commit error occurs.
        """
        try:
            new_user = User(name=name)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"User with username '{name}' already exists.")
        except Exception:
            db.session.rollback()
            raise


    def user_authorisation(self, name: str, password: str) -> Optional[User]:
        """Authenticates a user with their username and password.

        Args:
            name: The username.
            password: The password to verify.

        Returns:
            User: The authenticated User object.

        Raises:
            ValueError: If the username or password is invalid.
        """
        user = db.session.query(User).filter_by(name=name).first()

        if user and user.check_password(password):
            return user

        raise ValueError(f"Invalid username or password. Please, try again.")


# *********************** BOOK  ***************************


    def add_book(self, book: Book) -> None:
        """Adds a new book to the global catalog.

        Args:
            book: An instance of the Book model.

        Raises:
            ValueError: If the book already exists in the database.
            Exception: If any database commit error occurs.
        """
        try:
            db.session.add(book)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"Book {book.title} already exists.")
        except Exception:
            db.session.rollback()
            raise


    def get_general_filtered_books(self, genre: str = None) -> List[Book]:
        """Retrieves all books from the catalog with genre filtering.

        Args:
            genre: The genre name to filter by. If "All" or None, filtering is skipped.

        Returns:
            List[Book]: A list of matching Book objects.
        """
        query = db.session.query(Book)

        if genre and genre != "All":
            query = query.filter(Book.genre == genre)

        books = query.all()

        return books

    def add_book_to_user(self, user_id: int, book_id: int) -> None:
        """Adds an existing book to a user's personal library.

        Args:
            user_id: The ID of the user.
            book_id: The ID of the book.

        Raises:
            ValueError: If the book is already in the user's library.
            Exception: If any database commit error occurs.
        """
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


    def get_books_by_user(self, user_id: int) -> List[UserBooks]:
        """Retrieves all UserBooks relationship records for a specific user.

        Args:
            user_id: The ID of the user.

        Returns:
            List[UserBooks]: A list of UserBooks objects, or an empty list if not found.
        """
        user = db.session.get(User, user_id)
        if user:
            return user.list_of_reading_books
        return []


    def get_filtered_books(self, user_id: int, status: str = None, min_rating: float = None, genre: str = None) -> List[UserBooks]:
        """Retrieves filtered books from a user's personal library.

        Args:
            user_id: The ID of the user.
            status: Reading status filter (e.g., 'Reading', 'Completed').
            min_rating: Minimum acceptable rating.
            genre: Genre name filter.

        Returns:
            List[UserBooks]: A list of filtered UserBooks relationship objects.
        """
        query = db.session.query(UserBooks).join(UserBooks.reading_book).filter(UserBooks.user_id == user_id)

        if status and status != "All":
            query = query.filter(UserBooks.status == status)

        if min_rating and min_rating > 0:
            query = query.filter(UserBooks.rating >= min_rating)

        if genre and genre != "All":
            query = query.filter(Book.genre == genre)

        books = query.all()
        return books


    def get_user_genres(self, user_id: int) -> List[str]:
        """Retrieves a sorted list of unique book genres in the user's library.

        Args:
            user_id: The ID of the user.

        Returns:
            List[str]: A sorted list of unique genre names.
        """
        genres_tuples = db.session.query(Book.genre).join(UserBooks).filter(UserBooks.user_id == user_id).distinct().all()
        return sorted([g[0] for g in genres_tuples if g[0] is not None])


    def update_user_book(self,
                                user_id: int,
                                book_id: int,
                                new_status: str = None,
                                new_rating: float = None,
                                new_note: str = None) -> None:
        """Updates metadata (status, rating, note) of a book in a user's library.

        Args:
            user_id: The ID of the user.
            book_id: The ID of the book.
            new_status: The new reading status.
            new_rating: The new rating score.
            new_note: The new text note.

        Raises:
            ValueError: If the UserBooks entry for the given IDs does not exist.
            Exception: If any database commit error occurs.
        """
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
            raise ValueError("UserBooks entry not found")


# *********************** AUTHOR ***************************


    def add_author(self, name: str, birth_date: date = None, death_date: date = None) -> None:
        """Adds a new author to the system.

        Args:
            name: The unique name of the author.
            birth_date: The birth date of the author.
            death_date: The death date of the author (optional).

        Raises:
            ValueError: If an author with the same name already exists.
            Exception: If any database commit error occurs.
        """
        try:
            new_author = Author(author_name=name, birth_date=birth_date, death_date=death_date)
            db.session.add(new_author)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"Author with name '{name}' already exists.")
        except Exception:
            db.session.rollback()
            raise


    def get_authors_by_user(self, user_id: int) -> List[Author]:
        """Retrieves a list of unique authors from the user's book collection.

        Args:
            user_id: The ID of the user.

        Returns:
            List[Author]: A list of unique Author objects.
        """

        authors = db.session.query(Author).join(Book).join(UserBooks, UserBooks.book_id == Book.book_id).filter(UserBooks.user_id == user_id).distinct().all()
        return authors


    def get_books_by_author(self, author_id: int)-> List[Book]:
        """Retrieves all books written by a specific author.

        Args:
            author_id: The ID of the author.

        Returns:
            List[Book]: A list of books associated with the author.
        """
        author = db.session.get(Author, author_id)
        if author:
            return author.books
        return []


# *********************** COMMUNITY ***************************


    def create_community(self, name: str, description: str = None) -> None:
        """Creates a new community.

        Args:
            name: The unique name of the community.
            description: A brief description of the community's purpose.

        Raises:
            ValueError: If a community with the same name already exists.
            Exception: If any database commit error occurs.
        """
        try:
            new_community = Community(community_name=name, about_community=description)
            db.session.add(new_community)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"Community with name '{name}' already exists.")
        except Exception:
            db.session.rollback()
            raise


    def update_community(self, community_id: int, name: str, description: str) -> None:
        """Updates the name and description of an existing community.

        Args:
            community_id: The ID of the community.
            name: The new name for the community.
            description: The new description.

        Raises:
            Exception: If any database commit error occurs.
        """
        community = db.session.get(Community, community_id)
        if community:
            try:
                community.community_name = name
                community.about_community = description
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
        else:
            raise ValueError(f"Community {community_id} is not found.")


    def add_user_to_community(self, user_id: int, community_id: int) -> None:
        """Joins/adds a user to a specific community.

        Args:
            user_id: The ID of the user.
            community_id: The ID of the community.

        Raises:
            ValueError: If the user is already a member of the community.
            Exception: If any database commit error occurs.
        """
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


    def get_communities_by_user(self, user_id: int)-> List[Community]:
        """Retrieves all communities a specific user belongs to.

        Args:
            user_id: The ID of the user.

        Returns:
            List[Community]: A list of communities associated with the user.
        """
        user = db.session.get(User, user_id)
        if user:
            return user.list_of_communities_of_user
        return []


    def remove_user_from_community(self, user_id: int, community_id: int) -> None:
        """Removes a user from a community (leave community).

        Args:
            user_id: The ID of the user.
            community_id: The ID of the community.

        Raises:
            ValueError: If the user is not a member of the community.
            Exception: If any database commit error occurs.
        """
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


    def get_entities(self, model: Type[db.Model]) -> List[db.Model]:
        """Retrieves all records for a given database model."""
        return db.session.query(model).all()


    def get_entity_by_multiple_fields(self, model: Type[db.Model], **kwargs) -> Optional[db.Model]:
        """Finds the first record matching arbitrary keyword filter arguments."""
        return db.session.query(model).filter_by(**kwargs).first()


    def get_entity_by_id(self, model: Type[db.Model], ent_id: int)-> Optional[db.Model]:
        """Finds a single record of a model by its primary key (ID)."""
        return db.session.get(model, ent_id)


    def delete(self, entity) -> None:
        """Deletes any given model instance from the database.

        Args:
            entity: The SQLAlchemy model object to delete.

        Raises:
            Exception: If any database commit error occurs.
        """
        try:
            db.session.delete(entity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

