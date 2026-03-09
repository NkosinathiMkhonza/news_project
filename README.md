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

## Notes

- The project includes design assets in [Design_Digrams/README.md](/c:/Users/DJ%20CHLORINE/Documents/news_project/Design_Digrams/README.md).
- For production, set a strong `SECRET_KEY`, turn `DEBUG` off, and configure `ALLOWED_HOSTS`.
