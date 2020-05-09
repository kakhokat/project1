from flask import Flask, render_template, redirect, request
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
from flask_restful import abort

from data import db_session
from data.news import News, NewsForm
from data.register import LoginForm, RegisterForm
from data.users import User
import os

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'yandexlyceum_super_secret_key'
admin = "нет"


def main():
    db_session.global_init("db/blogs.sqlite")

    @login_manager.user_loader
    def load_user(user_id):
        session = db_session.create_session()
        return session.query(User).get(user_id)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        global admin
        admin_email = ['email_admin1@yandex.ru']
        admin_password = ['password_admin1']
        form = LoginForm()
        if form.validate_on_submit():
            session = db_session.create_session()
            user = session.query(User).filter(User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                if form.email.data in admin_email and form.password.data in admin_password:
                    admin = "да"
                else:
                    admin = "нет"
                return redirect("/")
            return render_template('login.html',
                                   message="Неправильный логин или пароль",
                                   form=form)
        return render_template('login.html', title='Авторизация', form=form)
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            if form.password.data != form.password_again.data:
                return render_template('register.html', title='Register', form=form,
                                       message="Пароли не совпадают!")
            session = db_session.create_session()
            if session.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Register', form=form,
                                       message="Такой пользователь уже есть!")
            user = User(
                name=form.name.data,
                about=form.about.data,
                email=form.email.data,
                hashed_password=form.password.data,
            )
            user.set_password(form.password.data)
            session.add(user)
            session.commit()
            return redirect('/login')
        return render_template('register.html', title='Регистрация', form=form)

    @app.route("/")
    def index():
        global admin
        session = db_session.create_session()
        q = request.args.get('q')
        if q and current_user.is_authenticated:
            news = session.query(News).filter(((News.title.contains(q)) | (News.content.contains(q))) & ((News.user == current_user) | (News.is_private != True)))
        elif q:
            news = session.query(News).filter((News.title.contains(q)) | (News.content.contains(q)) & (News.is_private != True))
        elif current_user.is_authenticated:
            news = session.query(News).filter((News.user == current_user) | (News.is_private != True))
        else:
            news = session.query(News).filter(News.is_private != True)
        return render_template("index.html", news=news, admin=admin)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect("/")

    @app.route('/news', methods=['GET', 'POST'])
    @login_required
    def add_news():
        form = NewsForm()
        if form.validate_on_submit():
            session = db_session.create_session()
            news = News()
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            current_user.news.append(news)
            session.merge(current_user)
            session.commit()
            return redirect('/')
        return render_template('news.html', title='Добавление новости',
                               form=form)     

    @app.route('/news/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_news(id):
        global admin
        form = NewsForm()
        if request.method == "GET":
            session = db_session.create_session()
            if admin == "да":
                news = session.query(News).filter(News.id == id).first()
            else:
                news = session.query(News).filter(News.id == id,
                                              News.user == current_user).first()
            if news:
                form.title.data = news.title
                form.content.data = news.content
                form.is_private.data = news.is_private
            else:
                abort(404)
        if form.validate_on_submit():
            session = db_session.create_session()
            if admin == "да":
                news = session.query(News).filter(News.id == id).first()
            else:
                news = session.query(News).filter(News.id == id,
                                              News.user == current_user).first()
            if news:
                news.title = form.title.data
                news.content = form.content.data
                news.is_private = form.is_private.data
                session.commit()
                return redirect('/')
            else:
                abort(404)
        return render_template('news.html', title='Редактирование новости', form=form)

    @app.route('/news_delete/<int:id>', methods=['GET', 'POST'])
    @login_required
    def news_delete(id):
        session = db_session.create_session()
        global admin
        if admin == "да":
            news = session.query(News).filter(News.id == id).first()
        else:
            news = session.query(News).filter(News.id == id,
                                            News.user == current_user).first()
        if news:
            session.delete(news)
            session.commit()
        else:
            abort(404)
        return redirect('/')
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    

if __name__ == '__main__':
    main()
