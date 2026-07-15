# ISE-HUB

ISE-HUB is a Flask-based web application developed as a **college mini project** for the Department of Information Science and Engineering. The application serves as a centralized platform for students, faculty, and administrators to manage academic activities efficiently.

> **Note:** This project was developed as a **collaborative academic project** as part of our college curriculum.

---

## Features

### Student Module
- Secure student login
- View study materials
- Access assignments
- Submit assignment files
- View attendance
- View internal marks
- View notifications
- Student profile

### Faculty Module
- Faculty login
- View assigned students
- Update attendance
- Update internal marks
- Upload study materials

### Admin Module
- Admin dashboard
- Manage students
- Upload assignments
- View student submissions
- Upload study materials
- Manage notifications
- Manage attendance
- Manage internal marks

---

## Technologies Used

- Python
- Flask
- HTML5
- CSS3
- JavaScript
- JSON (Data Storage)

---

## Project Structure

```
ISE-HUB/
│
├── app.py
├── data/
├── static/
│   ├── css/
│   └── js/
├── templates/
├── uploads/
└── README.md
```

---

## Installation

1. Clone the repository

```bash
git clone https://github.com/Jaishree-jusy/ISE-HUB.git
```

2. Navigate to the project

```bash
cd ISE-HUB
```

3. Install dependencies

```bash
pip install flask
```

4. Run the application

```bash
python app.py
```

5. Open your browser

```
http://127.0.0.1:5000
```

---

## Login Credentials

### Admin

- **Username:** `admin`
- **Password:** `123`

### Student

Students can log in using their **USN** or **registered email** along with their password.

### Faculty

Faculty members can log in using their assigned username and password.

---

## Educational Purpose

This project was developed solely for **academic and learning purposes** as part of our college mini project. It demonstrates the implementation of role-based authentication, file management, and basic academic portal functionalities using the Flask framework.

---

## Future Enhancements

- Database integration (MySQL/MongoDB)
- Password encryption
- Email notifications
- Student performance analytics
- Responsive mobile interface
- Cloud deployment

---

## Contributors

- **Jaishree K S**
- **Adithya K** 

---

## License

This repository is intended for **educational purposes only**.
