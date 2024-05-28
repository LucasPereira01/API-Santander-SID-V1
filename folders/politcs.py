from flask import Flask, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from db import get_db_connection
import requests

app = Flask(__name__)
