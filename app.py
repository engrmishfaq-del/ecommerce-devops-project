
from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename

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
@app.route("/add_product", methods=["GET", "POST"])
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
@app.route("/edit_product/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        image = request.form["image"]

        cursor.execute("""
        UPDATE products
        SET name=?, price=?, description=?, image=?
        WHERE id=?
        """, (name, price, description, image, id))

        conn.commit()
        conn.close()

        return redirect("/products")

    cursor.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cursor.fetchone()

    conn.close()

    return render_template("edit_product.html", product=product)
@app.route("/delete_product/<int:id>")
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

        cursor.execute("""
        INSERT INTO orders
        (customer_name, email, phone, address, total)
        VALUES (?, ?, ?, ?, ?)
        """, (customer_name, email, phone, address, total))

        conn.commit()

        return redirect("/")

    conn.close()

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )
@app.route("/orders")
def orders():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()

    conn.close()

    return render_template("orders.html", orders=orders)
@app.route("/dashboard")
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

    conn.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
