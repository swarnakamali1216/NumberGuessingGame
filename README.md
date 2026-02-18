---

## ⚠️ Known Issues & TODO
 
 - OAuth redirect: Google OAuth will fail with `redirect_uri_mismatch` unless you add the exact redirect URI to your Google Cloud Console. Use `http://127.0.0.1:5000/authorize/google` for local testing.
 - Pylance warnings: some legacy imports (e.g., `utils.helpers`) were removed during cleanup — a minimal `utils/helpers.py` has been restored for compatibility, but the CLI in `main.py` is deprecated.
 - Database migrations: Alembic has been scaffolded and the DB was stamped to the initial migration. When changing models, run `alembic revision --autogenerate -m "msg"` and apply with `alembic upgrade head`.
 - Production hardening pending: session cookie flags, rate limiting, and structured logging should be enabled before exposing publicly.

If you want help fixing any of the above, tell me which one and I will implement it.

---

## 🔎 Viewing user login details

You can inspect user accounts and login details either through the **Admin Dashboard** in the app or directly in PostgreSQL.

 - Admin dashboard (UI):
   1. Start the server: `python server_postgresql.py`.
   2. Open `http://127.0.0.1:5000/admin` and enter the `ADMIN_PASSWORD` from `web/.env`.
   3. The dashboard lists users and summary stats (name, email/guest flag, games won/lost, best score).

 - Direct DB access (psql):
   1. Connect with psql (example):
      ```powershell
      psql postgresql://gameuser:swarna_00_@localhost:5432/number_guessing_db
      ```
   2. Inspect the `users` table:
      ```sql
      SELECT id, name, email, google_id, avatar_url, created_at, is_admin
      FROM users
      ORDER BY created_at DESC
      LIMIT 100;
      ```
   3. Inspect profiles:
      ```sql
      SELECT u.id, u.name, p.games_won, p.best_score, p.current_streak
      FROM users u
      JOIN player_profiles p ON p.user_id = u.id
      ORDER BY p.games_won DESC;
      ```

 - Using pgAdmin: open the database, expand **Schemas → public → Tables → users**, then View Data → All Rows.

 - Logs: If you enabled Flask logging to stdout, you can also see login events in the server console. The Google OAuth flow logs redirect URIs and token events to help debugging.

---
# 🎯 GUESS IT — Number Guessing Game

A modern, responsive **number guessing game** built with **Flask**, **PostgreSQL**, and a gaming-style UI. Features session-based multiplayer support, user authentication (Google OAuth + Guest login), detailed stats tracking, and an admin dashboard.

---

## ✨ Features

- **🎮 Gaming UI**: Dark theme with neon accents, smooth animations, responsive design.
- **👤 Authentication**: 
  - Guest login (no signup needed).
  - Google OAuth (optional — only if credentials provided).
  - Admin panel (password-protected user management).
- **📊 Player Stats**: Games won/lost, best/worst scores, win streaks, achievements.
- **🏆 Leaderboard**: Global rankings by best score.
- **💾 Persistent Storage**: PostgreSQL database (scales beyond JSON).
- **🔐 Privacy**: Guest mode isolates player data; admin-only visibility for user stats.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Flask 3.1 |
| **ORM** | SQLAlchemy 2.0 + Flask-SQLAlchemy |
| **Database** | PostgreSQL 12+ |
| **Authentication** | Flask-Login + Authlib (OAuth) |
| **Frontend** | Bootstrap 5, Jinja2, Chart.js |
| **Styling** | Custom CSS (dark gaming theme) |

---

## 📋 Prerequisites

- **Python 3.10+** (tested on 3.11)
- **PostgreSQL 12+** (running locally or remote)
- **pip** or **conda**
- Windows PowerShell or command prompt

---

## 🚀 Quick Start (Windows)

### 1. Clone / Open the Project
```powershell
cd "C:\Number Guessing Game"
```

### 2. Create & Activate Virtual Environment
```powershell
python -m venv web\.venv
web\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
cd "C:\Number Guessing Game"
pip install -r requirements.txt
cd web
```
*(Or install manually)*:
```powershell
pip install flask flask_sqlalchemy flask_login authlib python-dotenv psycopg2-binary
```

### 4. Configure PostgreSQL Database

#### Option A: Using pgAdmin (Recommended)
1. Open **pgAdmin** → connect to your PostgreSQL server.
2. Create a **Login Role** named `gameuser`:
   - Right-click **Login/Group Roles** → **Create** → **Login/Group Role**.
   - Name: `gameuser`
   - Definition → Password: `swarna_00_` (or your preferred password)
   - Privileges → Can Login: **Yes**
3. Create a **Database** named `number_guessing_db`:
   - Right-click **Databases** → **Create** → **Database**.
   - Database: `number_guessing_db`
   - Owner: `gameuser` (select from dropdown)
4. Verify connection in Query Tool:
   ```sql
   SELECT * FROM users; -- Should return empty initially
   ```

#### Option B: Using Command Line (psql)
```bash
psql -U postgres  # Connect as superuser
CREATE ROLE gameuser WITH LOGIN PASSWORD 'swarna_00_';
CREATE DATABASE number_guessing_db OWNER gameuser;
GRANT ALL PRIVILEGES ON DATABASE number_guessing_db TO gameuser;
```

### 5. Configure Environment Variables
Create or edit `web/.env`:
```env
SECRET_KEY=your-random-secret-key-here-change-in-production
DATABASE_URL=postgresql://gameuser:swarna_00_@localhost:5432/number_guessing_db
ADMIN_PASSWORD=choose_a_secure_admin_password
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**Notes**:
- `SECRET_KEY`: Generate a random string (e.g., `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `DATABASE_URL`: Ensure credentials match your PostgreSQL user/password.
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`: **Optional** — leave blank to use Guest login only.

### 6. Run the Server
```powershell
cd "C:\Number Guessing Game\web"
python server_postgresql.py
```

You'll see:
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### 7. Open the App
Visit **http://127.0.0.1:5000** in your browser.

---

## 🎮 Usage

### Guest Login
1. Click **"Play as Guest"**.
2. Enter a 2–20 character nickname.
3. Choose difficulty (Easy, Medium, Hard).
4. Guess until you find the secret number.
5. Check your stats on the **Profile** page.

### Admin Dashboard
1. Visit **http://127.0.0.1:5000/admin**.
2. Enter the password from `ADMIN_PASSWORD` in `.env`.
3. View all registered users and their stats.

### Optional: Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a **Web Application** OAuth 2.0 credential.
3. Set **Authorized Redirect URI**: `http://127.0.0.1:5000/authorize/google`
4. Copy the **Client ID** and **Client Secret** to `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```
5. Restart the server — Google login button will appear.

---

## 📁 Project Structure

```
Number Guessing Game/
├── web/
│   ├── server_postgresql.py       # Main Flask app (PostgreSQL + OAuth)
│   ├── templates/
│   │   ├── base.html              # Base template (navbar, footer)
│   │   ├── login.html             # Login/guest entry page
│   │   ├── game.html              # Game interface
│   │   ├── profile.html           # Player stats page
│   │   ├── leaderboard.html       # Global rankings
│   │   ├── admin_login.html       # Admin password page
│   │   ├── admin_dashboard.html   # User management
│   │   ├── 404.html, 500.html     # Error pages
│   │   └── ...
│   ├── static/
│   │   ├── style.css              # Custom gaming CSS
│   │   ├── chart.js               # Chart.js integration
│   │   └── ...
│   ├── .venv/                     # Virtual environment (git-ignored)
│   ├── .env                       # Environment config (git-ignored)
│   ├── .env.example               # Example config
│   └── requirements.txt           # Python dependencies
├── migrate_to_postgresql.py       # JSON-to-Postgres migration helper (optional)
├── README.md                      # This file
├── main.py                        # Legacy CLI version (deprecated)
└── ... (other legacy files)
```

---

## 🗄️ Database Schema

### `users` Table
```sql
id (PRIMARY KEY)
google_id (VARCHAR, nullable, unique)
email (VARCHAR, nullable, unique)
name (VARCHAR)
avatar_url (VARCHAR, nullable)
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
is_admin (BOOLEAN, default false)
```

### `player_profiles` Table
```sql
id (PRIMARY KEY)
user_id (FOREIGN KEY → users.id)
games_won (INTEGER, default 0)
games_lost (INTEGER, default 0)
best_score (INTEGER, nullable)
worst_score (INTEGER, nullable)
total_attempts (INTEGER, default 0)
current_streak (INTEGER, default 0)
best_streak (INTEGER, default 0)
achievements (JSON array)
created_at (TIMESTAMP)
```

### `games` Table
```sql
id (PRIMARY KEY)
user_id (FOREIGN KEY → users.id)
difficulty (VARCHAR: 'easy', 'medium', 'hard')
attempts (INTEGER)
won (BOOLEAN)
secret_number (INTEGER)
guesses (JSON array)
played_at (TIMESTAMP)
completed_at (TIMESTAMP, nullable)
```

---

## 🔍 Troubleshooting

### "Database connection failed"
- Ensure PostgreSQL is running: `psql --version`
- Check `.env` `DATABASE_URL` matches your DB credentials.
- Test with `psql`: `psql postgresql://gameuser:swarna_00_@localhost:5432/number_guessing_db`

### "ModuleNotFoundError: No module named 'flask'"
- Activate virtualenv: `web\.venv\Scripts\Activate.ps1`
- Reinstall: `pip install -r requirements.txt`

### "OAuth client not found"
- This is normal if `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are not set.
- Guest login will work fine — the Google button is hidden.
- To enable OAuth, configure credentials in Google Cloud Console.

### "Port 5000 already in use"
- Kill the process: `lsof -ti:5000 | xargs kill -9` (macOS/Linux)
- On Windows: `netstat -ano | findstr :5000`, then `taskkill /PID <PID> /F`

---

## 📦 Dependencies

- **flask** — Web framework
- **flask-sqlalchemy** — ORM
- **flask-login** — Session management
- **authlib** — OAuth 2.0
- **python-dotenv** — Environment config
- **psycopg2-binary** — PostgreSQL adapter
- **sqlalchemy** — Database toolkit

Install all:
```powershell
pip install flask flask_sqlalchemy flask_login authlib python-dotenv psycopg2-binary
```

---

## 🚢 Deployment (Production)

1. Use a production WSGI server (**gunicorn** or **uWSGI**):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 'web.server_postgresql:app'
   ```
2. Set `SECRET_KEY` to a strong random value.
3. Use a remote PostgreSQL instance (e.g., AWS RDS, Azure Database).
4. Set `DATABASE_URL` to the remote connection string.
5. Configure HTTPS/SSL via a reverse proxy (nginx, Apache).
6. Use environment variables (not `.env` file) for secrets on the server.

---

## 📝 License & Attribution

© 2026 **Swarna1216** | All Rights Reserved

---

## 🤝 Contributing

To contribute improvements:
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Commit changes: `git commit -m "Add feature"`
4. Push to branch: `git push origin feature/my-improvement`
5. Open a pull request.

---

## 📧 Support

For issues or questions:
- Check the **Troubleshooting** section above.
- Review database logs in pgAdmin.
- Enable Flask debug mode for detailed error messages.

---

**Happy guessing! 🎯**
