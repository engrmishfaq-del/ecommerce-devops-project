from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")

        if session.get("role") != "admin":
            return "Access Denied: Admins only!", 403

        return f(*args, **kwargs)

    return decorated_function

app = Flask(__name__)
app.secret_key = "mysecretkey"
UPLOAD_FOLDER = "static/images/products"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect("ecommerce.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        products=products
    )
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
            """, (name, email, hashed_password))

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already registered!"

        conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/dashboard")

            return redirect("/")

        return "Invalid email or password!"

    return render_template("login.html")
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")
@app.route("/add_product", methods=["GET", "POST"])
@admin_required
def add_product():

    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        category = request.form["category"]

        image = request.files["image"]
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
    INSERT INTO products (name, price, description, image, category)
    VALUES (?, ?, ?, ?, ?)
    """, (name, price, description, filename, category))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add_product.html")
@app.route("/edit_product/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_product(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    )

    product = cursor.fetchone()

    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        category = request.form["category"]

        image = request.files["image"]

        if image and image.filename:

            filename = secure_filename(image.filename)

            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            cursor.execute("""
                UPDATE products
                SET name=?, price=?, description=?, category=?, image=?
                WHERE id=?
            """, (
                name,
                price,
                description,
                category,
                filename,
                id
            ))

        else:

            cursor.execute("""
                UPDATE products
                SET name=?, price=?, description=?, category=?
                WHERE id=?
            """, (
                name,
                price,
                description,
                category,
                id
            ))

        conn.commit()
        conn.close()

        return redirect("/products")

    conn.close()

    return render_template(
        "edit_product.html",
        product=product
    )
@app.route("/products")
def products():

    conn = get_db()
    cursor = conn.cursor()

    search = request.args.get("search", "")
    category = request.args.get("category", "")

    if search and category:
        cursor.execute(
            "SELECT * FROM products WHERE name LIKE ? AND category=?",
            ("%" + search + "%", category)
        )

    elif search:
        cursor.execute(
            "SELECT * FROM products WHERE name LIKE ?",
            ("%" + search + "%",)
        )

    elif category:
        cursor.execute(
            "SELECT * FROM products WHERE category=?",
            (category,)
        )

    else:
        cursor.execute("SELECT * FROM products")

    products = cursor.fetchall()

    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()

    conn.close()

    return render_template(
        "products.html",
        products=products,
        categories=categories,
        search=search,
        category=category
    )
@app.route("/product/<int:id>")
def product_detail(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    )

    product = cursor.fetchone()

    conn.close()

    return render_template(
        "product_detail.html",
        product=product
    )    
    
@app.route("/categories")
def categories():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
        AND category != ''
    """)

    categories = cursor.fetchall()

    conn.close()

    return render_template(
        "categories.html",
        categories=categories
    )
@app.route("/delete_product/<int:id>")
@admin_required
def delete_product(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM products WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/products")
@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cart WHERE product_id=?", (id,))
    item = cursor.fetchone()

    if item:
        cursor.execute(
            "UPDATE cart SET quantity = quantity + 1 WHERE product_id=?",
            (id,)
        )
    else:
        cursor.execute(
            "INSERT INTO cart (product_id, quantity) VALUES (?, ?)",
            (id, 1)
        )

    conn.commit()
    conn.close()

    return redirect("/")
@app.route("/cart")
def cart():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT products.*, cart.quantity
    FROM cart
    JOIN products
    ON cart.product_id = products.id
    """)

    cart_items = cursor.fetchall()

    total = 0

    for item in cart_items:
        total += item["price"] * item["quantity"]

    conn.close()

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )
@app.route("/remove_from_cart/<int:id>")
def remove_from_cart(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT quantity FROM cart WHERE product_id=?",
        (id,)
    )

    item = cursor.fetchone()

    if item:

        if item["quantity"] > 1:

            cursor.execute(
                "UPDATE cart SET quantity = quantity - 1 WHERE product_id=?",
                (id,)
            )

        else:

            cursor.execute(
                "DELETE FROM cart WHERE product_id=?",
                (id,)
            )

    conn.commit()
    conn.close()

    return redirect("/cart")
@app.route("/increase_quantity/<int:id>")
def increase_quantity(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE cart SET quantity = quantity + 1 WHERE product_id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/cart")
@app.route("/decrease_quantity/<int:id>")
def decrease_quantity(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT quantity FROM cart WHERE product_id=?",
        (id,)
    )

    item = cursor.fetchone()

    if item:

        if item["quantity"] > 1:

            cursor.execute(
                "UPDATE cart SET quantity = quantity - 1 WHERE product_id=?",
                (id,)
            )

        else:

            cursor.execute(
                "DELETE FROM cart WHERE product_id=?",
                (id,)
            )

    conn.commit()
    conn.close()

    return redirect("/cart")
@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT products.*, cart.quantity
        FROM cart
        JOIN products
        ON cart.product_id = products.id
    """)

    cart_items = cursor.fetchall()

    total = 0

    for item in cart_items:
        total += item["price"] * item["quantity"]

    if request.method == "POST":

        customer_name = request.form["customer_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        address = request.form["address"]
        payment_method = request.form["payment_method"]

        user_id = session.get("user_id")

        if payment_method == "Demo Card":
            payment_status = "Paid"
            transaction_id = "DEMO-" + str(int(total))
            order_status = "Confirmed"
        else:
            payment_status = "Pending"
            transaction_id = None
            order_status = "Pending"

        cursor.execute("""
            INSERT INTO orders
            (
                customer_name,
                email,
                phone,
                address,
                total,
                user_id,
                status,
                payment_method,
                payment_status,
                transaction_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_name,
            email,
            phone,
            address,
            total,
            user_id,
            order_status,
            payment_method,
            payment_status,
            transaction_id
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    conn.close()

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )
@app.route("/my_orders")
def my_orders():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    )

    orders = cursor.fetchall()

    conn.close()

    return render_template("my_orders.html", orders=orders)
@app.route("/admin/orders")
@admin_required
def admin_orders():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT orders.*, users.name AS user_name
        FROM orders
        LEFT JOIN users ON orders.user_id = users.id
        ORDER BY orders.id DESC
    """)

    orders = cursor.fetchall()

    conn.close()

    return render_template("admin_orders.html", orders=orders)
@app.route("/admin/update_order/<int:id>", methods=["GET", "POST"])
@admin_required
def admin_update_order(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM orders WHERE id=?",
        (id,)
    )

    order = cursor.fetchone()

    if not order:
        conn.close()
        return "Order not found"

    if request.method == "POST":

        status = request.form["status"]

        cursor.execute(
            "UPDATE orders SET status=? WHERE id=?",
            (status, id)
        )

        conn.commit()
        conn.close()

        return redirect("/admin/orders")

    conn.close()

    return render_template(
        "admin_update_order.html",
        order=order
    )

@app.route("/dashboard")
@admin_required
def dashboard():

    conn = get_db()
    cursor = conn.cursor()

    # Total Products
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    # Total Orders
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    # Total Revenue
    cursor.execute("SELECT SUM(total) FROM orders")
    total_revenue = cursor.fetchone()[0]

    if total_revenue is None:
        total_revenue = 0

    # Pending Orders
    cursor.execute(
        "SELECT COUNT(*) FROM orders WHERE status = ?",
        ("Pending",)
    )
    pending_orders = cursor.fetchone()[0]

    # Delivered Orders
    cursor.execute(
        "SELECT COUNT(*) FROM orders WHERE status = ?",
        ("Delivered",)
    )
    delivered_orders = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        delivered_orders=delivered_orders
    )
       

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
