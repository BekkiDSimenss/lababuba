from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_private = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Создаем таблицы при первом запуске
with app.app_context():
    db.create_all()
    # Создаем тестового пользователя, если его нет
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()

# Формы и маршруты
@app.route('/')
def index():
    if 'username' in session:
        # Для авторизованных пользователей показываем все посты
        posts = Post.query.order_by(Post.created_at.desc()).all()
    else:
        # Для анонимных - только публичные
        posts = Post.query.filter_by(is_private=False).order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['username'] = user.username
            flash('Вы успешно вошли в систему', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>')
def show_post(post_id):
    post = Post.query.get_or_404(post_id)
    # Проверяем, может ли пользователь видеть приватный пост
    if post.is_private and 'username' not in session:
        flash('Этот пост доступен только авторизованным пользователям', 'warning')
        return redirect(url_for('login'))
    return render_template('post.html', post=post)

@app.route('/create', methods=['GET', 'POST'])
def create_post():
    if 'username' not in session:
        flash('Для создания поста необходимо авторизоваться', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        is_private = 'is_private' in request.form
        
        user = User.query.filter_by(username=session['username']).first()
        post = Post(
            title=title,
            content=content,
            is_private=is_private,
            author=user
        )
        db.session.add(post)
        db.session.commit()
        flash('Пост успешно создан', 'success')
        return redirect(url_for('index'))
    
    return render_template('edit.html')

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'username' not in session:
        flash('Для редактирования поста необходимо авторизоваться', 'warning')
        return redirect(url_for('login'))
    
    post = Post.query.get_or_404(post_id)
    user = User.query.filter_by(username=session['username']).first()
    
    # Проверяем, что пользователь является автором поста
    if post.author != user:
        flash('Вы можете редактировать только свои посты', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.is_private = 'is_private' in request.form
        db.session.commit()
        flash('Пост успешно обновлен', 'success')
        return redirect(url_for('show_post', post_id=post.id))
    
    return render_template('edit.html', post=post)

@app.route('/delete/<int:post_id>')
def delete_post(post_id):
    if 'username' not in session:
        flash('Для удаления поста необходимо авторизоваться', 'warning')
        return redirect(url_for('login'))
    
    post = Post.query.get_or_404(post_id)
    user = User.query.filter_by(username=session['username']).first()
    
    if post.author != user:
        flash('Вы можете удалять только свои посты', 'danger')
        return redirect(url_for('index'))
    
    db.session.delete(post)
    db.session.commit()
    flash('Пост успешно удален', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)