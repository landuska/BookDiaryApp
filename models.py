from datetime import date
from typing import List, Optional

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """Represents a system user for authentication and library management."""

    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    list_of_reading_books: Mapped[List["UserBooks"]] = relationship(back_populates="user_reader",
                                                                    cascade="all, delete-orphan",
                                                                    passive_deletes=True)
    list_of_communities_of_user: Mapped[List["UserCommunities"]] = relationship(back_populates="user_member",
                                                                                cascade="all, delete-orphan",
                                                                                passive_deletes=True)
    taste_profile: Mapped["UserTasteProfile"] = relationship(back_populates="user", uselist=False,
                                                             cascade="all, delete-orphan"
                                                             )

    def set_password(self, password: str) -> None:
        """Hashes the password and stores it in the database.

        Args:
            password: The plain-text password to hash.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies the plain-text password against the stored hash.

        Args:
            password: The plain-text password to check.

        Returns:
            bool: True if the password matches, False otherwise.
        """

        return check_password_hash(self.password_hash, password)

    @validates('name')
    def validate_username(self, key: str, value: str) -> str:
        """Validates that the username typed by the user is valid.
        Args:
            key: The name of the field.
            value: The name string.

        Returns:
            str: Validated name.

        Raises:
            ValueError: If the name is not validate.
        """
        if not value or not value.strip():
            raise ValueError("Username cannot be empty.")
        if len(value.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return value.strip()

    def __repr__(self) -> str:
        return f"User (id={self.id}, name={self.name})"


class Book(db.Model):
    """Represents a book available in the global catalog."""

    __tablename__ = 'books'

    book_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isbn: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    ai_summary: Mapped[str] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('authors.author_id', ondelete='CASCADE'), nullable=False)
    genre: Mapped[str] = mapped_column(String, nullable=True)
    cover_url: Mapped[str] = mapped_column(String, nullable=True)

    list_of_readers: Mapped[List["UserBooks"]] = relationship(back_populates="reading_book",
                                                              cascade="all, delete-orphan", passive_deletes=True)
    author_of_book: Mapped["Author"] = relationship(back_populates="books")

    def __repr__(self) -> str:
        return f"Book (id={self.book_id}, title={self.title})"


class UserBooks(db.Model):
    """Association model representing a user's personal book collection with reading progress."""

    __tablename__ = 'user_books'

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(String, nullable=True)

    user_reader: Mapped["User"] = relationship(back_populates="list_of_reading_books")
    reading_book: Mapped["Book"] = relationship(back_populates="list_of_readers")

    @validates('status')
    def validate_status(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validates that the status belongs to predefined reading states.

        Args:
            key: The name of the field.
            value: The status string.

        Returns:
            Optional[str]: Validated status.

        Raises:
            ValueError: If the status is not allowed.
        """
        allowed_statuses = {'Want to read', 'Currently reading', 'Completed'}
        if value is not None and value not in allowed_statuses:
            raise ValueError(f"Invalid status. Allowed statuses are: {allowed_statuses}")
        return value

    @validates('rating')
    def validate_rating(self, key: str, value: Optional[float]) -> Optional[float]:
        """Validates that the book rating is between 0.0 and 10.0.

        Args:
            key: The name of the field being validated.
            value: The rating score provided.

        Returns:
            Optional[float]: The validated rating value.

        Raises:
            ValueError: If the rating score is out of the 0-10 range.
        """
        if value is not None and (value < 0.0 or value > 10.0):
            raise ValueError("Rating must be between 0 and 10.")
        return value

    @validates('note')
    def validate_note(self, key: str, value: Optional[str]) -> Optional[str]:
        """Trims whitespace from the book note typed by the user.
        Args:
            key: The name of the field being validated.
            value: The text of notes.

        Returns:
            Returns: Optional[str]: The note's text without whitespace, or None.
        """
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped != "" else None

    def __repr__(self) -> str:
        return f"UserBooks (user_id={self.user_id}, book_id={self.book_id})"


class Author(db.Model):
    """Represents a book author with biographical details."""

    __tablename__ = 'authors'

    author_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=True)
    death_date: Mapped[date] = mapped_column(Date, nullable=True)

    books: Mapped[List["Book"]] = relationship(back_populates="author_of_book", cascade="all, delete-orphan",
                                               passive_deletes=True)

    def __repr__(self) -> str:
        return f"Author (id={self.author_id}, name={self.author_name})"


class Community(db.Model):
    """Represents a user community or a book club within the application."""

    __tablename__ = 'communities'

    community_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    community_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    about_community: Mapped[str] = mapped_column(String, nullable=True)

    list_of_members: Mapped[List["UserCommunities"]] = relationship(back_populates="user_community",
                                                                    cascade="all, delete-orphan",
                                                                    passive_deletes=True)

    @validates('community_name')
    def validate_community_name(self, key: str, value: str) -> str:
        """Validates the community name typed by the user.
        Args:
            key: The name of the field being validated.
            value: The community name string.

        Returns:
            str: The community's name without whitespace.
        """
        if not value or not value.strip():
            raise ValueError("Community name cannot be empty.")
        if len(value.strip()) < 3:
            raise ValueError("Community name must be at least 3 characters long.")
        return value.strip()

    @validates('about_community')
    def validate_about_community(self, key: str, value: Optional[str]) -> Optional[str]:
        """Trims whitespace from the community description typed by the user.
        Args:
            key: The name of the field being validated.
            value: The text of community description.

        Returns:
            Returns: Optional[str]: The note's text without whitespace, or None.
        """
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped != "" else None

    def __repr__(self) -> str:
        return f"Community (id={self.community_id}, name={self.community_name})"


class UserCommunities(db.Model):
    """Association model linking users to the communities they have joined."""

    __tablename__ = 'user_communities'

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    community_id: Mapped[int] = mapped_column(Integer, ForeignKey('communities.community_id', ondelete='CASCADE'),
                                              primary_key=True)

    user_member: Mapped["User"] = relationship(back_populates="list_of_communities_of_user")
    user_community: Mapped["Community"] = relationship(back_populates="list_of_members")

    def __repr__(self) -> str:
        return f"UserCommunities (user_id={self.user_id}, community_id={self.community_id})"


class UserTasteProfile(db.Model):
    """Represents a user's reading taste profile."""

    __tablename__ = 'user_taste_profile'

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    profile_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    update_at: Mapped[date] = mapped_column(Date, nullable=True)
    user: Mapped["User"] = relationship(back_populates="taste_profile")

    def __repr__(self) -> str:
        return f"UserTasteProfile (user_id={self.user_id}, profile_data={self.profile_data})"
