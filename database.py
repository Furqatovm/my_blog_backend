import os
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
CORS(app)

# --- KONFIGURATSIYA ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 🔐 Xavfsizlik muhiti (Environment)
app.config['JWT_SECRET_KEY'] = 'sizning_juda_maxfiy_kalitingiz_12345' 
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

# Rasmlar uchun joy
UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- MODELLAR ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user") # 'admin' yoki 'user'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))
    post_image = db.Column(db.String(500))
    category = db.Column(db.String(100))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "content": self.content,
            "author": self.author, "post_image": self.post_image,
            "category": self.category, "date": self.date_posted.strftime("%Y-%m-%d %H:%M:%S")
        }

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}

class Newsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

# Bazani yaratish
with app.app_context():
    db.create_all()

# --- AUTH YO'LLARI ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Ma'lumotlar to'liq emas"}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email band"}), 400
    
    hashed_pw = generate_password_hash(data['password'])
    user_role = "admin" if User.query.count() == 0 else "user"
    
    new_user = User(username=data.get('username', 'User'), email=data['email'], password=hashed_pw, role=user_role)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": f"Ro'yxatdan o'tdingiz. Rolingiz: {user_role}"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if user and check_password_hash(user.password, data['password']):
        token = create_access_token(identity={'id': user.id, 'role': user.role})
        return jsonify({"token": token, "role": user.role, "username": user.username}), 200
    return jsonify({"error": "Login yoki parol xato"}), 401

# --- CATEGORY CRUD (ADMIN PROTECTED) ---

@app.route('/api/categories', methods=['POST'])
@jwt_required()
def add_category():
    identity = get_jwt_identity()
    if identity['role'] != 'admin':
        return jsonify({"error": "Faqat admin ruxsati bor"}), 403
    
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Nom kerak"}), 400
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({"error": "Bunday kategoriya bor"}), 400

    new_cat = Category(name=data['name'])
    db.session.add(new_cat)
    db.session.commit()
    return jsonify(new_cat.to_dict()), 201

@app.route('/api/categories/<int:id>', methods=['PUT'])
@jwt_required()
def update_category(id):
    identity = get_jwt_identity()
    if identity['role'] != 'admin':
        return jsonify({"error": "Faqat admin ruxsati bor"}), 403
    
    cat = Category.query.get_or_404(id)
    data = request.get_json()
    if 'name' in data:
        cat.name = data['name']
        db.session.commit()
    return jsonify(cat.to_dict())

@app.route('/api/categories/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_category(id):
    identity = get_jwt_identity()
    if identity['role'] != 'admin':
        return jsonify({"error": "Faqat admin ruxsati bor"}), 403
    
    cat = Category.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"message": "Kategoriya o'chirildi"})

# --- POST CRUD (ADMIN PROTECTED) ---

@app.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    identity = get_jwt_identity()
    if identity['role'] != 'admin':
        return jsonify({"error": "Faqat admin post qo'sha oladi"}), 403

    title = request.form.get('title')
    content = request.form.get('content')
    category = request.form.get('category')
    
    image_url = None
    if 'post_image' in request.files:
        file = request.files['post_image']
        if file.filename != '':
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"{request.host_url}uploads/{filename}"

    new_post = Post(title=title, content=content, category=category, post_image=image_url, author=identity['id'])
    db.session.add(new_post)
    db.session.commit()
    return jsonify(new_post.to_dict()), 201

@app.route('/api/posts/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_post(id):
    identity = get_jwt_identity()
    if identity['role'] != 'admin':
        return jsonify({"error": "Faqat admin o'chira oladi"}), 403
    
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post o'chirildi"})

# --- PUBLIC ROUTES ---

@app.route('/api/posts', methods=['GET'])
def get_posts():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return jsonify([p.to_dict() for p in posts])

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"error": "Email kerak"}), 400
    if Newsletter.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Siz allaqachon obuna bo'lgansiz"}), 200
    new_sub = Newsletter(email=data['email'])
    db.session.add(new_sub)
    db.session.commit()
    return jsonify({"message": "Muvaffaqiyatli obuna bo'lindi"}), 201

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)