from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import datetime
import boto3
import os
import random
import json
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# AWS config to get s3 bucket
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')

# S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)




app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
app.config['SECRET_KEY'] = 'secretkeyiknowitsunsecure'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tiktok_clone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
CORS(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    gender_preference = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_guest = db.Column(db.Boolean, default=False)
    
    user_tags = db.relationship('UserTag', backref='user', lazy=True, cascade='all, delete-orphan')
    media_posts = db.relationship('Media', backref='creator', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True, cascade='all, delete-orphan')
    saves = db.relationship('Save', backref='user', lazy=True, cascade='all, delete-orphan')
    follows = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy=True)
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True, cascade='all, delete-orphan')

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(30))
    is_default = db.Column(db.Boolean, default=False)
    
    user_tags = db.relationship('UserTag', backref='tag', lazy=True)
    media_tags = db.relationship('MediaTag', backref='tag', lazy=True)

class UserTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    interest_level = db.Column(db.Float, default=1.0)
    tag_type = db.Column(db.String(20), default='selected')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    media_type = db.Column(db.String(20))
    aws_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500))
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    duration = db.Column(db.Integer)
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    media_tags = db.relationship('MediaTag', backref='media', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='media', lazy=True, cascade='all, delete-orphan')
    saves = db.relationship('Save', backref='media', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='media', lazy=True, cascade='all, delete-orphan')

class MediaTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Save(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    gender_preference = data.get('gender_preference')
    selected_tags = data.get('selected_tags', [])
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, email=email, password_hash=password_hash, 
                gender_preference=gender_preference)
    db.session.add(user)
    db.session.commit()
    
    for tag_id in selected_tags:
        user_tag = UserTag(user_id=user.id, tag_id=tag_id, interest_level=1.0, tag_type='selected')
        db.session.add(user_tag)
    
    db.session.commit()
    session['user_id'] = user.id
    return jsonify({'success': True, 'user_id': user.id})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return jsonify({'success': True, 'user_id': user.id})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/guest_login', methods=['POST'])
def guest_login():
    guest_user = User(username=f"guest_{random.randint(1000, 9999)}", 
                     email=f"guest_{random.randint(1000, 9999)}@temp.com",
                     is_guest=True)
    db.session.add(guest_user)
    db.session.commit()
    
    default_tags = Tag.query.filter_by(is_default=True).all()
    for tag in default_tags:
        user_tag = UserTag(user_id=guest_user.id, tag_id=tag.id, 
                          interest_level=0.5, tag_type='algorithm')
        db.session.add(user_tag)
    
    db.session.commit()
    session['user_id'] = guest_user.id
    return jsonify({'success': True, 'user_id': guest_user.id, 'is_guest': True})

@app.route('/feed/<feed_type>')
def get_feed(feed_type):
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if feed_type == 'foryou':
        media_items = get_personalized_feed(user, page, per_page)
    elif feed_type == 'explore':
        media_items = get_explore_feed(user, page, per_page)
    else:
        return jsonify({'error': 'Invalid feed type'}), 400
    
    return jsonify({'media': media_items})

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'wav', 'pdf', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_media', methods=['POST'])
def upload_media():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Upload to S3
        s3_client.upload_fileobj(
            file,
            AWS_S3_BUCKET,
            unique_filename,
            ExtraArgs={'ACL': 'public-read'}
        )
        
        # Generate URL
        file_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        
        return jsonify({
            'success': True,
            'url': file_url,
            'filename': unique_filename
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_personalized_feed(user, page, per_page):
    user_tags = UserTag.query.filter_by(user_id=user.id).all()
    tag_weights = {ut.tag_id: ut.interest_level for ut in user_tags}
    
    if not tag_weights:
        return get_random_media(page, per_page)
    
    media_query = db.session.query(Media).join(MediaTag).filter(
        MediaTag.tag_id.in_(tag_weights.keys())
    ).order_by(Media.created_at.desc())
    
    media_items = media_query.paginate(page=page, per_page=per_page, error_out=False).items
    return format_media_response(media_items, user.id)

def get_explore_feed(user, page, per_page):
    media_query = Media.query.order_by(Media.view_count.desc(), Media.created_at.desc())
    media_items = media_query.paginate(page=page, per_page=per_page, error_out=False).items
    return format_media_response(media_items, user.id)

def get_random_media(page, per_page):
    media_query = Media.query.order_by(db.func.random())
    media_items = media_query.paginate(page=page, per_page=per_page, error_out=False).items
    return format_media_response(media_items, None)

def format_media_response(media_items, user_id=None):
    result = []
    for media in media_items:
        media_data = {
            'id': media.id,
            'title': media.title,
            'description': media.description,
            'media_type': media.media_type,
            'aws_url': media.aws_url,
            'thumbnail_url': media.thumbnail_url,
            'creator': media.creator.username,
            'creator_id': media.creator_id,
            'duration': media.duration,
            'view_count': media.view_count,
            'like_count': media.like_count,
            'comment_count': media.comment_count,
            'created_at': media.created_at.isoformat(),
            'tags': [{'id': mt.tag.id, 'name': mt.tag.name} for mt in media.media_tags],
            'is_liked': False,
            'is_saved': False,
            'is_following': False
        }
        
        if user_id:
            media_data['is_liked'] = Like.query.filter_by(user_id=user_id, media_id=media.id).first() is not None
            media_data['is_saved'] = Save.query.filter_by(user_id=user_id, media_id=media.id).first() is not None
            media_data['is_following'] = Follow.query.filter_by(follower_id=user_id, followed_id=media.creator_id).first() is not None
        
        result.append(media_data)
    
    return result

@app.route('/like/<int:media_id>', methods=['POST'])
def toggle_like(media_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    existing_like = Like.query.filter_by(user_id=user_id, media_id=media_id).first()
    media = Media.query.get(media_id)
    
    if existing_like:
        db.session.delete(existing_like)
        media.like_count = max(0, media.like_count - 1)
        liked = False
    else:
        new_like = Like(user_id=user_id, media_id=media_id)
        db.session.add(new_like)
        media.like_count += 1
        liked = True
    
    db.session.commit()
    return jsonify({'liked': liked, 'like_count': media.like_count})

@app.route('/save/<int:media_id>', methods=['POST'])
def toggle_save(media_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    existing_save = Save.query.filter_by(user_id=user_id, media_id=media_id).first()
    
    if existing_save:
        db.session.delete(existing_save)
        saved = False
    else:
        new_save = Save(user_id=user_id, media_id=media_id)
        db.session.add(new_save)
        saved = True
    
    db.session.commit()
    return jsonify({'saved': saved})

@app.route('/follow/<int:user_id>', methods=['POST'])
def toggle_follow(user_id):
    follower_id = session.get('user_id')
    if not follower_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    if follower_id == user_id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    
    existing_follow = Follow.query.filter_by(follower_id=follower_id, followed_id=user_id).first()
    
    if existing_follow:
        db.session.delete(existing_follow)
        following = False
    else:
        new_follow = Follow(follower_id=follower_id, followed_id=user_id)
        db.session.add(new_follow)
        following = True
    
    db.session.commit()
    return jsonify({'following': following})

@app.route('/comment/<int:media_id>', methods=['POST'])
def add_comment(media_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Comment cannot be empty'}), 400
    
    comment = Comment(user_id=user_id, media_id=media_id, content=content)
    db.session.add(comment)
    
    media = Media.query.get(media_id)
    media.comment_count += 1
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/comments/<int:media_id>')
def get_comments(media_id):
    comments = Comment.query.filter_by(media_id=media_id).order_by(Comment.created_at.desc()).all()
    return jsonify({
        'comments': [
            {
                'id': c.id,
                'username': c.user.username,
                'content': c.content,
                'created_at': c.created_at.isoformat()
            } for c in comments
        ]
    })

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': []})
    
    tags = Tag.query.filter(Tag.name.contains(query)).all()
    media_results = []
    
    for tag in tags:
        tag_media = db.session.query(Media).join(MediaTag).filter(
            MediaTag.tag_id == tag.id
        ).order_by(Media.view_count.desc()).limit(5).all()
        
        for media in tag_media:
            media_results.append({
                'id': media.id,
                'title': media.title,
                'thumbnail_url': media.thumbnail_url,
                'view_count': media.view_count,
                'creator': media.creator.username
            })
    
    return jsonify({'results': media_results})

@app.route('/profile')
def get_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get(user_id)
    user_tags = UserTag.query.filter_by(user_id=user_id).all()
    
    selected_tags = []
    algorithm_tags = []
    
    for ut in user_tags:
        tag_data = {
            'id': ut.tag.id,
            'name': ut.tag.name,
            'interest_level': ut.interest_level
        }
        
        if ut.tag_type == 'selected':
            selected_tags.append(tag_data)
        else:
            algorithm_tags.append(tag_data)
    
    return jsonify({
        'username': user.username,
        'selected_tags': selected_tags,
        'algorithm_tags': algorithm_tags,
        'is_guest': user.is_guest
    })

@app.route('/tags')
def get_all_tags():
    tags = Tag.query.all()
    return jsonify({
        'tags': [{'id': t.id, 'name': t.name, 'category': t.category} for t in tags]
    })

@app.route('/update_tag_interest', methods=['POST'])
def update_tag_interest():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    tag_id = data.get('tag_id')
    interest_level = data.get('interest_level')
    action = data.get('action')
    
    user_tag = UserTag.query.filter_by(user_id=user_id, tag_id=tag_id).first()
    
    if action == 'delete':
        if user_tag:
            db.session.delete(user_tag)
    elif action == 'ignore':
        if user_tag:
            db.session.delete(user_tag)
    elif action == 'keep':
        if user_tag:
            user_tag.interest_level = 0.3
            user_tag.tag_type = 'algorithm_weak'
    elif action == 'promote':
        if user_tag:
            user_tag.tag_type = 'selected'
            user_tag.interest_level = 1.0
        else:
            user_tag = UserTag(user_id=user_id, tag_id=tag_id, 
                              interest_level=1.0, tag_type='selected')
            db.session.add(user_tag)
    
    db.session.commit()
    return jsonify({'success': True})

def init_default_tags():
    default_tags = [
        'Amateurs','Anal','Anime','Asian', 'Bareback','BBW','BBM', 'BDSM', 'Big Cock',
       'Big Tits', 'College', 
        'Cumshot', 'Double Penetration', 'Exhibition', 
        'Facefuck', 'Gilf', 'Gagging', 'Gaping', 
        'Hijab', 'Inked', 'Japanese', 'Kinky', 'Lesbian', 'MILF','Missionary', 'Natural',
        'Oral', 'Pegging', 'Reverse Cowgirl', 'Stepsis','Threesome'
    ]
    
    for tag_name in default_tags:
        if not Tag.query.filter_by(name=tag_name).first():
            tag = Tag(name=tag_name, is_default=True)
            db.session.add(tag)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_default_tags()
    app.run(host='0.0.0.0', port=5000, debug=True)