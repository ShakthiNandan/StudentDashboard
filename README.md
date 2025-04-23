# Academic Dashboard

A Flask-based academic dashboard for students and staff to view academic performance, marks, and analytics.

## Features

- Student Dashboard
  - View personal information and academic details
  - Semester-wise mark analysis with interactive charts
  - CGPA progression tracking
  - Attendance monitoring

- Staff Dashboard
  - View class performance analytics
  - Subject-wise average marks
  - Top performers list
  - Real-time data refresh

## Setup

1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database and populate with sample data:
   ```bash
   python populate_db.py
   ```
   - You'll be prompted to enter the number of students to generate
   - The script will create sample data for students, marks, and staff

4. Run the application:
   ```bash
   python app.py
   ```

5. Access the dashboard:
   - Open http://localhost:5000 in your browser
   - Use the login page to access either student or staff dashboard
   - For students: Use any student name generated in the database
   - For staff: Use any staff name (format: "Prof. [Name]")

## Project Structure

```
academic_dashboard/
├── app.py              # Flask application and routes
├── models.py           # SQLAlchemy database models
├── populate_db.py      # Database seeding script
├── requirements.txt    # Python dependencies
├── templates/         
│   ├── base.html      # Base template with common layout
│   ├── login.html     # Login page
│   ├── student_dashboard.html  # Student view
│   └── staff_dashboard.html    # Staff view
└── README.md
```

## Technologies Used

- Backend: Python Flask
- Database: SQLite with SQLAlchemy ORM
- Frontend: Bootstrap 5, Plotly.js
- Charts: Interactive visualizations using Plotly
- Authentication: Simple name-based login system

## Development

- The application uses SQLite for simplicity
- All data is generated randomly but maintains realistic relationships
- Charts are rendered client-side using Plotly.js
- The interface is responsive and works on mobile devices 