# RePlate — Food Donation Platform

A complete college-project prototype for connecting food donors with nearby verified NGOs and food banks.

## Tagline
**Rescue. Redistribute. Repeat.**

## Features
- Donor registration/login
- NGO/Food Bank registration/login
- Admin panel
- Food donation form
- Nearest verified NGO matching using GPS coordinates
- NGO accept/reject workflow
- Pickup and delivery status tracking
- Donation history
- Dashboard statistics
- Responsive UI
- SQLite database

## Demo accounts
- Donor: donor@replate.demo / 1234
- NGO: ngo@replate.demo / 1234
- Admin: admin@replate.demo / admin123

## Run locally

1. Install Python 3.10+.
2. Open terminal in this folder.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Run:
   `python app.py`
5. Open:
   `http://127.0.0.1:5000`

The SQLite database is created automatically.

## Notes
This is a college-project prototype. Passwords are stored as plain text only to keep the demonstration simple; for production, use password hashing, CSRF protection, secure sessions, proper role permissions, an external database, and real notification/map services.
