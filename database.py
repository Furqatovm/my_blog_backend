import os
from flask import Flask, jsonify, request, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from werkzeug.utils import secure_filename # Fayl nomini xavfsiz qilish uchun

app = Flask(__name__)
CORS(app)

# --- KONFIGURATSIYA ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Rasmlar saqlanadigan papka
UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Maksimal 16MB rasm

# Papka bo'lmasa yaratamiz
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)

# --- MODELS ---

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), default="Anonymous")
    post_image = db.Column(db.String(500), nullable=True) # Rasmning URL manzili saqlanadi
    category = db.Column(db.String(100), default="Yangiliklar")
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "post_image": self.post_image,
            "category": self.category,
            "date": self.date_posted.strftime("%Y-%m-%d %H:%M:%S")
        }

# Baza jadvallarini yangilash (MUHIM!)
with app.app_context():
    db.create_all()

# --- RASMLARNI SERVIS QILISH ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- API ROUTES ---

@app.route('/')
def home():
    return {"status": "online", "message": "Blog API is active"}

# === CATEGORY CRUD ===
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])

@app.route('/api/categories', methods=['POST'])
def add_category():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Kategoriya nomi kiritilmagan"}), 400
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({"error": "Bunday kategoriya mavjud"}), 400
    new_cat = Category(name=data['name'])
    db.session.add(new_cat)
    db.session.commit()
    return jsonify(new_cat.to_dict()), 201

# === POST CRUD WITH IMAGE UPLOAD ===
@app.route('/api/posts', methods=['POST'])
def create_post():
    # Frontenddan ma'lumotlar 'multipart/form-data' bo'lib keladi
    title = request.form.get('title')
    content = request.form.get('content')
    author = request.form.get('author', 'Anonymous')
    category = request.form.get('category', 'Yangiliklar')
    
    if not title or not content:
        return jsonify({"error": "Title va Content bo'lishi shart"}), 400

    image_url = None
    if 'post_image' in request.files:
        file = request.files['post_image']
        if file.filename != '':
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Rasmga to'liq URL yaratamiz
            image_url = f"{request.host_url}uploads/{filename}"

    new_post = Post(
        title=title,
        content=content,
        author=author,
        category=category,
        post_image=image_url
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify(new_post.to_dict()), 201

@app.route('/api/posts', methods=['GET'])
def get_posts():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return jsonify([p.to_dict() for p in posts])

@app.route('/api/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post o'chirildi"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)