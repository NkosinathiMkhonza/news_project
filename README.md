# News Project

A Django news publishing platform with a clear editorial workflow:

- journalists create and submit articles
- editors create publishers and approve, reject, edit, or delete articles
- readers browse published content, comment, and subscribe to publishers or journalists
- subscribed readers receive in-app notifications when new articles are published

## Features

- Role-based access with `Reader`, `Journalist`, and `Editor`
- Separate `Publisher` model managed by editors
- Draft -> pending -> published/rejected article workflow
- Reader subscriptions to publishers and journalists
- In-app notifications created by Django signals on publication
- Commenting on published articles
- Password reset flow
- Django REST Framework endpoints for articles, categories, publishers, comments, and subscriptions

## Requirements

- Python 3.13+
- Django 4.2+
- Django REST Framework
- Pillow
- python-dotenv
- mysqlclient for MariaDB/MySQL usage
- black and flake8 for formatting and linting

Install dependencies:

```bash
pip install -r requirements.txt
```

Format and lint before resubmitting:

```bash
black .
flake8 news news_project manage.py
```

## Environment Setup

Copy the example file and adjust it for your machine:

```bash
copy .env.example .env
```

The project loads `.env` automatically with `python-dotenv`.

### Database selection

The settings file defines both SQLite and MySQL configurations. Use
`ACTIVE_DATABASE` to choose which one Django uses as `default`.

Example SQLite development setup:

```env
DEBUG=True
SECRET_KEY=your-secret-key
ACTIVE_DATABASE=sqlite
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Example MySQL or MariaDB setup:

```env
DEBUG=True
SECRET_KEY=your-secret-key
ACTIVE_DATABASE=mysql
DB_ENGINE=django.db.backends.mysql
DB_NAME=news_db
DB_USER=news_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=3306
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Because `default` is derived from `ACTIVE_DATABASE`, migrations and the
running server use the same database configuration.

Password reset emails use Django's console email backend by default, so the
reset link is visible in the terminal during local development.

## Setup

Run migrations:

```bash
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

Start the server:

```bash
python manage.py runserver
```

## Roles and Workflow

### Reader

- reads published articles
- comments on published articles
- subscribes to publishers and journalists
- receives notifications when subscribed content is published

### Journalist

- creates draft articles
- selects an existing publisher created by an editor
- submits articles for editorial review

### Editor

- creates publishers
- reviews pending articles
- approves or rejects submissions
- edits or deletes articles when required
- manages published and rejected articles from the editor dashboard

## Main Models

- `UserProfile`: stores the application role for each user
- `Publisher`: separate organization model created by editors
- `Article`: author, publisher, category, workflow status, review fields
- `Subscription`: reader subscription to exactly one target, either a publisher or a journalist
- `Notification`: in-app alert created when a subscribed article is published
- `Comment`: comments on published articles
- `ResetToken`: password reset support

## Notifications

The app uses a Django `post_save` signal on `Article`. When an article is
published, the signal finds readers subscribed to the article's publisher
or author and creates a single in-app notification per reader.

## API Endpoints

- `/api/articles/`
- `/api/articles/<id>/`
- `/api/categories/`
- `/api/publishers/`
- `/api/comments/`
- `/api/subscriptions/`

## Tests

Run the test suite with:

```bash
python manage.py test news
```

## Migrations

After model changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Running with a Virtual Environment (venv)

1. **Create a virtual environment** in the project root:
   ```bash
   python -m venv venv
   ```

2. **Activate** the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** – copy the example and edit:
   ```bash
   cp .env.example .env
   # Edit .env and set SECRET_KEY, ACTIVE_DATABASE, etc.
   ```
   > **Note:** Never commit your `.env` file. It is already excluded by `.gitignore`.

5. **Apply migrations and start the server**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser  # optional
   python manage.py runserver
   ```

## Running with Docker

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running.

### Steps

1. **Create your `.env` file** from the example:
   ```bash
   cp .env.example .env
   ```
   Set at minimum:
   ```env
   SECRET_KEY=your-strong-secret-key
   DEBUG=True
   ACTIVE_DATABASE=sqlite
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

2. **Build the Docker image**:
   ```bash
   docker build -t news_project .
   ```

3. **Run the container**:
   ```bash
   docker run --env-file .env -p 8000:8000 news_project
   ```

   Or, using Docker Compose:
   ```bash
   docker-compose up --build
   ```

4. Visit `http://localhost:8000` in your browser.

## Documentation

User-friendly HTML documentation generated with Sphinx is stored in [`docs/_build/html/`](docs/_build/html/index.html).  
To rebuild the docs locally:

```bash
cd docs
make html
```

## Notes

- The project includes design assets in [`Design_Digrams/README.md`](Design_Digrams/README.md).
- For production, set a strong `SECRET_KEY`, turn `DEBUG` off, and configure `ALLOWED_HOSTS`.
