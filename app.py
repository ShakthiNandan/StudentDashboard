import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, User, Student, Mark
import plotly.express as px
import plotly.graph_objects as go
import plotly.utils
import pandas as pd
import json
import uuid
import random
from pyvis.network import Network
import networkx as nx
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from tornado.ioloop import IOLoop
import threading
import time

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///academic.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    return app

app = create_app()

def create_animated_charts(data, semester):
    """Create animated charts for staff dashboard."""
    df = pd.DataFrame(data)
    
    # Animated Scatter Plot
    fig_scatter = px.scatter(
        df,
        x='semester',
        y='total',
        animation_frame='semester',
        animation_group='student',
        size='total',
        color='subject',
        title='Student Performance Across Semesters',
        template='plotly_white'
    )
    fig_scatter.update_layout(
        xaxis_title='Semester',
        yaxis_title='Total Marks',
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 1000, "redraw": True},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    )
                ]
            )
        ]
    )
    
    # Animated Bar Chart
    fig_bar = px.bar(
        df,
        x='subject',
        y='total',
        animation_frame='semester',
        color='subject',
        title='Subject Performance Across Semesters',
        template='plotly_white'
    )
    fig_bar.update_layout(
        xaxis_title='Subject',
        yaxis_title='Total Marks',
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 1000, "redraw": True},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    )
                ]
            )
        ]
    )
    
    return {
        'scatter': json.dumps(fig_scatter, cls=plotly.utils.PlotlyJSONEncoder),
        'bar': json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder)
    }

def create_network_diagram():
    """Create a network visualization of student-staff relationships."""
    
    # Create network visualization
    net = Network(height="500px", width="100%", notebook=False, directed=False)
    
    # Add nodes for students and staff
    students = Student.query.all()
    staff = User.query.filter_by(role='staff').all()
    
    # Ensure static directory exists
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Add student nodes
    for student in students:
        net.add_node(
            str(student.id), 
            label=student.user.name, 
            title=f"Student: {student.user.name}<br>Reg No: {student.reg_no}<br>Department: {student.department}",
            color="#97c2fc",
            shape="dot",
            size=15
        )
    
    # Add staff nodes
    for staff_member in staff:
        department = getattr(staff_member, 'department', 'Not specified')
        net.add_node(
            str(staff_member.id), 
            label=staff_member.name, 
            title=f"Staff: {staff_member.name}<br>Department: {department}",
            color="#ff9999",
            shape="star",
            size=25
        )
    
    # Add edges (random mentorship for demonstration)
    for student in students:
        # Assign 1-2 random staff mentors to each student
        num_mentors = random.randint(1, 2)
        mentors = random.sample(staff, min(num_mentors, len(staff)))
        for mentor in mentors:
            net.add_edge(
                str(student.id), 
                str(mentor.id), 
                title="Mentor", 
                color="#CCCCCC",
                width=2
            )
    
    # Enable physics for animation
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -80000,
          "springConstant": 0.001,
          "springLength": 200
        },
        "stabilization": {
          "enabled": true,
          "iterations": 1000
        }
      },
      "interaction": {
        "navigationButtons": true,
        "keyboard": true
      }
    }
    """)
    
    # Save to HTML file with absolute path
    network_path = os.path.join(static_dir, 'network.html')
    net.save_graph(network_path)
    
    return "/static/network.html"

def create_bokeh_app():
    # Create a Bokeh app for live GPA streaming
    def modify_doc(doc):
        # Create a figure
        p = figure(title="Live GPA Stream", x_axis_label="Time", y_axis_label="GPA", 
                  width=600, height=400)
        
        # Create a ColumnDataSource
        source = ColumnDataSource(data=dict(x=[], y=[]))
        
        # Add a line renderer
        p.line('x', 'y', source=source, line_width=2)
        
        # Function to update data
        def update():
            # Get current time
            x = time.time()
            
            # Get random GPA (for demonstration)
            y = random.uniform(7.0, 9.5)
            
            # Update data
            new_data = dict(
                x=source.data['x'] + [x],
                y=source.data['y'] + [y]
            )
            
            # Keep only last 20 points
            if len(new_data['x']) > 20:
                new_data['x'] = new_data['x'][-20:]
                new_data['y'] = new_data['y'][-20:]
            
            source.data = new_data
        
        # Add periodic callback
        doc.add_periodic_callback(update, 500)
        
        # Add to document
        doc.add_root(column(p))
    
    # Create application
    app = Application(FunctionHandler(modify_doc))
    
    return app

# Start Bokeh server in a separate thread
def start_bokeh_server():
    """Start the Bokeh server on a dynamically allocated port to avoid conflicts."""
    try:
        # Try using a specific port first, but if it fails, try with port=0 to auto-assign
        try:
            server = Server({'/bokeh': create_bokeh_app()}, io_loop=IOLoop())
            server.start()
            server.io_loop.start()
        except OSError:
            # If the default port is in use, try to use a random available port
            print("Warning: Default Bokeh port is in use. Trying with a random port...")
            server = Server({'/bokeh': create_bokeh_app()}, io_loop=IOLoop(), port=0)
            server.start()
            server.io_loop.start()
    except Exception as e:
        print(f"Failed to start Bokeh server: {e}")
        # Continue without Bokeh server

# Start Bokeh server in a separate thread
bokeh_thread = threading.Thread(target=start_bokeh_server)
bokeh_thread.daemon = True
bokeh_thread.start()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        
        user = User.query.filter_by(name=name, role=role).first()
        if user:
            if role == 'student':
                return redirect(url_for('student_dashboard', id=user.student.id))
            else:
                return redirect(url_for('staff_dashboard', id=user.id))
        flash('User not found')
    return render_template('login.html')

@app.route('/dashboard/student/<uuid:id>')
def student_dashboard(id):
    student = Student.query.get_or_404(id)
    
    # Calculate KPIs
    total_marks = [m.total for m in student.marks]
    cgpa = sum(total_marks) / (len(total_marks) * 100) * 10 if total_marks else 0
    current_semester = max([m.semester for m in student.marks]) if student.marks else 0
    current_semester_marks = [m.total for m in student.marks if m.semester == current_semester]
    current_semester_gpa = sum(current_semester_marks) / (len(current_semester_marks) * 100) * 10 if current_semester_marks else 0
    
    # Create DataFrame for all marks
    df = pd.DataFrame([{
        'semester': m.semester,
        'subject': m.subject,
        'internal': m.internal,
        'external': m.external,
        'total': m.total
    } for m in student.marks])
    
    # 1. Grouped Bar Chart (Internal vs External)
    fig_bar = px.bar(
        df,
        x='subject',
        y=['internal', 'external'],
        title='Internal vs External Marks by Subject',
        barmode='group',
        color_discrete_sequence=['#2ecc71', '#3498db']
    )
    fig_bar.update_layout(
        xaxis_title='Subject',
        yaxis_title='Marks',
        template='plotly_white'
    )
    
    # 2. Line Chart (CGPA Trend)
    semester_gpa = df.groupby('semester')['total'].mean().reset_index()
    semester_gpa['gpa'] = semester_gpa['total'] / 10
    fig_line = px.line(
        semester_gpa,
        x='semester',
        y='gpa',
        title='CGPA Trend Across Semesters',
        markers=True
    )
    fig_line.update_layout(
        xaxis_title='Semester',
        yaxis_title='GPA',
        template='plotly_white'
    )
    
    # 3. Donut Chart (CGPA Gauge)
    fig_donut = go.Figure(go.Indicator(
        mode="gauge+number",
        value=cgpa,
        title={'text': "CGPA"},
        gauge={
            'axis': {'range': [0, 10]},
            'bar': {'color': "#2ecc71"},
            'steps': [
                {'range': [0, 6], 'color': "#e74c3c"},
                {'range': [6, 8], 'color': "#f1c40f"},
                {'range': [8, 10], 'color': "#2ecc71"}
            ]
        }
    ))
    fig_donut.update_layout(template='plotly_white')
    
    # 4. Heatmap
    pivot_df = df.pivot(index='subject', columns='semester', values='total')
    fig_heatmap = px.imshow(
        pivot_df,
        title='Marks Heatmap (Subjects × Semesters)',
        color_continuous_scale='RdYlGn'
    )
    fig_heatmap.update_layout(
        xaxis_title='Semester',
        yaxis_title='Subject',
        template='plotly_white'
    )
    
    # 5. Radar Chart (Current Semester)
    current_semester_df = df[df['semester'] == current_semester]
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=current_semester_df['total'],
        theta=current_semester_df['subject'],
        fill='toself',
        name='Current Semester'
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        title='Current Semester Performance',
        template='plotly_white'
    )
    
    # 6. Box Plot
    fig_box = px.box(
        df,
        x='semester',
        y='total',
        title='Marks Distribution by Semester'
    )
    fig_box.update_layout(
        xaxis_title='Semester',
        yaxis_title='Total Marks',
        template='plotly_white'
    )
    
    # 7. Animated Scatter Plot (Performance Animation)
    fig_scatter = px.scatter(
        df,
        x='semester',
        y='total',
        animation_frame='semester',
        animation_group='subject',
        size='total',
        color='subject',
        title='Performance Across Semesters'
    )
    fig_scatter.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 1000, "redraw": True},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    )
                ],
                direction="left",
                pad={"r": 10, "t": 87},
                showactive=True,
                x=0.1,
                xanchor="right",
                y=0,
                yanchor="top"
            )
        ]
    )
    
    # 8. Animated Bar Chart (Subject Performance)
    fig_bar_animated = px.bar(
        df,
        x='subject',
        y='total',
        animation_frame='semester',
        title='Subject Performance Across Semesters'
    )
    fig_bar_animated.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 1000, "redraw": True},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    )
                ],
                direction="left",
                pad={"r": 10, "t": 87},
                showactive=True,
                x=0.1,
                xanchor="right",
                y=0,
                yanchor="top"
            )
        ]
    )
    
    # 9. Progress Chart (Cumulative Performance)
    # Calculate cumulative average for each subject across semesters
    subject_progress = df.groupby(['subject', 'semester'])['total'].mean().reset_index()
    subject_progress = subject_progress.sort_values(['subject', 'semester'])
    subject_progress['cumulative_avg'] = subject_progress.groupby('subject')['total'].transform('cumsum') / subject_progress.groupby('subject')['semester'].transform('count')
    
    fig_progress = px.line(
        subject_progress,
        x='semester',
        y='cumulative_avg',
        color='subject',
        title='Subject Progress Over Time',
        labels={'cumulative_avg': 'Cumulative Average', 'semester': 'Semester'}
    )
    fig_progress.update_layout(
        template='plotly_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    # Create network diagram
    network_path = create_network_diagram()
    
    # Prepare all plots
    plots = {
        'bar': json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder),
        'line': json.dumps(fig_line, cls=plotly.utils.PlotlyJSONEncoder),
        'donut': json.dumps(fig_donut, cls=plotly.utils.PlotlyJSONEncoder),
        'heatmap': json.dumps(fig_heatmap, cls=plotly.utils.PlotlyJSONEncoder),
        'radar': json.dumps(fig_radar, cls=plotly.utils.PlotlyJSONEncoder),
        'box': json.dumps(fig_box, cls=plotly.utils.PlotlyJSONEncoder),
        'scatter': json.dumps(fig_scatter, cls=plotly.utils.PlotlyJSONEncoder),
        'bar_animated': json.dumps(fig_bar_animated, cls=plotly.utils.PlotlyJSONEncoder),
        'progress': json.dumps(fig_progress, cls=plotly.utils.PlotlyJSONEncoder)
    }
    
    return render_template('student_dashboard.html',
                         student=student,
                         plots=plots,
                         network_path=network_path,
                         kpis={
                             'cgpa': round(cgpa, 2),
                             'attendance': 95,  # This should be calculated from actual attendance data
                             'current_semester_gpa': round(current_semester_gpa, 2)
                         })

@app.route('/api/student-refresh-stats', methods=['POST'])
def student_refresh_stats():
    """Endpoint for student dashboard data refresh"""
    data = request.json
    semester = data.get('semester')
    student_id = data.get('student_id')
    
    if not semester or not student_id:
        return jsonify({'error': 'Semester and student_id required'}), 400
    
    try:
        # Convert string ID to UUID object
        student_uuid = uuid.UUID(student_id)
        # Get student
        student = Student.query.get_or_404(student_uuid)
        
        # Get all marks for the student
        all_marks = Mark.query.filter_by(student_id=student.id).all()
        
        # Create DataFrame for all marks
        df = pd.DataFrame([{
            'semester': m.semester,
            'subject': m.subject,
            'internal': m.internal,
            'external': m.external,
            'total': m.total
        } for m in all_marks])
        
        # Filter by semester if not 'all'
        if semester != 'all':
            df = df[df['semester'] == int(semester)]
        
        # Calculate KPIs
        total_marks = df['total'].tolist()
        cgpa = sum(total_marks) / (len(total_marks) * 100) * 10 if total_marks else 0
        current_semester = max(df['semester'].unique()) if not df.empty else 0
        current_semester_marks = df[df['semester'] == current_semester]['total'].tolist()
        current_semester_gpa = sum(current_semester_marks) / (len(current_semester_marks) * 100) * 10 if current_semester_marks else 0
        
        # 1. Grouped Bar Chart (Internal vs External)
        fig_bar = px.bar(
            df,
            x='subject',
            y=['internal', 'external'],
            title='Internal vs External Marks by Subject',
            barmode='group',
            color_discrete_sequence=['#2ecc71', '#3498db']
        )
        fig_bar.update_layout(
            xaxis_title='Subject',
            yaxis_title='Marks',
            template='plotly_white'
        )
        
        # 2. Line Chart (CGPA Trend)
        semester_gpa = df.groupby('semester')['total'].mean().reset_index()
        semester_gpa['gpa'] = semester_gpa['total'] / 10
        fig_line = px.line(
            semester_gpa,
            x='semester',
            y='gpa',
            title='CGPA Trend Across Semesters',
            markers=True
        )
        fig_line.update_layout(
            xaxis_title='Semester',
            yaxis_title='GPA',
            template='plotly_white'
        )
        
        # 3. Donut Chart (CGPA Gauge)
        fig_donut = go.Figure(go.Indicator(
            mode="gauge+number",
            value=cgpa,
            title={'text': "CGPA"},
            gauge={
                'axis': {'range': [0, 10]},
                'bar': {'color': "#2ecc71"},
                'steps': [
                    {'range': [0, 6], 'color': "#e74c3c"},
                    {'range': [6, 8], 'color': "#f1c40f"},
                    {'range': [8, 10], 'color': "#2ecc71"}
                ]
            }
        ))
        fig_donut.update_layout(template='plotly_white')
        
        # 4. Heatmap
        pivot_df = df.pivot(index='subject', columns='semester', values='total')
        fig_heatmap = px.imshow(
            pivot_df,
            title='Marks Heatmap (Subjects × Semesters)',
            color_continuous_scale='RdYlGn'
        )
        fig_heatmap.update_layout(
            xaxis_title='Semester',
            yaxis_title='Subject',
            template='plotly_white'
        )
        
        # 5. Radar Chart (Current Semester)
        current_semester_df = df[df['semester'] == current_semester]
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=current_semester_df['total'],
            theta=current_semester_df['subject'],
            fill='toself',
            name='Current Semester'
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title='Current Semester Performance',
            template='plotly_white'
        )
        
        # 6. Box Plot
        fig_box = px.box(
            df,
            x='semester',
            y='total',
            title='Marks Distribution by Semester'
        )
        fig_box.update_layout(
            xaxis_title='Semester',
            yaxis_title='Total Marks',
            template='plotly_white'
        )
        
        # 7. Animated Scatter Plot (Performance Animation)
        fig_scatter = px.scatter(
            df,
            x='semester',
            y='total',
            animation_frame='semester',
            animation_group='subject',
            size='total',
            color='subject',
            title='Performance Across Semesters'
        )
        fig_scatter.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    buttons=[
                        dict(
                            label="Play",
                            method="animate",
                            args=[None, {
                                "frame": {"duration": 1000, "redraw": True},
                                "mode": "immediate",
                                "fromcurrent": True
                            }]
                        ),
                        dict(
                            label="Pause",
                            method="animate",
                            args=[[None], {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                                "fromcurrent": True
                            }]
                        )
                    ],
                    direction="left",
                    pad={"r": 10, "t": 87},
                    showactive=True,
                    x=0.1,
                    xanchor="right",
                    y=0,
                    yanchor="top"
                )
            ]
        )
        
        # 8. Animated Bar Chart (Subject Performance)
        fig_bar_animated = px.bar(
            df,
            x='subject',
            y='total',
            animation_frame='semester',
            title='Subject Performance Across Semesters'
        )
        fig_bar_animated.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    buttons=[
                        dict(
                            label="Play",
                            method="animate",
                            args=[None, {
                                "frame": {"duration": 1000, "redraw": True},
                                "mode": "immediate",
                                "fromcurrent": True
                            }]
                        ),
                        dict(
                            label="Pause",
                            method="animate",
                            args=[[None], {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                                "fromcurrent": True
                            }]
                        )
                    ],
                    direction="left",
                    pad={"r": 10, "t": 87},
                    showactive=True,
                    x=0.1,
                    xanchor="right",
                    y=0,
                    yanchor="top"
                )
            ]
        )
        
        # 9. Progress Chart (Cumulative Performance)
        # Calculate cumulative average for each subject across semesters
        subject_progress = df.groupby(['subject', 'semester'])['total'].mean().reset_index()
        subject_progress = subject_progress.sort_values(['subject', 'semester'])
        subject_progress['cumulative_avg'] = subject_progress.groupby('subject')['total'].transform('cumsum') / subject_progress.groupby('subject')['semester'].transform('count')
        
        fig_progress = px.line(
            subject_progress,
            x='semester',
            y='cumulative_avg',
            color='subject',
            title='Subject Progress Over Time',
            labels={'cumulative_avg': 'Cumulative Average', 'semester': 'Semester'}
        )
        fig_progress.update_layout(
            template='plotly_white',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        return jsonify({
            'bar_chart': json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder),
            'line_chart': json.dumps(fig_line, cls=plotly.utils.PlotlyJSONEncoder),
            'donut_chart': json.dumps(fig_donut, cls=plotly.utils.PlotlyJSONEncoder),
            'heatmap_chart': json.dumps(fig_heatmap, cls=plotly.utils.PlotlyJSONEncoder),
            'radar_chart': json.dumps(fig_radar, cls=plotly.utils.PlotlyJSONEncoder),
            'box_chart': json.dumps(fig_box, cls=plotly.utils.PlotlyJSONEncoder),
            'scatter_chart': json.dumps(fig_scatter, cls=plotly.utils.PlotlyJSONEncoder),
            'bar_animated_chart': json.dumps(fig_bar_animated, cls=plotly.utils.PlotlyJSONEncoder),
            'progress_chart': json.dumps(fig_progress, cls=plotly.utils.PlotlyJSONEncoder),
            'kpis': {
                'cgpa': round(cgpa, 2),
                'attendance': 95,  # This should be calculated from actual attendance data
                'current_semester_gpa': round(current_semester_gpa, 2)
            }
        })
    except ValueError:
        return jsonify({'error': 'Invalid student ID format'}), 400

@app.route('/dashboard/staff/<uuid:id>')
def staff_dashboard(id):
    """Render the staff dashboard with analytics and visualization."""
    # Get staff user
    staff = User.query.get_or_404(id)
    students = Student.query.all()
    
    # Create network diagram
    network_path = create_network_diagram()
    
    # Get all marks and create DataFrame with proper type conversion
    all_marks = Mark.query.all()
    df = pd.DataFrame([{
        'student_id': str(m.student.id),
        'student_name': m.student.user.name,
        'subject': m.subject,
        'internal': float(m.internal),
        'external': float(m.external),
        'total': float(m.total),
        'semester': m.semester,
        'department': m.student.department
    } for m in all_marks])
    
    # Calculate KPIs
    total_students = len(students)
    avg_cgpa = df['total'].mean() / 10 if not df.empty else 0
    attendance_rate = 95  # This should be calculated from actual attendance data
    
    # Create plots dictionary to store chart data
    plots = {}
    
    # ============= CHART 1: Department Performance Overview =============
    dept_performance = df.groupby('department').agg({
        'total': ['mean', 'count'],
        'internal': 'mean',
        'external': 'mean'
    }).round(2)
    dept_performance.columns = ['avg_total', 'student_count', 'avg_internal', 'avg_external']
    
    fig_dept = go.Figure()
    fig_dept.add_trace(go.Bar(
        x=dept_performance.index,
        y=dept_performance['avg_total'],
        name='Average Total',
        marker_color='#3498db'
    ))
    fig_dept.add_trace(go.Bar(
        x=dept_performance.index,
        y=dept_performance['avg_internal'],
        name='Average Internal',
        marker_color='#2ecc71'
    ))
    fig_dept.add_trace(go.Bar(
        x=dept_performance.index,
        y=dept_performance['avg_external'],
        name='Average External',
        marker_color='#e74c3c'
    ))
    fig_dept.update_layout(
        title='Department Performance Overview',
        xaxis_title='Department',
        yaxis_title='Average Marks',
        barmode='group',
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    plots['dept'] = json.dumps(fig_dept, cls=plotly.utils.PlotlyJSONEncoder)
    
    # ============= CHART 2: Subject-wise Performance Distribution =============
    subject_stats = df.groupby('subject').agg({
        'total': ['mean', 'std', 'min', 'max'],
        'student_id': 'count'
    }).round(2)
    subject_stats.columns = ['mean', 'std', 'min', 'max', 'student_count']
    
    fig_subject = go.Figure()
    fig_subject.add_trace(go.Box(
        y=df['total'],
        x=df['subject'],
        name='Marks Distribution',
        boxpoints='all',
        jitter=0.3,
        pointpos=-1.8,
        marker_color='#3498db'
    ))
    fig_subject.update_layout(
        title='Subject-wise Performance Distribution',
        xaxis_title='Subject',
        yaxis_title='Marks',
        template='plotly_white'
    )
    plots['subject'] = json.dumps(fig_subject, cls=plotly.utils.PlotlyJSONEncoder)
    
    # ============= CHART 3: Top 10 Performers =============
    top_students = df.groupby(['student_id', 'student_name']).agg({
        'total': 'mean',
        'semester': 'count'
    }).round(2)
    top_students.columns = ['avg_marks', 'semesters']
    top_students = top_students.nlargest(10, 'avg_marks').reset_index()
    
    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(
        x=top_students['avg_marks'],
        y=top_students['student_name'],
        orientation='h',
        marker_color='#2ecc71',
        text=top_students['avg_marks'].round(2),
        textposition='auto'
    ))
    fig_top.update_layout(
        title='Top 10 Performers',
        xaxis_title='Average Marks',
        yaxis_title='Student',
        template='plotly_white'
    )
    plots['top'] = json.dumps(fig_top, cls=plotly.utils.PlotlyJSONEncoder)
    
    # ============= CHART 4: Semester-wise Performance Trend =============
    semester_stats = df.groupby('semester').agg({
        'total': ['mean', 'std'],
        'student_id': 'count'
    }).round(2)
    semester_stats.columns = ['mean', 'std', 'student_count']
    
    fig_semester = go.Figure()
    fig_semester.add_trace(go.Scatter(
        x=semester_stats.index,
        y=semester_stats['mean'],
        mode='lines+markers',
        name='Average Marks',
        line=dict(color='#3498db', width=2),
        marker=dict(size=8)
    ))
    fig_semester.add_trace(go.Scatter(
        x=semester_stats.index,
        y=semester_stats['mean'] + semester_stats['std'],
        fill=None,
        mode='lines',
        line=dict(width=0),
        showlegend=False
    ))
    fig_semester.add_trace(go.Scatter(
        x=semester_stats.index,
        y=semester_stats['mean'] - semester_stats['std'],
        fill='tonexty',
        mode='lines',
        line=dict(width=0),
        name='Standard Deviation'
    ))
    fig_semester.update_layout(
        title='Semester-wise Performance Trend',
        xaxis_title='Semester',
        yaxis_title='Average Marks',
        template='plotly_white'
    )
    plots['semester'] = json.dumps(fig_semester, cls=plotly.utils.PlotlyJSONEncoder)
    
    # ============= CHART 5: Subject Performance Heatmap =============
    pivot_df = df.pivot_table(
        index='subject',
        columns='semester',
        values='total',
        aggfunc='mean'
    ).fillna(0).round(2)
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='RdYlGn',
        zmin=0,
        zmax=100
    ))
    fig_heatmap.update_layout(
        title='Subject Performance Heatmap',
        xaxis_title='Semester',
        yaxis_title='Subject',
        template='plotly_white'
    )
    plots['heatmap'] = json.dumps(fig_heatmap, cls=plotly.utils.PlotlyJSONEncoder)
    
    # ============= CHART 6: Department-wise Subject Performance (Radar Chart) =============
    dept_subject_avg = df.pivot_table(
        index='department',
        columns='subject',
        values='total',
        aggfunc='mean'
    ).fillna(0).round(2)
    
    fig_radar = go.Figure()
    for dept in dept_subject_avg.index:
        fig_radar.add_trace(go.Scatterpolar(
            r=dept_subject_avg.loc[dept].values,
            theta=dept_subject_avg.columns,
            fill='toself',
            name=dept
        ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        title='Department-wise Subject Performance',
        template='plotly_white'
    )
    plots['radar'] = json.dumps(fig_radar, cls=plotly.utils.PlotlyJSONEncoder)
    
    # ============= CHART 7: Student Performance Animation =============
    student_semester_avg = df.groupby(['student_id', 'student_name', 'semester'])['total'].mean().reset_index()
    
    fig_scatter = px.scatter(
        student_semester_avg,
        x='semester',
        y='total',
        animation_frame='semester',
        animation_group='student_name',
        size='total',
        color='student_name',
        title='Student Performance Across Semesters',
        template='plotly_white'
    )
    fig_scatter.update_layout(
        xaxis_title='Semester',
        yaxis_title='Average Marks',
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 1000, "redraw": True},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    )
                ],
                direction="left",
                pad={"r": 10, "t": 87},
                showactive=True,
                x=0.1,
                xanchor="right",
                y=0,
                yanchor="top"
            )
        ]
    )
    plots['scatter'] = json.dumps(fig_scatter, cls=plotly.utils.PlotlyJSONEncoder)
    
    # ============= CHART 8: Subject Performance Animation =============
    subject_semester_avg = df.groupby(['subject', 'semester'])['total'].mean().reset_index()
    
    fig_bar = px.bar(
        subject_semester_avg,
        x='subject',
        y='total',
        animation_frame='semester',
        color='subject',
        title='Subject Performance Across Semesters',
        template='plotly_white'
    )
    fig_bar.update_layout(
        xaxis_title='Subject',
        yaxis_title='Average Marks',
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 1000, "redraw": True},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    )
                ],
                direction="left",
                pad={"r": 10, "t": 87},
                showactive=True,
                x=0.1,
                xanchor="right",
                y=0,
                yanchor="top"
            )
        ]
    )
    plots['bar'] = json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder)
    
    # ============= CHART 9: Student Progress Chart =============
    student_progress = df.groupby(['student_id', 'student_name', 'semester'])['total'].mean().reset_index()
    student_progress = student_progress.sort_values(['student_id', 'semester'])
    
    # Calculate cumulative average correctly
    for student_id in student_progress['student_id'].unique():
        mask = student_progress['student_id'] == student_id
        student_progress.loc[mask, 'cumulative_avg'] = student_progress.loc[mask, 'total'].expanding().mean().values
    
    # Limit to first 10 students to avoid overcrowding
    top_student_ids = top_students['student_id'].tolist()[:10]
    filtered_progress = student_progress[student_progress['student_id'].isin(top_student_ids)]
    
    fig_progress = px.line(
        filtered_progress,
        x='semester',
        y='cumulative_avg',
        color='student_name',
        title='Student Progress Over Time',
        template='plotly_white'
    )
    fig_progress.update_layout(
        xaxis_title='Semester',
        yaxis_title='Cumulative Average',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    plots['progress'] = json.dumps(fig_progress, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Render template with all chart data
    return render_template('staff_dashboard.html',
                         staff=staff,
                         plots=plots,
                         network_path=network_path,
                         kpis={
                             'total_students': total_students,
                             'avg_cgpa': round(avg_cgpa, 2),
                             'attendance_rate': attendance_rate
                         })

@app.route('/api/refresh-stats', methods=['POST'])
def refresh_stats():
    """Endpoint for refreshing staff dashboard data based on semester selection."""
    semester = request.json.get('semester')
    if not semester:
        return jsonify({'error': 'Semester required'}), 400
        
    # Get all marks
    all_marks = Mark.query.all()
    
    # Create DataFrame for all marks with proper type conversion
    df = pd.DataFrame([{
        'student_id': str(m.student.id),
        'student_name': m.student.user.name,
        'subject': m.subject,
        'internal': float(m.internal),
        'external': float(m.external),
        'total': float(m.total),
        'semester': m.semester,
        'department': m.student.department
    } for m in all_marks])
    
    # Filter by semester if not 'all'
    if semester != 'all':
        df = df[df['semester'] == int(semester)]
    
    # ============= CHART 1: Subject Performance Distribution =============
    fig_subject = go.Figure()
    
    if not df.empty:
        fig_subject.add_trace(go.Box(
            y=df['total'],
            x=df['subject'],
            name='Marks Distribution',
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.8,
            marker_color='#3498db'
        ))
    
    semester_label = f"Semester {semester}" if semester != 'all' else "All Semesters"
    fig_subject.update_layout(
        title=f'{semester_label} - Subject Performance Distribution',
        xaxis_title='Subject',
        yaxis_title='Marks',
        template='plotly_white'
    )
    
    # ============= CHART 2: Top Performers =============
    top_students = df.groupby(['student_id', 'student_name'])['total'].mean().reset_index()
    top_students = top_students.nlargest(10, 'total')
    
    fig_top = go.Figure()
    
    if not top_students.empty:
        fig_top.add_trace(go.Bar(
            x=top_students['total'],
            y=top_students['student_name'],
            orientation='h',
            marker_color='#2ecc71',
            text=top_students['total'].round(2),
            textposition='auto'
        ))
    
    fig_top.update_layout(
        title=f'{semester_label} - Top 10 Performers',
        xaxis_title='Average Marks',
        yaxis_title='Student',
        template='plotly_white'
    )
    
    # ============= CHART 3: Student Performance Animation =============
    student_semester_avg = df.groupby(['student_id', 'student_name', 'semester'])['total'].mean().reset_index()
    
    # Use only top 15 students to avoid visual clutter
    top_student_ids = top_students['student_id'].tolist()[:15] if not top_students.empty else []
    student_semester_filtered = student_semester_avg[student_semester_avg['student_id'].isin(top_student_ids)] if top_student_ids else student_semester_avg
    
    fig_scatter = px.scatter(
        student_semester_filtered,
        x='semester',
        y='total',
        animation_frame='semester',
        animation_group='student_name',
        size='total',
        color='student_name',
        title=f'{semester_label} - Student Performance Animation',
        template='plotly_white'
    )
    fig_scatter.update_layout(
        xaxis_title='Semester',
        yaxis_title='Average Marks',
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 1000, "redraw": True},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    )
                ],
                direction="left",
                pad={"r": 10, "t": 87},
                showactive=True,
                x=0.1,
                xanchor="right",
                y=0,
                yanchor="top"
            )
        ]
    )
    
    # ============= CHART 4: Subject Performance Animation =============
    subject_semester_avg = df.groupby(['subject', 'semester'])['total'].mean().reset_index()
    
    fig_bar = px.bar(
        subject_semester_avg,
        x='subject',
        y='total',
        animation_frame='semester',
        color='subject',
        title=f'{semester_label} - Subject Performance Animation',
        template='plotly_white'
    )
    fig_bar.update_layout(
        xaxis_title='Subject',
        yaxis_title='Average Marks',
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 1000, "redraw": True},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "fromcurrent": True
                        }]
                    )
                ],
                direction="left",
                pad={"r": 10, "t": 87},
                showactive=True,
                x=0.1,
                xanchor="right",
                y=0,
                yanchor="top"
            )
        ]
    )
    
    # Prepare response with all chart data
    return jsonify({
        'avg_chart': json.dumps(fig_subject, cls=plotly.utils.PlotlyJSONEncoder),
        'top_chart': json.dumps(fig_top, cls=plotly.utils.PlotlyJSONEncoder),
        'animated_charts': {
            'scatter': json.dumps(fig_scatter, cls=plotly.utils.PlotlyJSONEncoder),
            'bar': json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder)
        }
    })

if __name__ == '__main__':
    app.run(debug=True)