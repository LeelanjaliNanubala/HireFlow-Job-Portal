# HireFlow - Job Portal & Recruitment Management Platform

Django 6.1 + Django REST Framework + MySQL 8.4 + Bootstrap 5 + Chart.js. Three roles: Candidate, Recruiter, Administrator.

> **Honest status:** this code was written without being able to run Django in the environment that produced it
> (no Django installed, no internet). It has passed Python syntax checks and a static check of template tags and URL
> names, but it has **not** been executed and **no automated test has been run yet**. Follow "First run checklist"
> below and send me the first error you see (the full traceback); we will fix it together.

## 1. Requirements
Python 3.13, MySQL 8.4 (and MySQL Workbench), Git, VS Code. Internet is needed in the browser for the Bootstrap, icons
and Chart.js CDN files (jsdelivr.net).

## 2. Folder structure
```
HireFlow/
  manage.py  requirements.txt  .env.example  .gitignore  README.md
  config/            settings.py, urls.py, api_urls.py, wsgi.py, asgi.py
  apps/
    common/          shared helpers: Bootstrap form mixin, template tags, API error handler, test factories
    accounts/        custom User, login/registration/password reset, audit log, seed_demo command
    candidates/      profile, education, experience, skills, private resumes, saved jobs
    companies/       Company, RecruiterProfile, public company page
    jobs/            jobs, search, recruiter job management, home page
    applications/    apply, status workflow, history
    interviews/      scheduling, feedback
    notifications/   in-app notifications
    analytics/       recruiter dashboard + administrator dashboard
  templates/         base.html + public/ accounts/ candidate/ recruiter/ admin_dashboard/ partials/ notifications/
  static/            css/hireflow.css, js/main.js, js/charts.js
  media_private/     resumes (private, never served by URL)
  docs/              DATABASE_SCHEMA.md  API_ENDPOINTS.md  USER_GUIDE.md
  tests/             test_api.py (app tests live in apps/*/tests.py)
```
Differences from the requested structure (and why): added `apps/common` for code shared by several apps;
API views live in `api.py` inside each app; business rules live in `services.py` so views stay small;
`config/api_urls.py` lists all API routes in one place.

## 3. Setup on Windows (PowerShell)
Open the extracted `HireFlow` folder in VS Code, open the terminal (Ctrl+`), then:

```powershell
# 3.1 Create and activate the virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
#   If PowerShell says scripts are disabled, run once:  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 3.2 Install packages
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Create the MySQL database
Open MySQL Workbench, connect as root, open a new query tab and run (choose your own password):
```sql
CREATE DATABASE hireflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hireflow_user'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON hireflow.* TO 'hireflow_user'@'localhost';
GRANT ALL PRIVILEGES ON test_hireflow.* TO 'hireflow_user'@'localhost';
FLUSH PRIVILEGES;
```
(The `test_hireflow` line lets Django create a temporary test database when you run the tests.)

### 3.4 Create your `.env`
```powershell
Copy-Item .env.example .env
notepad .env
```
Set `DJANGO_SECRET_KEY` to a long random text, and `DB_USER`, `DB_PASSWORD` to the values above.
Generate a key with: `python -c "import secrets; print(secrets.token_urlsafe(50))"`.

**Quick fallback without MySQL:** set `DB_ENGINE=sqlite` in `.env`. Everything works with a local `db.sqlite3` file.
Use this if `mysqlclient` does not install; in that case delete the `mysqlclient` line from `requirements.txt`.

### 3.5 First run checklist
```powershell
python manage.py check              # finds configuration errors; should print "no issues"
python manage.py makemigrations     # creates the migration files (the custom User model is already configured)
python manage.py migrate            # creates all tables in MySQL
python manage.py test               # runs the automated tests
python manage.py seed_demo          # optional: demo users, company, jobs (see docs/USER_GUIDE.md)
python manage.py createsuperuser    # optional: your own administrator (email + full name + password)
python manage.py runserver          # start the site
```
Open http://127.0.0.1:8000/ . Stop the server with Ctrl+C.

What the commands do: `check` validates settings and models; `makemigrations` writes Python files describing table
changes; `migrate` applies them to the database; `test` runs the tests in a temporary database; `seed_demo` inserts demo
rows; `createsuperuser` creates an administrator (role *Administrator*); `runserver` starts the development server.

**Do not delete the `migrations` folders or your database without asking first**: it destroys data or history.

## 4. Where things are
* Website: `/`  |  Admin dashboard: `/dashboard/admin/`  |  Django admin: `/django-admin/`  |  API: `/api/`
* API docs and Postman steps: `docs/API_ENDPOINTS.md`  |  Tables and ER diagram: `docs/DATABASE_SCHEMA.md`
* Emails (password reset) are printed in the terminal unless `EMAIL_ENABLED=True` in `.env`.

## 5. Security notes
Passwords are hashed; roles are enforced on the server; recruiters can only touch their own company's jobs and
applicants; resumes are stored outside any public folder, validated by extension, size and file signature, and can be
downloaded only by the owner, a recruiter the candidate applied to, or an administrator. Secrets are in `.env`
(never commit it). For a real deployment set `DJANGO_DEBUG=False`, a real secret key and `DJANGO_ALLOWED_HOSTS`.

## 6. Git
```powershell
git init
git add .
git status                           # check that .env, .venv and db.sqlite3 are NOT listed
git commit -m "Initial HireFlow project"
```

## 7. Not included (optional future work)
Email delivery to real inboxes, interview calendar view, resume keyword extraction and job recommendations, CSV
reports, deployment. AI matching, if added, must only support humans and never decide hiring automatically.
