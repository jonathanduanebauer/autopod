import os
import psycopg2
import datetime
import openai
import json
import csv
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, make_response, send_file
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS
from logging.handlers import RotatingFileHandler
import logging
from podcast_summary_script import generate_summary, create_headline, extract_keywords, connect_db, list_transcriptions, read_transcription_by_name

# Load OpenAI API Key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# Flask App Initialization
app = Flask(__name__)
auth = HTTPBasicAuth()
CORS(app)

# Logging Setup
handler = RotatingFileHandler('app.log', maxBytes=100000, backupCount=3)
logging.basicConfig(level=logging.WARNING, handlers=[handler])

# Auth Users – Load from env or config (do not hardcode passwords in production)
users = {
    os.getenv("FLASK_ADMIN_USER", "admin"): os.getenv("FLASK_ADMIN_PASS", "changeme123")
}

@auth.verify_password
def verify_password(username, password):
    return username in users and users[username] == password

def get_show_data(show_name):
    conn = connect_db()
    cur = conn.cursor()
    query = """
        SELECT filename, headline, summary, keywords, mp3_filename, created_at, image_filename
        FROM summaries 
        WHERE filename LIKE %s 
        ORDER BY created_at DESC
    """
    try:
        cur.execute(query, (f"%{show_name}%",))
        rows = cur.fetchall()
        formatted_rows = []
        for row in rows:
            filename, headline, summary, keywords, mp3_filename, created_at, image_filename = row
            formatted_date = created_at.strftime('%Y-%m-%d %H:%M:%S') if isinstance(created_at, datetime.datetime) else str(created_at)
            formatted_rows.append((filename, headline, summary, keywords, mp3_filename, formatted_date, image_filename))
    except psycopg2.Error as e:
        logging.error(f"Database error in get_show_data: {e}")
        formatted_rows = []
    finally:
        cur.close()
        conn.close()
    return formatted_rows

@app.route('/')
@auth.login_required
def index():
    return render_template('index.html')

@app.route('/newstalk_breakfast')
@auth.login_required
def newstalk_breakfast():
    rows = get_show_data("Newstalk_Breakfast")
    return render_template('newstalk_breakfast.html', rows=rows)

@app.route('/pat_kenny')
@auth.login_required
def pat_kenny():
    rows = get_show_data("Pat_Kenny")
    return render_template('pat_kenny.html', rows=rows)

@app.route('/the_hard_shoulder')
@auth.login_required
def the_hard_shoulder():
    rows = get_show_data("Hard_Shoulder")
    return render_template('the_hard_shoulder.html', rows=rows)

@app.route('/lunchtime_live')
@auth.login_required
def lunchtime_live():
    rows = get_show_data("Lunchtime_Live")
    return render_template('lunchtime_live.html', rows=rows)

@app.route('/edit/<filename>', methods=['GET', 'POST'])
@auth.login_required
def edit(filename):
    conn = connect_db()
    cur = conn.cursor()
    if request.method == 'POST':
        headline = request.form['headline']
        summary = request.form['summary']
        keywords = request.form['keywords']
        image_filename = None

        if 'image' in request.files and request.files['image'].filename:
            image = request.files['image']
            if image and image.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                if len(image.read()) <= 5 * 1024 * 1024:
                    image.seek(0)
                    image_filename = secure_filename(f"{filename}_{image.filename}")
                    image.save(os.path.join('/home/ftpuser/flask/templates/images', image_filename))
                else:
                    return "Image file too large (max 5MB)", 400

        cur.execute("""
            UPDATE summaries 
            SET headline = %s, summary = %s, keywords = %s, image_filename = %s
            WHERE filename = %s
        """, (headline, summary, keywords, image_filename, filename))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for(request.form.get('return_page', 'index')))
    else:
        cur.execute("""
            SELECT headline, summary, keywords, image_filename 
            FROM summaries 
            WHERE filename = %s
        """, (filename,))
        item = cur.fetchone()
        cur.close()
        conn.close()
        return render_template('edit.html', 
            filename=filename, 
            headline=item[0], 
            summary=item[1], 
            keywords=item[2], 
            image_filename=item[3], 
            return_page=request.args.get('return_page', 'index')
        )

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory('/home/ftpuser/flask/templates/images', filename)

@app.route('/mp3/<filename>')
def serve_mp3(filename):
    return send_from_directory('/home/ftpuser/autobahn/processing', filename)

@app.route('/run_scripts')
@auth.login_required
def run_scripts():
    return render_template('run_scripts.html')

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    file = request.files['file']
    filename = request.form['filename']
    file.save(os.path.join('/home/ftpuser/autobahn/processing', filename))
    return jsonify({'success': True, 'message': f'Audio file {filename} saved successfully'})

@app.route('/audiomass')
@auth.login_required
def audiomass():
    filename = request.args.get('filename', None)
    return render_template('audiomass.html', filename=filename) 

@app.route('/story_style', methods=['GET', 'POST'])
@auth.login_required
def story_style():
    output_text = None
    if request.method == 'POST':
        input_text = request.form['inputText']
        style = request.form['style']
        output_text = style_text(input_text, style)
    return render_template('story_style.html', outputText=output_text)

def style_text(text, style):
    return f"Styled text in {style}: {text}"

@app.route('/generate_summary', methods=['GET', 'POST'])
@auth.login_required
def generate_summary_page():
    files = list_transcriptions(sort_by_date=True)
    transcript = ""
    headline = ""
    summary = ""
    keywords = []
    selected_file = ""

    if request.method == 'POST':
        selected_file = request.form.get('file_select', '')
        transcript = request.form.get('transcript', '')

        if selected_file and not transcript:
            transcript = read_transcription_by_name(selected_file)

        if 'generate' in request.form and transcript:
            db_connection = connect_db()
            summary = generate_summary(transcript, db_connection)
            headline = create_headline(summary)
            keywords = extract_keywords(transcript, summary)
            db_connection.close()

        elif 'download' in request.form and transcript:
            filename = "generated_summary.txt"
            filepath = os.path.join("/tmp", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Headline:\n{headline}\n\n")
                f.write(f"Summary:\n{summary}\n\n")
                f.write(f"Keywords:\n{', '.join(keywords)}\n")
            return send_file(filepath, as_attachment=True)

    return render_template(
        'generate_summary.html',
        files=files,
        selected_file=selected_file,
        transcript=transcript,
        headline=headline,
        summary=summary,
        keywords=", ".join(keywords)
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
