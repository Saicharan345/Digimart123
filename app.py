from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            image TEXT,
            price REAL,
            description TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

@app.route('/', methods=['GET'])
def main_page():
    return render_template('main.html')

@app.route('/intro', methods=['GET', 'POST'])
def intro():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        if action == 'signup':
            try:
                hashed_pw = generate_password_hash(password)
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
                conn.commit()
                return redirect(url_for('intro'))
            except:
                return "Username already exists!"

        elif action == 'login':
            c.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                return redirect(url_for('marketplace'))
            else:
                return "Invalid login!"
        conn.close()
    return render_template('intro.html')

@app.route('/marketplace')
def marketplace():
    if 'user_id' not in session:
        return redirect(url_for('intro'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        SELECT ads.id, item_name, price, image, description, users.username, users.id
        FROM ads
        JOIN users ON ads.user_id = users.id
    ''')
    ads = c.fetchall()
    conn.close()
    return render_template('marketplace.html', username=session['username'], ads=ads)

@app.route('/create', methods=['GET', 'POST'])
def create_order():
    if 'user_id' not in session:
        return redirect(url_for('intro'))

    if request.method == 'POST':
        item_name = request.form['item_name']
        price = request.form['price']
        description = request.form['description']

        image_file = request.files['image']
        if image_file:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
        else:
            filename = ""

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''INSERT INTO ads (user_id, item_name, image, price, description)
                     VALUES (?, ?, ?, ?, ?)''',
                  (session['user_id'], item_name, filename, price, description))
        conn.commit()
        conn.close()

        return redirect(url_for('marketplace'))

    return render_template('create_order.html')

@app.route('/your-orders')
def your_orders():
    if 'user_id' not in session:
        return redirect(url_for('intro'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT item_name, price, image, description FROM ads WHERE user_id = ?", (session['user_id'],))
    orders = c.fetchall()
    conn.close()

    return render_template('your_orders.html', orders=orders)

@app.route('/edit-orders')
def edit_orders():
    if 'user_id' not in session:
        return redirect(url_for('intro'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, item_name, price, image, description FROM ads WHERE user_id = ?", (session['user_id'],))
    ads = c.fetchall()
    conn.close()

    return render_template('edit_orders.html', ads=ads)

@app.route('/edit/<int:ad_id>', methods=['GET', 'POST'])
def edit_ad(ad_id):
    if 'user_id' not in session:
        return redirect(url_for('intro'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        item_name = request.form['item_name']
        price = request.form['price']
        description = request.form['description']
        image_file = request.files['image']

        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
        else:
            c.execute("SELECT image FROM ads WHERE id = ?", (ad_id,))
            filename = c.fetchone()[0]

        c.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        c.execute('''INSERT INTO ads (user_id, item_name, image, price, description)
                     VALUES (?, ?, ?, ?, ?)''',
                  (session['user_id'], item_name, filename, price, description))
        conn.commit()
        conn.close()
        return redirect(url_for('edit_orders'))

    c.execute("SELECT item_name, price, description, image FROM ads WHERE id = ?", (ad_id,))
    ad = c.fetchone()
    conn.close()
    return render_template('edit_ad.html', ad=ad, ad_id=ad_id)

@app.route('/delete/<int:ad_id>')
def delete_ad(ad_id):
    if 'user_id' not in session:
        return redirect(url_for('intro'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM ads WHERE id = ? AND user_id = ?", (ad_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_orders'))

@app.route('/message/<int:receiver_id>', methods=['GET', 'POST'])
def message(receiver_id):
    if 'user_id' not in session:
        return redirect(url_for('intro'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        content = request.form['content']
        c.execute("INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
                  (session['user_id'], receiver_id, content))
        conn.commit()

    c.execute('''SELECT users.username, messages.content, messages.sender_id
                 FROM messages
                 JOIN users ON messages.sender_id = users.id
                 WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
                 ORDER BY messages.timestamp''',
              (session['user_id'], receiver_id, receiver_id, session['user_id']))
    messages = c.fetchall()

    c.execute("SELECT username FROM users WHERE id = ?", (receiver_id,))
    receiver_name = c.fetchone()[0]
    conn.close()
    return render_template("message.html", messages=messages, receiver_name=receiver_name, receiver_id=receiver_id)

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('intro'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        SELECT DISTINCT u.id, u.username FROM users u
        JOIN messages m ON (m.sender_id = u.id OR m.receiver_id = u.id)
        WHERE u.id != ? AND (m.sender_id = ? OR m.receiver_id = ?)
    ''', (session['user_id'], session['user_id'], session['user_id']))
    threads = c.fetchall()
    conn.close()
    return render_template("messages.html", threads=threads)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main_page'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
