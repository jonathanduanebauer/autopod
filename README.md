# Podcast Dashboard & AI Summary Platform

A Flask-based web dashboard for managing and summarizing radio and podcast content using GPT-4. This system allows for audio uploads, text summaries, headline and keyword generation, SEO analysis, Meta ads lead scoring, and manual editorial control.

## Features

- Password-protected admin dashboard using HTTP Basic Auth
- GPT-4 powered summary, headline, and keyword generation
- Editable summaries and image uploads for each episode
- Upload interface for MP3s or text transcripts
- Lead scoring and report generation based on Meta Ads JSON data
- SEO analysis tool with scoring and suggested rewrites
- CSV export of enhanced leads
- Dynamic image and audio file rendering for web display
- Multi-show support (Newstalk Breakfast, Pat Kenny, Hard Shoulder, etc.)
- Optional reference style matching using previous summaries

## Tech Stack

- **Backend**: Python (Flask)
- **Frontend**: Jinja2, HTML, Bootstrap
- **AI**: OpenAI GPT-4 (`openai.ChatCompletion`)
- **Database**: PostgreSQL
- **Authentication**: Flask HTTP Basic Auth
- **Email**: SMTP2GO API
- **Logging**: Rotating file logging to `app.log`

## Folder Structure
/home/ftpuser/
├── autobahn/
│ ├── processing/ # Input folder for transcripts and MP3s
│ ├── completed/ # Output folder for summaries
├── flask/
│ ├── templates/
│ │ ├── index.html
│ │ ├── newstalk_breakfast.html
│ │ ├── pat_kenny.html
│ │ ├── lunchtime_live.html
│ │ └── images/ # Uploaded images for episodes


## Setup Instructions

### 1. Install Requirements

```bash
pip install flask flask_httpauth flask_cors openai psycopg2-binary


