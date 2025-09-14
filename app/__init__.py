from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os

def create_app():
    # Create the main app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-wheredhego')
    
    # Force HTTPS in production
    @app.before_request
    def force_https():
        if not request.is_secure and not app.debug:
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
    
    # Initialize database (for game scores, no auth)
    from app.starting5.models import db
    db.init_app(app)
    
    # Register the starting5 blueprint
    from app.starting5.routes import bp as starting5_bp
    app.register_blueprint(starting5_bp, url_prefix='/starting5')
    
    # Register the gridiron11 blueprint
    from app.gridiron11.routes import bp as gridiron11_bp
    app.register_blueprint(gridiron11_bp, url_prefix='/gridiron11')
    
    # Register the creatorpoll blueprint
    from app.creatorpoll.routes import bp as creatorpoll_bp
    app.register_blueprint(creatorpoll_bp, url_prefix='/creatorpoll')
    
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

    app.logger.info("Wheredhego app with Starting5 game created successfully")
    return app
