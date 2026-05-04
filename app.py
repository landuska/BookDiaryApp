from flask import Flask, render_template, request, redirect,  url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from models import *
from data_manage import DataManager
from helpers import *

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
    return render_template('books.html', books=books)


# *************** AUTHORS *************


@app.route('/authors', methods=['GET'])
def all_authors():
    authors = data_manager.get_entities(Author)
    return render_template('authors.html', authors=authors)


@app.route('/author/<int:author_id>', methods=['GET'])
def books_by_author(author_id):
    author = data_manager.get_entity_by_multiple_fields(Author, author_id=author_id, )
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
            return render_template('register.html')

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


@app.route('/user/<username>')
@login_required
def user_page(username):
    return render_template('user_page.html', username=username)


@app.route('/user/<username>/logout')
@login_required
def logout(username):
    logout_user()
    return redirect(url_for('index'))

@app.route('/user/<username>/delete', methods=['POST'])
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


@app.route('/user/<username>/my_books', methods=['GET'])
@login_required
def my_books(username):
    user_books = data_manager.get_books_by_user(user_id=current_user.id)
    return render_template('my_books.html', books=user_books)


@app.route('/user/<username>/add_book', methods=['GET', 'POST'])
@login_required
def add_book(username):
    if request.method == 'POST':
        input_title = request.form.get('title').strip()
        if not input_title:
            flash("Please enter a title")
            return redirect(url_for('add_book', username=current_user.name))

        book_data = get_book_info(input_title)

        if not book_data:
            flash(f"Book {input_title} not found")
            return redirect(url_for('add_book', username=current_user.name))

        api_title, authors, cover_url = book_data
        name_of_author = authors[0] if authors else "Unknown Author"

        try:
            author_obj = data_manager.get_entity_by_multiple_fields(Author, author_name=name_of_author)

            if not author_obj:
                data_manager.add_author(name=name_of_author)
                flash(f"Author '{name_of_author}' was added successfully")

                author_obj = data_manager.get_entity_by_multiple_fields(Author, author_name=name_of_author)

            if author_obj is None:
                raise ValueError(f"Could not retrieve author '{name_of_author}' from database.")

            book_obj = data_manager.get_entity_by_multiple_fields(Book, title=api_title)
            if not book_obj:
                new_book = Book(
                    title=api_title,
                    author_id=author_obj.author_id,
                    cover_url=cover_url
                )

                data_manager.add_book(new_book)
                book_obj = data_manager.get_entity_by_multiple_fields(Book, title=api_title)

            user_book = UserBooks(
                user_id=current_user.id,
                book_id=book_obj.book_id
            )

            data_manager.add_book_to_user(user_book.user_id, user_book.book_id)
            flash(f"Book '{api_title}' was added successfully")

        except ValueError as e:
            flash(str(e))

        except SQLAlchemyError as e:
            flash(f"Database error: {str(e)}")

        except Exception as e:
            flash(f"Some error occurred. Please try again: {str(e)}")

        return redirect(url_for('add_book', username=current_user.name))

    if request.method == 'GET':
        return render_template('add_book.html', username=current_user.name)


@app.route('/my_books/update/<int:book_id>', methods=['GET', 'POST'])
@login_required
def update_book_info(book_id):
    if request.method == 'POST':
        status = request.form.get('status')
        rating = request.form.get('rating')
        note = request.form.get('note')
        try:
            data_manager.update_user_book(current_user.id, book_id, status, rating, note)
            flash("Book was updated successfully")
            return redirect(url_for('my_books', username=current_user.name))

        except ValueError as e:
            flash(str(e))

        except SQLAlchemyError as e:
            flash(f"Database error: {str(e)}")

        except Exception as e:
            flash(f"Some error occurred. Please try again: {str(e)}")

        return redirect(url_for('my_books', username=current_user.name))

    if request.method == 'GET':
        user_book = data_manager.get_entity_by_multiple_fields(UserBooks, user_id=current_user.id, book_id=book_id)
        return render_template('book_info.html', book=user_book)


@app.route('/my_books/delete/<int:book_id>', methods=['POST'])
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
            return redirect(url_for('my_books', username=current_user.name))

        data_manager.delete(user_book)
        flash(f"Book was deleted successfully")

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('my_books', username=current_user.name))


# ********************* AUTHORS ************************


@app.route('/user/<username>/my_authors', methods=['GET'])
@login_required
def my_authors(username):
    authors = data_manager.get_authors_by_user(user_id=current_user.id)
    return render_template('my_authors.html', authors=authors)


# *******************+ COMMUNITIES *********************


@app.route('/user/<username>/my_communities', methods=['GET'])
@login_required
def my_communities(username):
    user_communities = data_manager.get_communities_by_user(user_id=current_user.id)
    return render_template('my_communities.html', communities=user_communities)


@app.route('/communities/create', methods=['GET', 'POST'])
@login_required
def create_community():
    if request.method == 'POST':
        input_name = request.form.get('name')
        if not input_name:
            flash("Please enter a name")
            return redirect(url_for('create_community'))

        try:
            data_manager.create_community(input_name)
            flash(f"Community '{input_name}' was created successfully")

            community_obj = data_manager.get_entity_by_multiple_fields(Community, community_name=input_name)

            data_manager.add_user_to_community(user_id=current_user.id, community_id=community_obj.community_id)
            flash(f"User was added to community successfully")
            return redirect(url_for('my_communities', username=current_user.name))

        except ValueError as e:
            flash(str(e))

        except SQLAlchemyError as e:
            flash(f"Database error: {str(e)}")

        except Exception as e:
            flash(f"Some error occurred. Please try again: {str(e)}")

        return redirect(url_for('create_community'))

    if request.method == 'GET':
        return render_template('create_community.html')


@app.route('/communities/join/<int:community_id>', methods=['POST'])
@login_required
def join_community(community_id):
    try:
        data_manager.add_user_to_community(current_user.id, community_id)
        flash(f"User joined to community successfully")
        return redirect(url_for('community_info', community_id=community_id))

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('my_communities', username=current_user.name))


@app.route('/communities/delete/<int:community_id>', methods=['POST'])
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
            return redirect(url_for('my_communities', username=current_user.name))

        data_manager.delete(user_community)
        flash("Community was deleted successfully")

    except ValueError as e:
        flash(str(e))

    except SQLAlchemyError as e:
        flash(f"Database error: {str(e)}")

    except Exception as e:
        flash(f"Some error occurred. Please try again: {str(e)}")

    return redirect(url_for('my_communities', username=current_user.name))


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