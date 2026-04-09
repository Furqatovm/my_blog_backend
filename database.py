import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)

# Barcha domenlardan so'rovlarni qabul qilish (CORS xatosini oldini oladi)
CORS(app)

# 1. Database Configuration (SQLite)
# Renderda SQLite fayli aniq yo'lda bo'lishi uchun 'basedir' ishlatamiz
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. Blog Post Model
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), default="Anonymous")
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Ma'lumotni JSON formatiga o'girish uchun yordamchi funksiya"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "date": self.date_posted.strftime("%Y-%m-%d %H:%M:%S")
        }

# 3. Database-ni yaratish
with app.app_context():
    db.create_all()

# --- API ROUTES ---

@app.route('/')
def home():
    return {"status": "success", "message": "Backend server muvaffaqiyatli ishlayapti!"}

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Barcha postlarni olish"""
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return jsonify([post.to_dict() for post in posts])

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_single_post(post_id):
    """Bitta postni ID orqali olish"""
    post = Post.query.get_or_404(post_id)
    return jsonify(post.to_dict())

@app.route('/api/posts', methods=['POST'])
def create_post():
    """Yangi post yaratish"""
    data = request.get_json()
    
    if not data or 'title' not in data or 'content' not in data:
        return jsonify({"error": "Sarlavha (title) yoki mazmun (content) kiritilmagan"}), 400
        
    new_post = Post(
        title=data['title'],
        content=data['content'],
        author=data.get('author', 'Anonymous')
    )
    
    db.session.add(new_post)
    db.session.commit()
    
    return jsonify({"message": "Post muvaffaqiyatli yaratildi!", "post": new_post.to_dict()}), 201

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """Postni o'chirish"""
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post o'chirildi!"})

# --- SERVERNI ISHGA TUSHIRISH ---

if __name__ == '__main__':
    # Render muhiti uchun portni aniqlash
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' bo'lishi shart, aks holda server tashqariga ko'rinmaydi
    app.run(host='0.0.0.0', port=port)