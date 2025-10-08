from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
app = Flask("Krida")
app.secret_key = os.urandom(24)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",          
    "password": "032312",  
    "database": "Krida"
}
