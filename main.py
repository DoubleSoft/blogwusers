from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user, \
    AnonymousUserMixin
from forms import CreatePostForm, CreateUserForm, CreateLoginForm, CreatCommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONFIGURE TABLES
class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref=db.backref("posts"))
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref=db.backref("comments"))
    text = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    blog_posts = db.relationship("BlogPost", backref=db.backref("comments"))

#db.create_all()

def admin_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(type(current_user))
        if (isinstance(current_user, AnonymousUserMixin)):
            return abort(403)
        elif current_user.id !=1:
            return abort(401)
        else:
            return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)

@app.route('/register', methods=['POST','GET'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash("The email entered is already used, log in instead")
            return redirect(url_for("login"))
        pw_hashed = generate_password_hash(password,salt_length=8)
        new_user = User(name=name,email=email,password=pw_hashed)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form = CreateUserForm(),logged_in=current_user.is_authenticated)

@app.route('/login', methods= ['POST','GET'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        db_user = User.query.filter_by(email=email).first()
        if db_user:
            password = request.form.get('password')
            if check_password_hash(db_user.password,password):
                login_user(db_user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Wrong password, try again")
        else:
            flash("The email does not exist, please try again")
            return redirect(url_for('login'))
    return render_template("login.html", form = CreateLoginForm())

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    form = CreatCommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = requested_post.comments
    user_name ='zero'
    logged_in = False
    user = User.query.get(1)
    if current_user.is_authenticated:
        user = User.query.get(current_user.id)
        user_name = user.name
        email = user.email
        logged_in=True
    if form.validate_on_submit():
        new_comment= Comment(
            user = current_user,
            user_id = current_user.id,
            blog_posts = BlogPost.query.get(post_id),
            post_id = post_id,
            text = form.body.data)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post',post_id=post_id))
    print(user_name)
    return render_template("post.html", post=requested_post, form=form, logged_in=logged_in,
                           name=user_name,comments=comments,user=user)

@app.route("/new-post", methods=['POST','GET'])
@admin_login
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            user_id=current_user.id,
            user=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,logged_in=current_user.is_authenticated)

@app.route("/edit-post/<int:post_id>", methods=['GET','POST'])
@admin_login
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form,logged_in=current_user.is_authenticated, is_edit=True)

@app.route("/delete/<int:post_id>")
@admin_login
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    app.run(debug=True)
