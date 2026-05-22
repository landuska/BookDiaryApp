from flask import Flask, render_template, request, redirect,  url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from models import *
from data_manage import DataManager
from helpers import *
from openai_helpers import *


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:dlyaraboty_Python2026@localhost:5432/postgres"

db.init_app(app)

with app.app_context():
    db.create_all()

app.secret_key = 'flashkey'
login_manager = LoginManager(app)
login_manager.login_view = 'login'
data_manager = DataManager()


# ***********************************************
# ******** THE USER IS NOT LOGGED IN *********
# ***********************************************


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


# ***************** BOOKS ****************


@app.route('/books', methods=['GET'])
def all_books():
    books = data_manager.get_entities(Book)
    genre = request.args.get('genre', 'All')
    filtered_books = data_manager.get_general_filtered_books(genre=genre)
    genres = set()
    if books:
        for book in books:
            genres.add(book.genre)
    list_of_genres = sorted(list(genres))
    return render_template('books.html', books=filtered_books,genres=list_of_genres, selected_genre=genre)


@app.route('/books/<int:book_id>', methods=['GET'])
def book_public(book_id):

    book = data_manager.get_entity_by_id(Book, book_id)

    return render_template(
        "book_public.html",
        book=book
    )


# *************** AUTHORS *************


@app.route('/authors', methods=['GET'])
def all_authors():
    authors = data_manager.get_entities(Author)
    return render_template('authors.html', authors=authors)


@app.route('/authors/<int:author_id>', methods=['GET'])
def books_by_author(author_id):
    author = data_manager.get_entity_by_id(Author, author_id)
    if not author:
        flash("Author not found")
        return redirect(url_for('authors'))

    all_books = data_manager.get_books_by_author(author_id)
    return render_template('books_by_author.html', books=all_books, author=author)


# *************** COMMUNITIES ****************


@app.route('/communities', methods=['GET'])
def all_communities():
    communities = data_manager.get_entities(Community)
    return render_template('communities.html', communities=communities)


@app.route('/communities/<int:community_id>', methods=['GET'])
def community_info(community_id):
    community = data_manager.get_entity_by_multiple_fields(Community, community_id=community_id)
    members = community.list_of_members

    is_member = False
    if current_user.is_authenticated:
        for user in members:
            if user.user_id == current_user.id:
                is_member = True
                break

    return render_template('community_info.html', community=community,members=members,is_member=is_member)


# ***********************************************
# *************+ AUTHORISATION ******************
# ***********************************************


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip().lower()
        password = request.form.get('password').strip()

        if not username or not password:
            flash("Please fill in all fields")
            return redirect(url_for('register'))

        try:
            data_manager.add_user(name=username, password=password)
            flash(f"User '{username}' was created successfully")
            return redirect(url_for('index'))

        except ValueError as e:
            flash(str(e))

        except SQLAlchemyError as e:
            flash(f"Database error: {str(e)}")

        except Exception as e:
            flash(f"Some error occurred. Please try again: {str(e)}")


    if request.method == 'GET':
        return render_template('register.html')


@app.route('/', methods=['POST'])
def login():
    username = request.form.get('username').strip().lower()
    password = request.form.get('password').strip()

    try:
        user = data_manager.user_authorisation(name=username, password=password)
        if user:
            login_user(user)
            flash(f"Welcome back, {current_user.name}!")
            return redirect(url_for('user_page', username=current_user.name))

    except ValueError as e:
        flash(str(e))
        return redirect(url_for('index'))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")


@app.route('/<username>')
@login_required
def user_page(username):
    return render_template('user_page.html', username=username)


@app.route('/<username>/logout')
@login_required
def logout(username):
    logout_user()
    return redirect(url_for('index'))

@app.route('/<username>/delete', methods=['POST'])
@login_required
def delete_user(username):
    try:
        user = data_manager.get_entity_by_multiple_fields(
            User,
            id=current_user.id
        )

        if not user:
            flash("Account not found.")
            return redirect(url_for('user_page', username=current_user.name))

        data_manager.delete(user)
        flash(f"Your account was deleted successfully")

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('index'))


# *************************************************************
# ************* THE USER IS LOGGED IN ************************+
# *************************************************************

# ************* BOOKS **************************


@app.route('/<username>/user_books', methods=['GET'])
@login_required
def user_books(username):
    user = data_manager.get_entity_by_multiple_fields(User, name=username)

    status = request.args.get('status', 'All')
    rating = request.args.get('rating', type=float)
    genre = request.args.get('genre', 'All')

    all_user_books = data_manager.get_filtered_books(
        user_id=user.id,
        status=status,
        min_rating=rating,
        genre=genre
    )

    genres = data_manager.get_user_genres(current_user.id)

    is_owner = (current_user.id == user.id)
    return render_template('user_books.html', user=user, books=all_user_books,genres=genres, current_status=status,current_rating=rating,current_genre=genre,is_owner=is_owner)


@app.route('/<username>/add_book', methods=['GET', 'POST'])
@login_required
def add_book(username):
    if request.method == 'POST':
        input_title = request.form.get('title', '').strip()

        if not input_title:
            flash("No book title provided")
            return redirect(request.referrer or url_for('add_book', username=current_user.name))

        try:
            book_obj = data_manager.get_entity_by_multiple_fields(Book, title=input_title)
            if not book_obj:
                api_book_data = get_book_info(input_title)

                if not api_book_data:
                    flash(f"Book {input_title} not found")
                    return redirect(request.referrer or url_for('add_book', username=current_user.name))

                name_of_author = api_book_data.get('author')
                author_obj = data_manager.get_entity_by_multiple_fields(Author, author_name=name_of_author)

                if not author_obj:
                    data_manager.add_author(name=name_of_author)

                author_obj = data_manager.get_entity_by_multiple_fields(Author, author_name=name_of_author)

                new_book = Book(
                    isbn=api_book_data.get("isbn", ""),
                    description=api_book_data.get("description", ""),
                    title=api_book_data.get("title", ""),
                    author_id=author_obj.author_id,
                    genre=api_book_data.get("genre", ""),
                    cover_url=api_book_data.get("cover_url", "")
                )

                data_manager.add_book(new_book)

                book_obj = data_manager.get_entity_by_multiple_fields(Book, isbn=new_book.isbn)

            user_book = UserBooks(
                user_id=current_user.id,
                book_id=book_obj.book_id
            )

            data_manager.add_book_to_user(user_book.user_id, user_book.book_id)
            flash(f"Book '{book_obj.title}' was added successfully")

        except ValueError as e:
            flash(str(e))

        except SQLAlchemyError as e:
            flash(f"Database error: {str(e)}")

        except Exception as e:
            flash(f"Some error occurred. Please try again: {str(e)}")

        return redirect(request.referrer or url_for('add_book', username=current_user.name))

    if request.method == 'GET':
        return render_template('add_book.html', username=current_user.name)


@app.route('/<int:user_id>/user_books/<int:book_id>', methods=['GET'])
@login_required
def user_book_info(user_id, book_id):
    user_book = data_manager.get_entity_by_multiple_fields(UserBooks, user_id=user_id, book_id=book_id)
    if user_book is None:
        flash("Book not found in this library.")

    is_owner = (current_user.id == user_id)
    return render_template('book_info.html', book=user_book, is_owner=is_owner)


@app.route('/user_books/<int:book_id>/update', methods=['POST'])
@login_required
def update_book_info(book_id):
    status = request.form.get('status')
    rating = request.form.get('rating')
    note = request.form.get('note')
    try:
        data_manager.update_user_book(current_user.id, book_id, status, rating, note)
        flash("Book was updated successfully")
        return redirect(url_for('user_books', username=current_user.name))

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('user_books', username=current_user.name))


@app.route('/user_books/<int:book_id>/delete', methods=['POST'])
@login_required
def delete_book(book_id: int):
    try:
        user_book = data_manager.get_entity_by_multiple_fields(
            UserBooks,
            user_id=current_user.id,
            book_id=book_id
        )

        if not user_book:
            flash("Book not found in your collection.")
            return redirect(url_for('user_books', username=current_user.name))

        data_manager.delete(user_book)
        flash(f"Book was deleted successfully")

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('user_books', username=current_user.name))


# ********************* AUTHORS ************************


@app.route('/<username>/user_authors', methods=['GET'])
@login_required
def user_authors(username):
    authors = data_manager.get_authors_by_user(user_id=current_user.id)
    return render_template('user_authors.html', authors=authors)


# *******************+ COMMUNITIES *********************


@app.route('/<username>/communities', methods=['GET'])
@login_required
def user_communities(username):
    all_user_communities = data_manager.get_communities_by_user(user_id=current_user.id)
    return render_template('user_communities.html', communities=all_user_communities)


@app.route('/communities/create', methods=['GET', 'POST'])
@login_required
def create_community():
    if request.method == 'POST':
        input_name = request.form.get('name')
        input_description = request.form.get('description')

        if not input_name:
            flash("Please enter a name")
            return redirect(url_for('create_community'))

        try:
            data_manager.create_community(input_name, input_description)
            flash(f"Community '{input_name}' was created successfully")

            community_obj = data_manager.get_entity_by_multiple_fields(Community, community_name=input_name)

            data_manager.add_user_to_community(user_id=current_user.id, community_id=community_obj.community_id)
            flash(f"User was added to community successfully")
            return redirect(url_for('user_communities', username=current_user.name))

        except ValueError as e:
            flash(str(e))

        except SQLAlchemyError as e:
            flash(f"Database error: {str(e)}")

        except Exception as e:
            flash(f"Some error occurred. Please try again: {str(e)}")

        return redirect(url_for('create_community'))

    if request.method == 'GET':
        return render_template('create_community.html')


@app.route('/communities/<int:community_id>/update', methods=['POST'])
@login_required
def update_community(community_id):
    new_name = request.form.get('name')
    new_description = request.form.get('description')

    try:
        data_manager.update_community(community_id, new_name, new_description)
        flash(f"Community '{new_name}' was updated successfully")
        return redirect(url_for('community_info', community_id=community_id))

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('user_communities', username=current_user.name))


@app.route('/communities/<int:community_id>/join', methods=['POST'])
@login_required
def join_community(community_id):
    try:
        data_manager.add_user_to_community(current_user.id, community_id)
        flash(f"User joined to community successfully")

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('user_communities', username=current_user.name))


@app.route('/<int:community_id>/members', methods=['GET'])
@login_required
def community_members(community_id):
    community = data_manager.get_entity_by_id(Community, ent_id=community_id)

    is_member = any(member.user_id == current_user.id for member in community.list_of_members)
    if not is_member:
        flash("You must be a member to see this page.")
        return redirect(url_for('community_info', community_id=community_id))

    return render_template('community_members.html', community=community)


@app.route('/communities/<int:community_id>/leave', methods=['POST'])
@login_required
def leave_community(community_id: int):
    try:
        user_community = data_manager.get_entity_by_multiple_fields(
            UserCommunities,
            user_id=current_user.id,
            community_id=community_id
        )

        if not user_community:
            flash("Community not found.")
            return redirect(url_for('user_communities', username=current_user.name))

        data_manager.delete(user_community)
        flash("Community was deleted successfully")

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('user_communities', username=current_user.name))


@app.route('/communities/<int:community_id>/delete', methods=['POST'])
@login_required
def delete_community(community_id: int):
    try:
        community_obj = data_manager.get_entity_by_id(Community, community_id)

        if not community_obj:
            flash("Community not found.")
            return redirect(url_for('user_communities', username=current_user.name))

        data_manager.delete(community_obj)
        flash("Community was deleted successfully")

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('user_communities', username=current_user.name))

# *********************************************
# ************ ERRORS *************************
# **********************************************


@app.errorhandler(404)
def page_not_found(error):
    """Custom error handler for 404 (Page Not Found) errors."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    """Custom error handler for 500 (Internal Server Error) errors."""
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)