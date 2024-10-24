import requests
import os
import pandas as pd

from flask import Flask, request, render_template, redirect, url_for, session, flash

from utils import Literature, get_genai_response


app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generates a random 24-byte key

# Predefined credentials for authentication
VALID_USERNAME = "admin"
VALID_PASSWORD = "admin123"


# Decorator function to ensure user is logged in before accessing certain routes
def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' in session:  # Check if user is logged in
            return f(*args, **kwargs)
        else:
            flash('You need to log in first')  # Flash a message if not logged in
            return redirect(url_for('login'))  # Redirect to login page
    wrap.__name__ = f.__name__
    return wrap

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # Handle login form submission
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == VALID_USERNAME and password == VALID_PASSWORD:  # Validate credentials
            session['logged_in'] = True  # Set session variable for logged-in status
            session['username'] = username  # Store username in session
            return redirect(url_for('search_query'))  # Redirect to automation page
        else:
            message = 'Invalid username or password'  # Error message for invalid login
            return render_template('login.html', message=message)  # Render login page with message
    
    return render_template('login.html')  # Render login page


@app.route('/logout')
@login_required  # Protect logout route with login requirement
def logout():
    session.pop('logged_in', None)  # Remove logged-in status from session
    session.pop('username', None)  # Remove username from session
    flash('You have been logged out')  # Flash logout message
    return redirect(url_for('login'))  # Redirect to login page


@app.route('/search_query', methods=['GET', 'POST'])
def search_query():
    # articles = []
    if request.method == 'POST':
        query = request.form.get('query')
        lit_obj = Literature(query)
        uids = lit_obj.search_pubmed()
        if uids:
            xml_data = lit_obj.fetch_details(uids)
            articles = lit_obj.parse_article_details(uids, xml_data)
            list_article= get_genai_response(articles)

            return render_template('index.html', articles=list_article, show_sidebar=True)
    return render_template('search.html')


# def index():
    

@app.route('/article/<uid>', methods=['GET'])
def article_details(uid):
    file_path = os.path.join('Reports', 'All_Literature.xlsx')
    df = pd.read_excel(file_path)

    df['UID'] = df['UID'].astype(str)
    uid = str(uid)
    article_data = df[df['UID'] == uid]

    # Check if any rows match the uid
    if not article_data.empty:
        article_dict = article_data.iloc[0].to_dict()
        # print('')
        return render_template('details.html', article=article_dict, show_sidebar=True)
    else:
        return render_template('error.html', message="No article found with UID: " + uid), 404



# @app.route('/article/<uid>')
# def article(uid):
#     article_details = fetch_pubmed_article(uid)
#     return render_template('article.html', article=article_details, show_sidebar=True)


if __name__ == "__main__":
    app.run(debug=True)
