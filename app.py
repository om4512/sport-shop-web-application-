from flask import Flask, render_template, request, redirect, url_for, session, flash , send_from_directory
import mysql.connector
import mysql.connector.errors as mysql_errors
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
import os
app = Flask("Krida")
app.secret_key = os.urandom(24)
UPLOAD_FOLDER=os.path.join(os.getcwd(),"static","uploads")
ALLOWED_EXTENSIONS={"png","jpg","jpeg","gif"}
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
app.config["UPLOAD_FOLDER"]=UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"]=4*1024*1024
DB_CONFIG ={
   "host":"localhost",
   "user":"root",
   "password":"032312",
   "database":"Krida",
   "auth_plugin":"mysql_native_password"
}
def get_connection():
   return mysql.connector.connect(**DB_CONFIG)
def allowed_file(filename):
   return"." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS
def login_required(f):
   @wraps(f)
   def decorated(*args, **kwargs):
        if 'user_id' not in session:
           flash("Login required","Warning")
           return redirect(url_for("login"))
        return f(*args, **kwargs)
   return decorated
def admin_required(f):
   @wraps(f)
   def decorated(*args, **kwargs):
      if not session.get("is_admin"):
         flash("Admin access required.", "danger")
         return redirect(url_for("index"))
      return f(*args, **kwargs)
   return decorated
@app.route("/register", methods=["GET","POST"])
def register():
   if request.method=="POST":
      username=request.form.get("username","").strip()
      email=request.form.get("email","").strip()
      password=request.form.get("password","").strip()
      pw_hash=generate_password_hash(password)
      conn = get_connection()
      cursor = conn.cursor()
      try:
         cursor.execute("INSERT INTO users (username, email, password_hash, is_admin)VALUES (%s,%s,%s,%s)" ,(username, email or None, pw_hash,False),)
         conn.commit()
         flash("Registration succesfull - please log in.","success")
         return redirect(url_for("login"))
      except mysql_errors.IntegrityError:
         flash("Username or email already exists.","danger")
         return redirect(url_for("register"))
      finally:
         cursor.close()
         conn.close()
   return render_template("register.html")
@app.route("/login",methods=["GET","POST"])
def login():
   if request.method == "POST":
      username = request.form.get("username","").strip()
      password= request.form.get("password","").strip()
      conn = get_connection()
      cursor = conn.cursor(dictionary=True)
      cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
      user = cursor.fetchone()
      cursor.close()
      conn.close()
      if user and check_password_hash(user["password_hash"], password):
         session["user_id"]=user["id"]
         session["username"]=user["username"]
         session["is_admin"]=bool(user["is_admin"])
         flash(f"Welcome,{user['username']}!","success")
         return redirect(url_for("index"))
      else:
         flash("Invalid username or password.","danger")
         return redirect(url_for("login"))
   return render_template("login.html") 
@app.route("/logout")
@login_required
def logout():
   session.clear()
   flash("Logged out.","info")
   return redirect(url_for("login"))   
@app.route("/")
@login_required
def index():
   conn = get_connection()
   cursor = conn.cursor(dictionary=True)
   cursor.execute("SELECT * FROM equipment ORDER BY created_at DESC")
   items = cursor.fetchall()
   cursor.close()
   conn.close()
   return render_template("index.html", items=items)
@app.route("/equipment/<int:item_id>")
@login_required
def equipment_detail(item_id):
   conn = get_connection()
   cursor = conn.cursor(dictionary=True)
   cursor.execute("SELECT * FROM equipment WHERE id = %s", (item_id,))
   item = cursor.fetchone()
   cursor.close()
   conn.close()
   if not item:
      flash("Item not found.","Warning")
      return redirect(url_for("index"))
   return render_template("equipment_detail.html", item=item)
@app.route("/dashboard")
@login_required
@admin_required
def dashboard():
   conn = get_connection()
   cursor = conn.cursor(dictionary=True)
   cursor.execute("SELECT COUNT(*) AS total_users FROM users")
   total_users = cursor.fetchone()["total_users"]
   cursor.execute("SELECT COUNT(*) AS total_products FROM equipment")
   total_products= cursor.fetchone()["total_products"]
   cursor.execute("SELECT SUM(stock) AS total_stock FROM equipment")
   total_stock = cursor.fetchone()["total_stock"] or 0 
   cursor.execute("SELECT COUNT(*) AS cart_items FROM cart")
   cart_items = cursor.fetchone()["cart_items"]
   cursor.execute("SELECT * FROM  equipment ORDER BY created_at DESC LIMIT 5")
   recent = cursor.fetchall()
   cursor.close()
   conn.close()
   print("is_admin:", session.get("is_admin"))
   return render_template("dashboard.html", total_users=total_users, total_products=total_products, total_stock=total_stock, cart_items=cart_items, recent=recent)
@app.route("/equipment/add", methods= ["GET","POST"])
@login_required
@admin_required
def add_equipment():
   if request.method == "POST":
      name= request.form.get("name","").strip()
      category = request.form.get("category","").strip()
      description = request.form.get("description","").strip()
      price = request.form.get("price","0")
      stock = request.form.get("stock","0")
      file= request.files.get("image")
      if file and file.filename !="" and allowed_file(file.filename):
       filename = secure_filename(file.filename)
       base, ext = os.path.splitext(filename)
       filename=f"{base}_{int(os.times().system)}{ext}"
       dest = os.path.join(app.config["UPLOAD_FOLDER"], filename)
       file.save(dest)
       image_filename = filename
      conn= get_connection()
      cursor = conn.cursor()
      cursor.execute("INSERT INTO equipment(name,category,description,price,stock,image) VALUES (%s,%s,%s,%s,%s,%s)" ,(name, category,description, price,stock,image_filename))
      conn.commit()
      cursor.close()
      conn.close()
      flash("Equipment added successfully.","success")
      return redirect(url_for("index"))
   return render_template("add_product.html")
@app.route("/equipment/edit/<int:item_id>", methods=["GET","POST"])
@login_required
@admin_required
def edit_equipment(item_id):
   conn = get_connection()
   cursor = conn.cursor(dictionary=True)
   cursor.execute("SELECT * FROM equipment WHERE id=%s", (item_id,))
   item = cursor.fetchone()

   if not item:
        cursor.close()
        conn.close()
        flash("Item not found.", "warning")
        return redirect(url_for("index"))

   if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "0")
        stock = request.form.get("stock", "0")

        file = request.files.get("image")
        if file and file.filename != "" and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(os.times().system)}{ext}"
            dest = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(dest)
            cursor.execute(
                "UPDATE equipment SET name=%s, category=%s, description=%s, price=%s, stock=%s, image=%s WHERE id=%s",
                (name, category, description, price, stock, filename, item_id)
            )
        else:
            cursor.execute(
                "UPDATE equipment SET name=%s, category=%s, description=%s, price=%s, stock=%s WHERE id=%s",
                (name, category, description, price, stock, item_id)
            )

        conn.commit()
        cursor.close()
        conn.close()
        flash("Equipment updated.", "success")
        return redirect(url_for("equipment_detail", item_id=item_id))

   cursor.close()
   conn.close()
   return render_template("update_product.html",item=item)
@app.route("/equipment/delete/<int:item_id>",methods=["POST"])
@login_required
@admin_required
def delete_equipment(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image FROM equipment WHERE id=%s", (item_id,))
    res = cursor.fetchone()
    cursor.execute("DELETE FROM equipment WHERE id=%s", (item_id,))
    conn.commit()
    cursor.close()
    conn.close()
    if res and res[0]:
        path = os.path.join(app.config["UPLOAD_FOLDER"], res[0])
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    flash("Equipment deleted.", "info")
    return redirect(url_for("index"))
@app.route("/cart")
@login_required
def view_cart():
    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id AS cart_id, e.id AS equipment_id, e.name, e.price, e.image, c.quantity
        FROM cart c JOIN equipment e ON c.equipment_id = e.id
        WHERE c.user_id = %s
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    total = sum(row["price"] * row["quantity"] for row in rows) if rows else 0
    return render_template("cart.html", rows=rows, total=total)

@app.route("/cart/add/<int:equipment_id>", methods=["POST"])
@login_required
def add_to_cart(equipment_id):
    user_id = session["user_id"]
    qty = int(request.form.get("quantity", 1))
    if qty < 1:
        qty = 1

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM cart WHERE user_id=%s AND equipment_id=%s", (user_id, equipment_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE cart SET quantity = quantity + %s WHERE id=%s", (qty, existing[0]))
    else:
        cursor.execute("INSERT INTO cart (user_id, equipment_id, quantity) VALUES (%s,%s,%s)",
                       (user_id, equipment_id, qty))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Added to cart.", "success")
    return redirect(url_for("view_cart"))

@app.route("/cart/remove/<int:cart_id>", methods=["POST"])
@login_required
def remove_from_cart(cart_id):
    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Removed from cart.", "info")
    return redirect(url_for("view_cart"))

@app.route("/cart/checkout", methods=["POST"])
@login_required
def checkout():
    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id as cart_id, c.quantity, e.id as eid, e.name, e.price, e.stock
        FROM cart c JOIN equipment e ON c.equipment_id = e.id
        WHERE c.user_id=%s
    """, (user_id,))
    rows = cursor.fetchall()
    try:
        for r in rows:
            if r["stock"] < r["quantity"]:
                raise Exception(f"Not enough stock for {r['name']}")
            new_stock = r["stock"] - r["quantity"]
            cursor.execute("UPDATE equipment SET stock=%s WHERE id=%s", (new_stock, r["eid"]))
        cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(str(e), "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("view_cart"))

    cursor.close()
    conn.close()
    flash("Checkout complete. (No payment processing in demo)", "success")
    return redirect(url_for("index"))
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"],filename)
@app.context_processor
def inject_user():
   return dict(logged_in=("user_id" in session), username=session.get("username"), is_admin=session.get("is_admin", False))
if __name__ == "__main__":
 os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
 print(app.url_map)
 app.run(debug=True, host="127.0.0.1",port=5000)