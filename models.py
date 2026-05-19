from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from datetime import date
from typing import List
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model,UserMixin):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    list_of_reading_books: Mapped[List["UserBooks"]] = relationship(back_populates="user_reader", cascade="all, delete",
        passive_deletes=True)
    list_of_communities_of_user: Mapped[List["UserCommunities"]] = relationship(back_populates="user_member")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User (id={self.id}, name={self.name})"


class Book(db.Model):
    __tablename__ = 'books'

    book_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('authors.author_id', ondelete='CASCADE'), nullable=False)
    genre: Mapped[str] = mapped_column(String, nullable=True)
    cover_url: Mapped[str] = mapped_column(String, nullable=True)

    list_of_readers: Mapped[List["UserBooks"]] = relationship(back_populates="reading_book")
    author_of_book: Mapped["Author"] = relationship(back_populates="books")

    def __repr__(self):
        return f"Book (id={self.book_id}, title={self.title})"


class UserBooks(db.Model):
    __tablename__ = 'user_books'

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(String, nullable=True)

    user_reader: Mapped["User"] = relationship(back_populates="list_of_reading_books")
    reading_book: Mapped["Book"] = relationship(back_populates="list_of_readers")

    def __repr__(self):
        return f"UserBooks (user_id={self.user_id}, book_id={self.book_id})"


class Author(db.Model):
    __tablename__ = 'authors'

    author_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=True)
    death_date: Mapped[date] = mapped_column(Date, nullable=True)

    books: Mapped[List["Book"]] = relationship(back_populates="author_of_book")

    def __repr__(self):
        return f"Author (id={self.author_id}, name={self.author_name})"


class Community(db.Model):
    __tablename__ = 'communities'

    community_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    community_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    about_community: Mapped[str] = mapped_column(String, nullable=True)

    list_of_members: Mapped[List["UserCommunities"]] = relationship(back_populates="user_community", cascade="all, delete",
        passive_deletes=True)

    def __repr__(self):
        return f"Community (id={self.community_id}, name={self.community_name})"


class UserCommunities(db.Model):
    __tablename__ = 'user_communities'

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    community_id: Mapped[int] = mapped_column(Integer, ForeignKey('communities.community_id', ondelete='CASCADE'), primary_key=True)

    user_member: Mapped["User"] = relationship(back_populates="list_of_communities_of_user")
    user_community: Mapped["Community"] = relationship(back_populates="list_of_members")

    def __repr__(self):
        return f"UserCommunities (user_id={self.user_id}, community_id={self.community_id})"