import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='Applied')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verifier_comment = db.Column(db.Text, nullable=True)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300), nullable=False)
    doc_type = db.Column(db.String(100), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_db():
    with app.app_context():
        db.create_all()


def send_notification(to_email: str, subject: str, message: str):
    mail_host = os.getenv('MAIL_SERVER')
    mail_port = int(os.getenv('MAIL_PORT', '587'))
    mail_user = os.getenv('MAIL_USERNAME')
    mail_pass = os.getenv('MAIL_PASSWORD')

    if mail_host and mail_user and mail_pass:
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = mail_user
            msg['To'] = to_email
            msg.set_content(message)

            with smtplib.SMTP(mail_host, mail_port) as server:
                server.starttls()
                server.login(mail_user, mail_pass)
                server.send_message(msg)
            app.logger.info('Sent email to %s', to_email)
        except Exception as e:
            app.logger.error('Failed to send email: %s', e)
    else:
        # Fallback: print to console
        app.logger.info('Notification to %s -- %s: %s', to_email, subject, message)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/verifier')
def verifier_ui():
    return render_template('verifier.html')


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/applications', methods=['POST'])
def submit_application():
    # Accept multipart form data
    name = request.form.get('name')
    email = request.form.get('email')
    amount = request.form.get('amount', type=float)
    purpose = request.form.get('purpose')

    if not (name and email and amount):
        return jsonify({'error': 'name, email and amount are required'}), 400

    app_obj = Application(name=name, email=email, amount=amount, purpose=purpose)
    db.session.add(app_obj)
    db.session.flush()

    # Handle files
    files = request.files.getlist('documents')
    for f in files:
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1]
            unique = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
            f.save(save_path)
            doc_type = request.form.get(f'doc_type_{f.filename}', 'document')
            doc = Document(application_id=app_obj.id, filename=unique, original_filename=f.filename, doc_type=doc_type)
            db.session.add(doc)

    db.session.commit()

    # Notification
    send_notification(email, 'Application Submitted', f'Your application (ID: {app_obj.id}) was submitted and is in Applied status.')

    return jsonify({'id': app_obj.id, 'status': app_obj.status}), 201


@app.route('/api/applications', methods=['GET'])
def list_applications():
    apps = Application.query.order_by(Application.created_at.desc()).all()
    result = []
    for a in apps:
        docs = Document.query.filter_by(application_id=a.id).all()
        result.append({
            'id': a.id,
            'name': a.name,
            'email': a.email,
            'amount': a.amount,
            'purpose': a.purpose,
            'status': a.status,
            'created_at': a.created_at.isoformat(),
            'verifier_comment': a.verifier_comment,
            'documents': [
                {'id': d.id, 'filename': d.filename, 'original_filename': d.original_filename, 'doc_type': d.doc_type}
                for d in docs
            ]
        })
    return jsonify(result)


@app.route('/api/applications/<int:app_id>/verify', methods=['POST'])
def verify_application(app_id):
    data = request.json or {}
    action = data.get('action')
    comment = data.get('comment')

    app_obj = Application.query.get_or_404(app_id)

    if action == 'verify':
        app_obj.status = 'Verified'
        app_obj.verifier_comment = comment
    elif action == 'send_back':
        app_obj.status = 'Sent Back'
        app_obj.verifier_comment = comment
    else:
        return jsonify({'error': 'invalid action'}), 400

    db.session.commit()

    # Notify applicant
    send_notification(app_obj.email, f'Application {app_obj.status}', f'Your application (ID: {app_obj.id}) status changed to {app_obj.status}. Comment: {comment or ""}')

    return jsonify({'id': app_obj.id, 'status': app_obj.status})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')))
