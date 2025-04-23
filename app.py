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

def create_animated_charts(marks_data, semester):
    # Create DataFrame for plotting
    df = pd.DataFrame(marks_data)
    
    # Animated scatter plot
    scatter_fig = px.scatter(
        df, 
        x="subject", 
        y="total", 
        animation_frame="semester", 
        animation_group="student", 
        size="total",
        color="subject",
        title=f"Student Performance Across Semesters"
    )
    
    # Add play/pause button with proper configuration
    scatter_fig.update_layout(
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
    
    # Animated bar chart with proper animation controls
    bar_fig = px.bar(
        df, 
        x="subject", 
        y="total", 
        animation_frame="semester",
        title=f"Subject Performance Across Semesters"
    )
    
    # Add play/pause button with proper configuration
    bar_fig.update_layout(
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
    
    return {
        'scatter': json.dumps(scatter_fig, cls=plotly.utils.PlotlyJSONEncoder),
        'bar': json.dumps(bar_fig, cls=plotly.utils.PlotlyJSONEncoder)
    }

def create_network_diagram():
    # Create a sample network (student-staff mentorship)
    net = Network(height="500px", width="100%", notebook=False)
    
    # Add nodes for students and staff
    students = Student.query.all()
    staff = User.query.filter_by(role='staff').all()
    
    # Add student nodes
    for student in students:
        net.add_node(
            str(student.id), 
            label=student.user.name, 
            title=f"Student: {student.user.name}<br>Reg No: {student.reg_no}<br>Department: {student.department}",
            color="#97c2fc"
        )
    
    # Add staff nodes
    for staff_member in staff:
        net.add_node(
            str(staff_member.id), 
            label=staff_member.name, 
            title=f"Staff: {staff_member.name}",
            color="#ff9999"
        )
    
    # Add edges (random mentorship for demonstration)
    for student in students:
        # Assign 1-2 random staff mentors to each student
        num_mentors = random.randint(1, 2)
        mentors = random.sample(staff, min(num_mentors, len(staff)))
        for mentor in mentors:
            net.add_edge(str(student.id), str(mentor.id), title="Mentor")
    
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
          "enabled": false
        }
      }
    }
    """)
    
    # Save to HTML file
    net.save_graph("static/network.html")
    
    return "static/network.html"

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
    server = Server({'/bokeh': create_bokeh_app()}, io_loop=IOLoop())
    server.start()
    server.io_loop.start()

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
    # Endpoint for student dashboard data refresh
    data = request.json
    semester = data.get('semester')
    student_id = data.get('student_id')
    
    if not semester or not student_id:
        return jsonify({'error': 'Semester and student_id required'}), 400
    
    # Get student
    student = Student.query.get_or_404(student_id)
    
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

@app.route('/dashboard/staff/<uuid:id>')
def staff_dashboard(id):
    staff = User.query.get_or_404(id)
    students = Student.query.all()
    
    # Create network diagram
    network_path = create_network_diagram()
    
    # Calculate department-wide KPIs
    all_marks = Mark.query.all()
    total_students = len(students)
    avg_cgpa = sum(m.total for m in all_marks) / (len(all_marks) * 100) * 10 if all_marks else 0
    attendance_rate = 95  # This should be calculated from actual attendance data
    
    # Create DataFrame for all marks
    df = pd.DataFrame([{
        'student': m.student.user.name,
        'subject': m.subject,
        'total': float(m.total),
        'semester': m.semester,
        'department': m.student.department
    } for m in all_marks])
    
    # 1. Department Performance Chart
    dept_performance = df.groupby('department')['total'].mean().reset_index()
    fig_dept = px.bar(
        dept_performance,
        x='department',
        y='total',
        title='Department Performance Overview',
        color='department',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_dept.update_layout(
        xaxis_title='Department',
        yaxis_title='Average Marks',
        template='plotly_white'
    )
    
    # 2. Subject Performance Distribution
    fig_subject = px.box(
        df,
        x='subject',
        y='total',
        title='Subject Performance Distribution',
        color='subject',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_subject.update_layout(
        xaxis_title='Subject',
        yaxis_title='Total Marks',
        template='plotly_white',
        showlegend=False
    )
    
    # 3. Top 5 Performers
    top_students = df.groupby('student')['total'].mean().nlargest(5).reset_index()
    fig_top = px.bar(
        top_students,
        x='total',
        y='student',
        orientation='h',
        title='Top 5 Performers',
        color='total',
        color_continuous_scale='Viridis'
    )
    fig_top.update_layout(
        xaxis_title='Average Marks',
        yaxis_title='Student',
        template='plotly_white'
    )
    
    # 4. Semester-wise Performance
    semester_perf = df.groupby('semester')['total'].mean().reset_index()
    fig_semester = px.line(
        semester_perf,
        x='semester',
        y='total',
        title='Semester-wise Performance Trend',
        markers=True
    )
    fig_semester.update_layout(
        xaxis_title='Semester',
        yaxis_title='Average Marks',
        template='plotly_white'
    )
    
    # 5. Subject Heatmap
    pivot_df = df.pivot_table(
        index='subject',
        columns='semester',
        values='total',
        aggfunc='mean'
    ).fillna(0)
    
    fig_heatmap = px.imshow(
        pivot_df,
        title='Subject Performance Heatmap',
        color_continuous_scale='RdYlGn'
    )
    fig_heatmap.update_layout(
        xaxis_title='Semester',
        yaxis_title='Subject',
        template='plotly_white'
    )
    
    # 6. Department-wise Subject Performance
    fig_radar = go.Figure()
    departments = df['department'].unique()
    subjects = df['subject'].unique()
    
    for dept in departments:
        dept_data = df[df['department'] == dept]
        dept_avg = dept_data.groupby('subject')['total'].mean()
        fig_radar.add_trace(go.Scatterpolar(
            r=dept_avg.values,
            theta=dept_avg.index,
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
    
    # 7. Animated Scatter Plot (Student Performance)
    fig_scatter = px.scatter(
        df,
        x='semester',
        y='total',
        animation_frame='semester',
        animation_group='student',
        size='total',
        color='subject',
        title='Student Performance Across Semesters'
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
    fig_bar = px.bar(
        df,
        x='subject',
        y='total',
        animation_frame='semester',
        title='Subject Performance Across Semesters'
    )
    fig_bar.update_layout(
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
    # Calculate cumulative average for each student across semesters
    student_progress = df.groupby(['student', 'semester'])['total'].mean().reset_index()
    student_progress = student_progress.sort_values(['student', 'semester'])
    student_progress['cumulative_avg'] = student_progress.groupby('student')['total'].transform('cumsum') / student_progress.groupby('student')['semester'].transform('count')
    
    fig_progress = px.line(
        student_progress,
        x='semester',
        y='cumulative_avg',
        color='student',
        title='Student Progress Over Time',
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
    
    # Prepare all plots
    plots = {
        'dept': json.dumps(fig_dept, cls=plotly.utils.PlotlyJSONEncoder),
        'subject': json.dumps(fig_subject, cls=plotly.utils.PlotlyJSONEncoder),
        'top': json.dumps(fig_top, cls=plotly.utils.PlotlyJSONEncoder),
        'semester': json.dumps(fig_semester, cls=plotly.utils.PlotlyJSONEncoder),
        'heatmap': json.dumps(fig_heatmap, cls=plotly.utils.PlotlyJSONEncoder),
        'radar': json.dumps(fig_radar, cls=plotly.utils.PlotlyJSONEncoder),
        'scatter': json.dumps(fig_scatter, cls=plotly.utils.PlotlyJSONEncoder),
        'bar': json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder),
        'progress': json.dumps(fig_progress, cls=plotly.utils.PlotlyJSONEncoder)
    }
    
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
    # Endpoint for staff dashboard data refresh
    semester = request.json.get('semester')
    if not semester:
        return jsonify({'error': 'Semester required'}), 400
        
    # Get all marks
    all_marks = Mark.query.all()
    
    # Create DataFrame for all marks
    df = pd.DataFrame([{
        'student': m.student.user.name,
        'subject': m.subject,
        'total': float(m.total),
        'semester': m.semester,
        'department': m.student.department
    } for m in all_marks])
    
    # Filter by semester if not 'all'
    if semester != 'all':
        df = df[df['semester'] == int(semester)]
    
    # Create animated charts
    charts = create_animated_charts(df.to_dict('records'), semester)
    
    # Average marks by subject
    avg_marks = df.groupby('subject')['total'].mean().reset_index()
    avg_fig = px.bar(avg_marks, x='subject', y='total',
                    title=f'Semester {semester} - Average Marks by Subject')
    
    # Top 5 performers
    top_students = df.groupby('student')['total'].mean().nlargest(5)
    top_fig = px.bar(top_students, orientation='h',
                    title=f'Semester {semester} - Top 5 Performers')
    
    return jsonify({
        'avg_chart': json.dumps(avg_fig, cls=plotly.utils.PlotlyJSONEncoder),
        'top_chart': json.dumps(top_fig, cls=plotly.utils.PlotlyJSONEncoder),
        'animated_charts': charts
    })

if __name__ == '__main__':
    app.run(debug=True) 