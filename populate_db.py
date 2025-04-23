import random
from faker import Faker
from models import db, User, Student, Mark
from app import create_app
import uuid

fake = Faker('en_IN')  # Indian locale for names

# Engineering subjects by semester
SUBJECTS = {
    1: ['Engineering Mathematics I', 'Engineering Physics', 'Engineering Chemistry', 'Engineering Graphics', 'Basic Electrical Engineering', 'Programming in C'],
    2: ['Engineering Mathematics II', 'Environmental Science', 'Basic Electronics', 'Data Structures', 'Digital Systems', 'Object Oriented Programming'],
    3: ['Probability and Statistics', 'Database Management Systems', 'Computer Organization', 'Operating Systems', 'Theory of Computation', 'Web Technologies'],
    4: ['Discrete Mathematics', 'Computer Networks', 'Software Engineering', 'Design and Analysis of Algorithms', 'Microprocessors', 'Python Programming'],
    5: ['Artificial Intelligence', 'Machine Learning', 'Computer Graphics', 'Cloud Computing', 'Information Security', 'Big Data Analytics'],
    6: ['Deep Learning', 'Internet of Things', 'Mobile Computing', 'Compiler Design', 'Distributed Systems', 'Natural Language Processing'],
    7: ['Data Mining', 'Blockchain Technology', 'Quantum Computing', 'Robotics', 'Virtual Reality', 'Network Security'],
    8: ['Edge Computing', 'DevOps', 'Green Computing', 'High Performance Computing', 'Software Testing', 'Project Management']
}

DEPARTMENTS = ['Computer Science', 'Information Technology', 'Electronics', 'Mechanical', 'Civil']

def generate_marks():
    internal = random.randint(40, 50)
    external = random.randint(40, 50)
    return internal, external, internal + external

def calculate_gpa(marks):
    if not marks:
        return 0.0
    total = sum(mark.total for mark in marks)
    max_possible = len(marks) * 100
    gpa = (total / max_possible) * 10
    return min(round(gpa, 2), 9.99)

def populate_db(num_students=20):
    app = create_app()
    with app.app_context():
        # Clear existing data
        Mark.query.delete()
        Student.query.delete()
        User.query.delete()
        db.session.commit()

        # Generate students
        for _ in range(num_students):
            # Create user
            user = User(
                id=uuid.uuid4(),
                name=fake.name(),
                role='student'
            )
            db.session.add(user)
            db.session.flush()

            # Create student
            student = Student(
                id=uuid.uuid4(),
                user_id=user.id,
                reg_no=f'2024{fake.unique.random_number(digits=4)}',
                department=random.choice(DEPARTMENTS),
                semester=random.randint(1, 8),
                attendance=round(random.uniform(75, 100), 2)
            )
            db.session.add(student)
            db.session.flush()

            # Generate marks for each semester
            all_semester_marks = []
            for sem in range(1, 9):
                semester_marks = []
                for subject in SUBJECTS[sem]:
                    # 15% chance of missing mark entry
                    if random.random() > 0.15:
                        internal, external, total = generate_marks()
                        mark = Mark(
                            id=uuid.uuid4(),
                            student_id=student.id,
                            semester=sem,
                            subject=subject,
                            internal=internal,
                            external=external,
                            total=total
                        )
                        db.session.add(mark)
                        semester_marks.append(mark)
                all_semester_marks.extend(semester_marks)
                
                # Calculate and update CGPA
                student.cgpa = calculate_gpa(all_semester_marks)
            
        # Create staff users
        for _ in range(5):
            staff = User(
                id=uuid.uuid4(),
                name=f"Prof. {fake.name()}",
                role='staff'
            )
            db.session.add(staff)

        db.session.commit()

if __name__ == '__main__':
    num = input("How many students to generate? [default=20]: ")
    try:
        num = int(num)
    except (ValueError, TypeError):
        num = 20
    populate_db(num) 