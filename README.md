# Personal Finance Tracker

A Flask-based personal finance application for tracking income, expenses, budgets, savings goals, and financial summaries for individual users.

## Features

- User registration and login
- Secure password hashing with Werkzeug
- Add, edit, and delete transactions
- Income and expense tracking by category
- Dashboard summary cards
- Budget planning and current budget usage
- Savings goal tracking
- Monthly and category reports
- CSV and PDF export support
- Responsive Bootstrap UI

## Project Structure

- app.py – Flask routes and application logic
- models.py – SQLite database logic and analytics queries
- templates/ – Jinja templates for login, dashboard, reports, and other screens
- static/ – CSS and JavaScript assets
- database/finance.db – SQLite database file
- requirements.txt – Python dependencies

## Tech Stack

- Python 3
- Flask
- SQLite
- Bootstrap 5
- Chart.js
- ReportLab

## Setup

1. Open a terminal in the project folder.
2. Create a virtual environment:
   python -m venv venv
3. Activate the virtual environment:
   - Windows PowerShell: .\venv\Scripts\Activate.ps1
   - Windows CMD: .\venv\Scripts\activate.bat
4. Install dependencies:
   pip install -r requirements.txt
5. Start the app:
   python app.py
6. Open this URL in a browser:
   http://127.0.0.1:5000/login

## Database Notes

The app uses SQLite and initializes tables automatically through the app startup logic. Existing data is preserved when the project is restarted.

## Default Run Command

python app.py

## Project Goal

This project is designed as a professional B.Tech AI & Data Science macro project demonstrating a practical finance application with authentication, analytics, and portfolio-ready UI.
