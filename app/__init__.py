from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_login import LoginManager
import os
import click

def create_app():
    # Create the main app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-wheredhego')
    
    # Force HTTPS in production only
    @app.before_request
    def force_https():
        # Only redirect to HTTPS in production (when not in debug mode and not local)
        if (not request.is_secure and 
            not app.debug and 
            not request.host.startswith('localhost') and 
            not request.host.startswith('127.0.0.1')):
            if request.headers.get('X-Forwarded-Proto') != 'https':
                return redirect(request.url.replace('http://', 'https://'), code=301)
    
    # Configure database - MySQL for production, SQLite for development
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Production MySQL database
    if os.environ.get('DATABASE_URL'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    elif os.environ.get('MYSQL_HOST'):
        # MySQL configuration from environment variables
        mysql_user = os.environ.get('MYSQL_USER', 'devgreeny')
        mysql_password = os.environ.get('MYSQL_PASSWORD', 'lebron69')
        mysql_host = os.environ.get('MYSQL_HOST', 'devgreeny.mysql.pythonanywhere-services.com')
        mysql_db = os.environ.get('MYSQL_DATABASE', 'devgreeny$default')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}'
    else:
        # Development SQLite database
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'wheredhego.db')
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database (for game scores)
    from app.starting5.models import db
    db.init_app(app)
    
    # Initialize login manager for unified auth
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to track your scores across games.'
    
    @login_manager.user_loader
    def load_user(user_id):
        # Use SQLite models for local development, MySQL for production
        if os.environ.get('USE_LOCAL_SQLITE') or not os.environ.get('MYSQL_HOST'):
            from app.auth.sqlite_models import User
        else:
            from app.auth.models import User
        return User.get_by_id(int(user_id))
    
    # Register the starting5 blueprint
    from app.starting5.routes import bp as starting5_bp
    app.register_blueprint(starting5_bp, url_prefix='/starting5')
    
    # Register the gridiron11 blueprint
    from app.gridiron11.routes import bp as gridiron11_bp
    app.register_blueprint(gridiron11_bp, url_prefix='/gridiron11')
    
    # Register the creatorpoll blueprint - use SQLite for local dev, MySQL for production
    if os.environ.get('USE_LOCAL_SQLITE') or not os.environ.get('MYSQL_HOST'):
        from app.creatorpoll.routes import bp as creatorpoll_bp
        print("🔧 Using SQLite CreatorPoll routes for local development")
    else:
        from app.creatorpoll.mysql_routes import bp as creatorpoll_bp
        print("🔧 Using MySQL CreatorPoll routes for production")
    app.register_blueprint(creatorpoll_bp, url_prefix='/creatorpoll')
    
    # Register the auth blueprint for unified authentication
    from app.auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Create database tables if they don't exist
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Database tables may already exist: {e}")

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/healthz")
    def healthz():
        return "ok"
    
    # Favicon routes - serve favicon files from the favicon directory
    @app.route('/favicon/<path:filename>')
    def favicon(filename):
        favicon_dir = os.path.join(app.root_path, '..', 'favicon')
        return send_from_directory(favicon_dir, filename)
    
    # Traditional favicon.ico route for backward compatibility
    @app.route('/favicon.ico')
    def favicon_ico():
        favicon_dir = os.path.join(app.root_path, '..', 'favicon')
        return send_from_directory(favicon_dir, 'favicon.ico')

    # Register CLI commands
    from app.tasks import register_cli_commands
    register_cli_commands(app)

    app.logger.info("Wheredhego app with Starting5 game created successfully")
    return app
