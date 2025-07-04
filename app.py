from flask import Flask, render_template, request, redirect, url_for,session,flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for sessions

# Dummy login data
OWNER_USERNAME = "owner"
OWNER_PASSWORD = "1234"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == OWNER_USERNAME and password == OWNER_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('owner_dashboard'))
        else:
            flash("Invalid Credentials", "error")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Initialize database
def init_db():
    conn = sqlite3.connect('kirana.db')
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_name TEXT,
                  phone_number TEXT,
                  order_date TEXT,
                  status TEXT DEFAULT 'Pending')''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS order_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_id INTEGER,
                  item_name TEXT,
                  quantity INTEGER,
                  availability TEXT DEFAULT 'Yes',
                  price REAL,
                  FOREIGN KEY(order_id) REFERENCES orders(id))''')
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/place_order', methods=['POST'])
def place_order():
    customer_name = request.form['name']
    phone_number = request.form['phone']
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save order to database
    conn = sqlite3.connect('kirana.db')
    c = conn.cursor()
    
    c.execute("INSERT INTO orders (customer_name, phone_number, order_date) VALUES (?, ?, ?)",
              (customer_name, phone_number, order_date))
    order_id = c.lastrowid
    
    # Save each item
    item_names = request.form.getlist('item_name[]')
    quantities = request.form.getlist('quantity[]')
    
    for item_name, quantity in zip(item_names, quantities):
        if item_name.strip():  # Only save if item name is not empty
            c.execute("INSERT INTO order_items (order_id, item_name, quantity) VALUES (?, ?, ?)",
                      (order_id, item_name, quantity))
    
    conn.commit()
    conn.close()
    
    return render_template('order_confirmation.html', phone_number=phone_number)

@app.route('/check_status', methods=['GET', 'POST'])
def check_status():
    if request.method == 'POST':
        phone_number = request.form['phone']
        
        conn = sqlite3.connect('kirana.db')
        c = conn.cursor()
        
        # Get all orders for this phone number
        c.execute("SELECT * FROM orders WHERE phone_number=? ORDER BY order_date DESC", (phone_number,))
        orders = c.fetchall()
        
        order_details = []
        for order in orders:
            order_id = order[0]
            c.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,))
            items = c.fetchall()
            
            # Calculate total bill
            total = sum(item[5] for item in items if item[5] is not None)
            
            order_details.append({
                'order_id': order_id,
                'date': order[3],
                'status': order[4],
                'items': items,
                'total': total
            })
        
        conn.close()
        return render_template('order_status.html', orders=order_details, phone_number=phone_number)
    
    return render_template('order_status.html')

@app.route('/owner')
def owner_dashboard():
    conn = sqlite3.connect('kirana.db')
    c = conn.cursor()
    
    # Get all orders grouped by date and phone number
    c.execute("SELECT * FROM orders ORDER BY order_date DESC")
    orders = c.fetchall()
    
    order_details = []
    for order in orders:
        order_id = order[0]
        c.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,))
        items = c.fetchall()
        
        # Calculate total bill
        total = sum(item[5] for item in items if item[5] is not None)
        
        order_details.append({
            'order_id': order_id,
            'customer_name': order[1],
            'phone_number': order[2],
            'date': order[3],
            'status': order[4],
            'items': items,
            'total': total
        })
    
    conn.close()
    return render_template('owner_dashboard.html', orders=order_details)

@app.route('/update_order', methods=['POST'])
def update_order():
    order_id = request.form['order_id']
    
    conn = sqlite3.connect('kirana.db')
    c = conn.cursor()
    
    # Update each item's availability and price
    item_ids = request.form.getlist('item_id[]')
    availabilities = request.form.getlist('availability[]')
    prices = request.form.getlist('price[]')
    
    for item_id, availability, price in zip(item_ids, availabilities, prices):
        c.execute("UPDATE order_items SET availability=?, price=? WHERE id=?",
                  (availability, float(price) if price else None, item_id))
    
    # Update order status if marked as packed
    if 'mark_packed' in request.form:
        c.execute("UPDATE orders SET status='Packed' WHERE id=?", (order_id,))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('owner_dashboard'))

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    conn = sqlite3.connect('kirana.db')
    c = conn.cursor()
    
    # Delete order items first (due to foreign key constraint)
    c.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
    # Then delete the order itself
    c.execute("DELETE FROM orders WHERE id=?", (order_id,))
    
    conn.commit()
    conn.close()
    
    flash("Order deleted successfully.", "success")
    return redirect(url_for('owner_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)