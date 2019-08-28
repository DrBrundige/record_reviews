from flask import Flask, render_template, redirect, request, flash, session
from flask_bcrypt import Bcrypt
from mysqlconnection import connectToMySQL

app = Flask(__name__)
app.secret_key = 'bigm00d'
bcrypt = Bcrypt(app)

from datetime import datetime, timedelta, date

import requests
import json
import base64


@app.route('/')
def index():
	update_auth_key()

	# print('Serving login screen')
	return render_template('login.html', u=session['temp_name'])


@app.route('/register', methods=['POST'])
def register():
	session['temp_name'] = request.form['username']

	print("Validating!")
	is_valid = True
	mysql = connectToMySQL('recordreviews')

	query = "SELECT * FROM users WHERE username=%(e)s"
	data = {
		"e": request.form['username'],
	}
	username = mysql.query_db(query, data)
	print(f"Username: {username}")

	print(request.form)

	if username.__len__() > 0:
		print("Username already exists!")
		flash("Username already exists!", 'register')
		is_valid = False
	if not request.form['pword1'] == request.form['pword2']:
		print("Passwords do not match!")
		flash("Passwords do not match!", 'register')
		is_valid = False
	if len(request.form['pword1']) < 8:
		print("Password too short!")
		flash("Password too short!", 'register')
		is_valid = False
	if request.form['pword1'].isalpha():
		print("Password too weak!")
		flash("Password too weak!", 'register')
		is_valid = False

	print(f"The registration is: { is_valid}")

	if is_valid:
		print("Registration Valid!")
		pw_hash = bcrypt.generate_password_hash(request.form['pword1'])

		query = "INSERT INTO users (username, password, created_at, updated_at) VALUES (%(u)s,%(p)s, now(), now());"
		data = {
			"u": request.form["username"],
			"p": pw_hash
		}
		print(query)
		print(data)
		mysql = connectToMySQL('recordreviews')
		id = mysql.query_db(query, data)
		print(id)

		print(f"Created new user with id {id}")
		session['id'] = id
		session['username'] = request.form['username']

		return redirect('/home')

	return redirect('/')


@app.route('/login', methods=['POST'])
def login():
	print(f"Logging the fuck on")

	mysql = connectToMySQL('recordreviews')

	query = "SELECT * FROM users WHERE username=%(e)s"
	data = {
		"e": request.form['name'],
	}
	username = mysql.query_db(query, data)
	print(f"Username: {username}")

	if len(username) == 0:
		print("User not found!")
		flash("Could not log in!", 'login')
	else:
		if bcrypt.check_password_hash(username[0]['password'], request.form['password']):
			print("Passwords match!")
			id = username[0]['id']
			session['id'] = id
			session['username'] = username[0]['username']
			return redirect('/home')
		else:
			print("Password incorrect!")
			flash("Could not log in!", 'login')

	return redirect('/')


@app.route('/home')
def home():
	if 'id' not in session:
		user = {'id': -1, 'username': ''}
	else:
		user = {'id': session['id'], 'username': session['username']}

	update_auth_key()
	access = session['key']
	head = {'Authorization': 'Bearer ' + access}

	params = {'country': 'us', 'limit': 12}

	r = requests.get('https://api.spotify.com/v1/browse/new-releases', headers=head, params=params)

	if r.status_code == 200:
		new_releases = r.json()

		# for result in new_releases['albums']['items']:
		# 	print(result['name'])

		return render_template('new_releases.html', nr=new_releases['albums']['items'], u=user)

	else:
		print('Request failed, error code: ' + str(r.status_code) + ' | ' + r.reason)

	return render_template('login.html')


@app.route('/record/<uri>')
def show_record(uri):
	user_review = []
	if 'id' not in session:
		user = {'id': -1, 'username': ''}
	else:
		user = {'id': session['id'], 'username': session['username']}
		mysql = connectToMySQL('recordreviews')

		query = "SELECT * FROM reviews WHERE album_uri = %(e)s AND user_id = %(u)s;"
		data = {
			"e": uri,
			"u": session['id'],
		}
		user_review = mysql.query_db(query, data)

	update_auth_key()
	access = session['key']
	head = {'Authorization': 'Bearer ' + access}
	r = requests.get('https://api.spotify.com/v1/albums/' + uri, headers=head)
	if r.status_code == 200:
		record_data = r.json()

		mysql = connectToMySQL('recordreviews')

		query = "SELECT reviews.id AS id, reviews.text, reviews.score, users.username as username, reviews.created_at FROM reviews JOIN users ON users.id = reviews.user_id WHERE album_uri = %(e)s ORDER BY reviews.created_at LIMIT 6;"
		data = {
			"e": uri,
			"u": session['id'],
		}
		reviews = mysql.query_db(query, data)

		score = 0

		for review in reviews:
			score += review['score']
		if len(reviews) > 0:
			score = score / len(reviews)

		tacos = get_tacos(score)

		return render_template('reviews_album.html', data=record_data, u=user, reviews=reviews, score=score,
		                       num=len(reviews), tacos=tacos, ur=user_review)

	elif r.status_code == 404:
		print('No such record! Redirecting to failure page')
		return render_template('no_album.html', uri=uri)
	else:
		print('Request failed, error code: ' + str(r.status_code) + ' | ' + r.reason)

	return redirect('/')


@app.route('/review', methods=['POST'])
def review():
	if 'id' not in session:
		session['id'] = -1

	if session['id'] == -1:
		print("Review failed! No user is logged in!")
		return redirect('/')
	else:
		query = "INSERT INTO reviews (score, text, album_uri, album_title, user_id, created_at, updated_at) VALUES (%(s)s, %(t)s, %(a)s, %(i)s, %(u)s, now(), now());"
		data = {
			"s": request.form["stars"],
			"t": request.form["text"],
			"a": request.form["uri"],
			"i": request.form["title"],
			"u": session['id']
		}
		print(query)
		print(data)
		mysql = connectToMySQL('recordreviews')
		print(mysql.query_db(query, data))

		print(f"Created new review!")

	return redirect(f'/user/{session["id"]}')


@app.route('/update', methods=['POST'])
def update():
	if 'id' not in session:
		session['id'] = -1

	if session['id'] == -1:
		print("Review failed! No user is logged in!")
		return redirect('/')
	else:
		query = "UPDATE reviews SET score = %(s)s, text = %(t)s, updated_at = now() WHERE id = %(i)s;"
		data = {
			"s": request.form["stars"],
			"t": request.form["text"],
			"i": request.form['id']
		}
		print(query)
		print(data)
		mysql = connectToMySQL('recordreviews')
		print(mysql.query_db(query, data))

		print(f"Updated review!")

	return redirect(f'/user/{session["id"]}')


@app.route('/user/<id>')
def dashboard(id):
	if 'id' not in session:
		current_user = {'id': -1, 'username': ''}
	else:
		current_user = {'id': session['id'], 'username': session['username']}

	mysql = connectToMySQL('recordreviews')

	query = "SELECT * FROM users WHERE id = %(i)s;"
	data = {
		"i": id,
	}
	this_user = mysql.query_db(query, data)

	if len(this_user) == 0:
		print(f"No user with id {id} exists!")
		return redirect('/')
	else:
		mysql = connectToMySQL('recordreviews')

		query = "SELECT * FROM reviews WHERE user_id = %(i)s;"
		data = {
			"i": id,
		}
		user_reviews = mysql.query_db(query, data)

		return render_template('user.html', user=this_user[0], u=current_user, ur=user_reviews)


@app.route('/review/<id>')
def show_review(id):
	if 'id' not in session:
		current_user = {'id': -1, 'username': '', 'likes': -1}
	else:
		# likes: 0 = user does not like review, 1 = user likes review, 2 = user is review author
		current_user = {'id': session['id'], 'username': session['username'], 'likes': 0}

	mysql = connectToMySQL('recordreviews')

	query = "SELECT reviews.id AS id, reviews.album_uri, reviews.album_title, reviews.text, reviews.score, users.username, users.id as user_id, reviews.created_at FROM reviews  JOIN users ON users.id = reviews.user_id WHERE reviews.id = %(i)s"
	data = {
		"i": id,
	}
	this_review = mysql.query_db(query, data)

	if len(this_review) == 0:
		print(f"No review with id {id} exists!")
		return redirect('/')
	else:
		tacos = get_tacos(this_review[0]['score'])

		# This query uses the same set of data as before
		mysql = connectToMySQL('recordreviews')
		query = "SELECT user_id FROM likes WHERE review_id = %(i)s"
		data = {
			"i": id,
		}
		likes = mysql.query_db(query, data)
		current_user['no_likes'] = len(likes)

		# Checks if logged in user wrote review
		if current_user['id'] == this_review[0]['user_id']:
			current_user['likes'] = 2
		else:
			for like in likes:
				if like['user_id'] == current_user['id']:
					current_user['likes'] = 1

		return render_template('show_review.html', r=this_review[0], u=current_user, t=tacos)


@app.route('/review/<id>/like')
def like_review(id):
	if 'id' in session:
		mysql = connectToMySQL('recordreviews')

		query = "INSERT INTO likes (user_id, review_id, created_at) VALUES (%(u)s,%(r)s,now())"
		data = {
			"u": session['id'],
			"r": id,
		}

		new_like = mysql.query_db(query, data)

	return redirect(f'/review/{id}')


@app.route('/review/<id>/unlike')
def unlike_review(id):
	if 'id' in session:
		mysql = connectToMySQL('recordreviews')

		query = "DELETE FROM likes WHERE user_id = %(u)s AND review_id = %(r)s"
		data = {
			"u": session['id'],
			"r": id,
		}

		delete_like = mysql.query_db(query, data)

	return redirect(f'/review/{id}')


@app.route('/review/<id>/delete')
def delete_review(id):
	if 'id' in session:
		mysql = connectToMySQL('recordreviews')
		query = "DELETE FROM likes WHERE review_id = %(r)s"
		data = {
			"r": id,
		}
		delete_likes = mysql.query_db(query, data)

		mysql = connectToMySQL('recordreviews')
		query = "DELETE FROM reviews WHERE id = %(r)s"
		data = {
			"r": id,
		}
		delete_likes = mysql.query_db(query, data)

	return redirect(f'/home')


@app.route('/search', methods=['POST'])
def search():
	if 'id' not in session:
		user = {'id': -1, 'username': ''}
	else:
		user = {'id': session['id'], 'username': session['username']}

	print(f"Searching for {request.form['search']}")
	search_str = ""
	for char in request.form['search']:
		if char == " ":
			search_str += "+"
		else:
			search_str += char

	return redirect(f'/search/{search_str}')


@app.route('/search/<str>')
def show_search(str):
	if 'id' not in session:
		user = {'id': -1, 'username': ''}
	else:
		user = {'id': session['id'], 'username': session['username']}

	update_auth_key()
	access = session['key']
	head = {'Authorization': 'Bearer ' + access}

	params = {'q': str, 'type': 'album', 'limit': 12}

	r = requests.get('https://api.spotify.com/v1/search', headers=head, params=params)

	if r.status_code == 200:
		search_results = r.json()

		# for result in search_results['albums']['items']:
		# 	print(result['name'])

		return render_template('search_results.html', sr=search_results['albums']['items'], str=str, u=user)

	else:
		print('Request failed, error code: ' + str(r.status_code) + ' | ' + r.reason)

	return render_template('login.html')


# Renews Spotify authentication key if it does not exist or has expired
# Also resets id if it does not exist
def update_auth_key():
	if 'id' not in session:
		session['id'] = -1
	if 'username' not in session:
		session['username'] = ""
	if 'temp_name' not in session:
		session['temp_name'] = ""

	if 'key' not in session:
		print("Auth key does not exist!")
		session['key'] = get_auth_key()
		session['time'] = datetime.now() + timedelta(minutes=55)
	if session['time'] < datetime.now():
		print("Auth key has expired!")
		session['key'] = get_auth_key()
		session['time'] = datetime.now() + timedelta(minutes=55)

	return


def get_auth_key():
	print("Resetting Auth key!")
	client_id_str = 'c6fbe9bb305a403491e9a9098434ed94' + ':' + '2ac0945809784998a447621a63d84584'
	client_id_64 = base64.b64encode(client_id_str.encode())

	payload = {'content-encoding': 'application/x-www-form-urlencoded', 'grant_type': 'client_credentials'}
	head = {'Authorization': b'basic ' + client_id_64}

	r = requests.post('https://accounts.spotify.com/api/token', data=payload, headers=head)

	if r.status_code == 200:
		data = r.json()
		access = data['access_token']
		return access
	else:
		return ""


def get_tacos(score):
	if score > 4.7:
		return "🌮🌮🌮🌮🌮"
	if score > 3.7:
		return "🌮🌮🌮🌮"
	if score > 2.7:
		return "🌮🌮🌮"
	if score > 1.7:
		return "🌮🌮"

	return "🌮"


@app.route('/logout')
def logout():
	print("Logging out")
	session.clear()

	return redirect('/')


print("Record Reviews 2019")

if __name__ == "__main__":
	app.run(debug=True)
