import csv
import io
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.security import check_password_hash, generate_password_hash

from models import (
    add_transaction,
    create_goal,
    delete_goal,
    delete_transaction,
    get_budget,
    get_budget_usage,
    get_category_report,
    get_dashboard_summary,
    get_expense_by_category,
    get_financial_insights,
    get_goals,
    get_income_vs_expense,
    get_monthly_expense_trend,
    get_monthly_report,
    get_transaction_by_id,
    get_transactions,
    get_user_by_email,
    get_user_by_id,
    init_db,
    register_user,
    save_budget,
    update_goal,
    update_transaction,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.config["SECRET_KEY"] = "finance-tracker-secret-key"


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for("register"))

        if get_user_by_email(email):
            flash("An account with that email already exists.", "warning")
            return redirect(url_for("register"))

        user_id = register_user(name, email, generate_password_hash(password))
        session["user_id"] = user_id
        session["user_name"] = name
        flash("Registration successful. Welcome!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    summary = get_dashboard_summary(user_id)
    expense_by_category = get_expense_by_category(user_id)
    income_vs_expense = get_income_vs_expense(user_id)
    monthly_expense = get_monthly_expense_trend(user_id, months=6)
    budget_usage = get_budget_usage(user_id)
    insights = get_financial_insights(user_id)
    goals = get_goals(user_id)

    chart_categories = [item["category"] for item in expense_by_category]
    chart_expense_values = [float(item["total"]) for item in expense_by_category]

    monthly_labels = [item["month"] for item in monthly_expense]
    monthly_values = [float(item["total"]) for item in monthly_expense]

    return render_template(
        "dashboard.html",
        summary=summary,
        expense_by_category=expense_by_category,
        income_vs_expense=income_vs_expense,
        monthly_expense=monthly_expense,
        budget_usage=budget_usage,
        insights=insights,
        goals=goals,
        chart_categories=chart_categories,
        chart_expense_values=chart_expense_values,
        monthly_labels=monthly_labels,
        monthly_values=monthly_values,
    )


@app.route("/transactions", methods=["GET", "POST"])
@login_required
def transactions():
    user_id = session["user_id"]

    if request.method == "POST":
        transaction_type = request.form.get("type", "").strip().lower()
        category = request.form.get("category", "").strip()
        amount = request.form.get("amount", type=float)
        description = request.form.get("description", "").strip()
        date_value = request.form.get("date") or datetime.today().strftime("%Y-%m-%d")

        if transaction_type not in {"income", "expense"}:
            flash("Transaction type is invalid.", "danger")
            return redirect(url_for("transactions"))

        if not category or amount is None or amount <= 0:
            flash("Category and valid amount are required.", "danger")
            return redirect(url_for("transactions"))

        add_transaction(user_id, transaction_type, category, amount, description, date_value)
        flash("Transaction added successfully.", "success")
        return redirect(url_for("transactions"))

    filters = {
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
        "category": request.args.get("category", "").strip(),
        "type": request.args.get("type", "").strip().lower(),
        "amount_min": request.args.get("amount_min"),
        "amount_max": request.args.get("amount_max"),
        "sort": request.args.get("sort", "date_desc"),
    }

    transaction_rows = get_transactions(user_id, filters)
    return render_template("transactions.html", transactions=transaction_rows, filters=filters)


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    user_id = session["user_id"]
    transaction = get_transaction_by_id(user_id, transaction_id)

    if not transaction:
        flash("Transaction not found.", "warning")
        return redirect(url_for("transactions"))

    if request.method == "POST":
        transaction_type = request.form.get("type", "").strip().lower()
        category = request.form.get("category", "").strip()
        amount = request.form.get("amount", type=float)
        description = request.form.get("description", "").strip()
        date_value = request.form.get("date") or datetime.today().strftime("%Y-%m-%d")

        if transaction_type not in {"income", "expense"}:
            flash("Transaction type is invalid.", "danger")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        if not category or amount is None or amount <= 0:
            flash("Category and valid amount are required.", "danger")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        update_transaction(user_id, transaction_id, transaction_type, category, amount, description, date_value)
        flash("Transaction updated successfully.", "success")
        return redirect(url_for("transactions"))

    return render_template("transactions.html", edit_transaction=transaction, filters={})


@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete_transaction_route(transaction_id):
    user_id = session["user_id"]
    delete_transaction(user_id, transaction_id)
    flash("Transaction deleted successfully.", "success")
    return redirect(url_for("transactions"))


@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    user_id = session["user_id"]
    current_budget = get_budget(user_id)
    usage = get_budget_usage(user_id)

    if request.method == "POST":
        budget_value = request.form.get("monthly_budget", type=float)
        if budget_value is None or budget_value <= 0:
            flash("Budget must be a positive number.", "danger")
            return redirect(url_for("budget"))

        save_budget(user_id, budget_value)
        if usage["spent"] > budget_value:
            flash("Budget exceeded. Consider reducing discretionary expenses.", "warning")
        else:
            flash("Monthly budget saved successfully.", "success")
        return redirect(url_for("budget"))

    return render_template("budget.html", current_budget=current_budget, usage=usage)


@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    user_id = session["user_id"]

    if request.method == "POST":
        if request.form.get("action") == "update":
            goal_id = request.form.get("goal_id", type=int)
            goal_name = request.form.get("goal_name", "").strip()
            target_amount = request.form.get("target_amount", type=float)
            saved_amount = request.form.get("saved_amount", type=float)

            if goal_id and goal_name and target_amount and saved_amount is not None:
                update_goal(user_id, goal_id, goal_name, target_amount, saved_amount)
                flash("Savings goal updated.", "success")
            return redirect(url_for("goals"))

        goal_name = request.form.get("goal_name", "").strip()
        target_amount = request.form.get("target_amount", type=float)
        saved_amount = request.form.get("saved_amount", type=float) or 0

        if not goal_name or target_amount is None or target_amount <= 0:
            flash("Goal name and a valid target amount are required.", "danger")
            return redirect(url_for("goals"))

        create_goal(user_id, goal_name, target_amount, saved_amount)
        flash("Savings goal added successfully.", "success")
        return redirect(url_for("goals"))

    goals_list = get_goals(user_id)
    return render_template("goals.html", goals=goals_list)


@app.route("/goals/<int:goal_id>/delete", methods=["POST"])
@login_required
def delete_goal_route(goal_id):
    user_id = session["user_id"]
    delete_goal(user_id, goal_id)
    flash("Savings goal deleted.", "success")
    return redirect(url_for("goals"))


@app.route("/reports")
@login_required
def reports():
    user_id = session["user_id"]
    selected_month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    monthly_report = get_monthly_report(user_id, selected_month)
    category_report = get_category_report(user_id)

    total_spent = sum(float(item["total"]) for item in monthly_report)
    total_income = sum(float(item["amount"]) for item in get_transactions(user_id) if item["type"] == "income")

    return render_template(
        "reports.html",
        selected_month=selected_month,
        monthly_report=monthly_report,
        category_report=category_report,
        total_spent=total_spent,
        total_income=total_income,
    )


@app.route("/export/csv")
@login_required
def export_csv():
    user_id = session["user_id"]
    transactions = get_transactions(user_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Category", "Amount", "Description"])

    for txn in transactions:
        writer.writerow([
            txn["date"],
            txn["type"],
            txn["category"],
            txn["amount"],
            txn["description"],
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=finance_report.csv"
    return response


@app.route("/export/pdf")
@login_required
def export_pdf():
    user_id = session["user_id"]
    transactions = get_transactions(user_id)

    output = io.BytesIO()
    pdf = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph("Personal Finance Tracker Report", styles["Title"]))
    elements.append(Spacer(1, 20))

    rows = [["Date", "Type", "Category", "Amount", "Description"]]
    for txn in transactions:
        rows.append([
            txn["date"],
            txn["type"],
            txn["category"],
            f"${txn['amount']:.2f}",
            txn["description"] or "-",
        ])

    table = Table(rows)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ("ALIGN", (3, 1), (3, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ])
    )
    elements.append(table)
    pdf.build(elements)

    pdf_data = output.getvalue()
    response = Response(pdf_data, mimetype="application/pdf")
    response.headers["Content-Disposition"] = "attachment; filename=finance_report.pdf"
    return response


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
