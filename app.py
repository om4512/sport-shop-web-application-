from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import mysql.connector.errors as mysql_errors
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
import os
app = Flask("Krida")
app.secret_key = os.urandom(24)
UPLOAD_FOLDER ='static/uploads'
app.config['UPLOAD_FOLDER']= UPLOAD_FOLDER
db = mysql.connector.connect(
   host="localhost",
   user="root",
   password="032312",
   database="Krida",
   auth_plugin='mysql_native_password'
)
def get_connection():
   return mysql.connector.connect(db)
def login_required(f):
   @wraps(f)
   def wrapped(*args, **kwargs):
        if 'user_id' not in session:
           flash("Login required","Warning")
           return redirect(url_for("login"))
        return f(*args, **kwargs)
   return wrapped

@app.route("/register",methods=["GET","POST"])
def register():
   if request.method == "POST":
      username= request.form["Username"].strip()
      email=request.form["Email"].strip()
      password=request.form["Password"].strip()
      pw_hash=generate_password_hash(password)
      db=get_connection()
      cursor = db.cursor()
      cursor.execute("INSERT INTO users (username,email,password_hash)VALUES (%s, %s,%s)", (username,email,pw_hash))
      db.commit()
      db.close()
      flash("Registered succesfully, Please login","Success")
      return redirect(url_for("login"))
   return render_template("register.html")
@app.route("/login", methods=["GET","POST"])
def login():
   if request.method== "POST":
      username = request.form["Username"]
      password= request.form["Password"]
      db = get_connection()
      cursor= db.cursor(dictionary=True)
      cursor.execute("Select * FROM users WHERE username=%s",(username,))
      user=cursor.fetchone()
      db.close()
      if user and check_password_hash(user["password_hash"],password):
          session["user_id"]= user["id"]
          session["username"]=user["username"]
          session["is_admin"]= bool(user["is_admin"])
          flash("Log in Successful","Success")
          return redirect(url_for("index"))
      else:
         flash("invalid Credentials","Danger")
         return render_template("login.html")
   return render_template("login.html")

@app.route("/logout")
def logout():
   session.clear()
   flash("Logged out successfully.","Success")
   return redirect(url_for("index"))
def admin_required(f):
   @wraps(f)
   def decorated(*args, **kwargs):
      if not session.get("is_admin"):
         flash("Admin access required.", "danger")
         return redirect(url_for("index"))
      return f(*args, **kwargs)
   return decorated
@app.route("/")
def index():
   db=get_connection()
   cursor= db.cursor(dictionary =True)
   cursor.execute("SELECT * FROM equipment ORDER BY created_at DESC")
   items = cursor.fetchall()
   db.close()
   return render_template("index.html",items=items)
@app.route("/equipment/<int:item_id>")
def equipment_detail(item_id):
   db = get_connection()
   cursor = db.cursor(dictionary =True)
   cursor.execute("SELECT * FROM equipment WHERE id=%s",(item_id))
   item = cursor.fetchone()
   db.close()
   return render_template("equipment-detail.html", item=item)
@app.route("/add", methods=["GET","POST"])
@admin_required
def add_equipment():
   if request.method == "POST":
      name =request.form["Name"]
      category = request.form["Category"]
      description = request.form["Description"]
      price = request.form["Price"]
      stock = request.form["Stock"]
      image_file = request.files["Image"]
      filename = None
      if image_file and image_file.filename!="":
         filename = secure_filename(image_file.filename)
         image_path = os.path.join(app.config["UPLOAD_FOLDER"],filename)
         image_file.save(image_path)
      db = get_connection()
      cursor = db.cursor()
      cursor.execute("INSERT INTO equipment (name, category, description, price, stock) VALUES (%s,%s,%s, %s,%s)",(name,category, description , price, stock))
      db.commit()
      db.close()
      flash("Equipment Added Successfully","Success")
      return redirect(url_for("index"))
   return render_template("add_product.html")
@app.route("/updatwe/<int:item_id>", methods = ["GET","POST"])
@admin_required
def update_equipment(id):
   db = get_connection()
   cursor = db.cursor(dictionary = True)
   if request.method == "POST":
      name = request.form["Name"]
      category = request.form["Category"]
      description = request.form["Description"]
      price = request.form["Price"]
      stock = request.form["Stock"]
      image_file = request.files["Image"]
      filename = None
      if image_file and image_file.filename!="":
         filename = secure_filename(image_file.filename)
         image_path = os.path.join(app.config["UPLOAD_FOLDER"],filename)
         image_file.save(image_path)
      cursor.execute("UPDATE equipment SET name=%s,category=%s, description=%s, price=%s, stock=%s WHERE id=%s",(name, category, description, price, stock,id))
      db.commit()
      db.close()
      flash("Updateed Successfully","Success")
      return redirect(url_for("index"))
   cursor.execute("SELECT * FROM equipment WHERE id=%s",(id,))
   item = cursor.fetchone()
   db.close()
   return render_template("update_equipment.html", item=item)
@app.route("/delete/<int:item_id>")
@admin_required
def delete_equipment(id):
   db = get_connection()
   cursor = db.cursor()
   cursor.execute("DELETE FROM equipment WHERE id+%s",(id,))
   db.commit()
   db.close()
   flash("DELETED SUCCESSFULLY.","INFO")
   return redirect(url_for("index"))
@app.route("/cart")
@login_required
def view_cart():
   user_id = session["user_id"]
   db = get_connection()
   cursor = db.cursor(dictionary=True)
   cursor.execute("""SELECT c.id, c.quantity, e.name, e.price FROM cart c JOIN equipment e ON c.equipment_id =e.d WHERE c.user_id=%s""", (user_id,))
   rows = cursor.fetchall()
   db.close()
   total = sum(r['Price']* r["quantity"] for r in rows)
   return render_template("cart.html", rows=rows, total=total)
@app.route("/cart/add/<int:item_id>", methods=["POST"])
@login_required
def add_to_cart(item_id):
  qty = int(request.form.get("Quantity",1))
  user_id = session["user_id"]
  db = get_connection()
  cursor = db.cursor()
  cursor.execute("INSERT INTO cart (user_id, equipment_id, quantity) VALUES (%s, %s, %s)", (user_id, item_id, qty))
  db.commit()
  db.close()
  flash("Item added to cart","Success")
  return redirect(url_for("view_cart"))
@app.route("/cart/remove/<int:cart_id>")
def remove_from_cart(cart_id):
   db = get_connection()
   cursor= db.cursor()
   cursor.execute("DELETE FROM cart WHERE id=%s",(cart_id,))
   db.commit()
   db.close()
   return redirect(url_for("view_cart"))
if __name__== "__main__":
 if not os.path.exists(UPLOAD_FOLDER):
   os.markedirs(UPLOAD_FOLDER)
app.run(debug=True)