# PC Hardware Store 💻

Live demo: [pc-hardware-store.onrender.com](https://pc-hardware-store.onrender.com/)

A comprehensive CRUD (Create, Read, Update, Delete) web application designed for managing a PC hardware inventory. This project demonstrates a full-stack approach, combining a fast and modern backend API with a responsive, user-friendly frontend interface.

## 🚀 Features

*   **Full CRUD Operations:** Seamlessly add, view, edit, and delete hardware products from the database.
*   **Responsive UI:** Frontend designed with HTML5 and SCSS to ensure a clean experience across different devices.
*   **Dynamic Data Validation:** Client-side form validation built with JavaScript for instant feedback.
*   **Robust Database:** Persistent data storage configured with PostgreSQL.

## 🛠️ Tech Stack

**Backend:**
*   Python 3.10+
*   FastAPI
*   PostgreSQL

**Frontend:**
*   HTML5
*   SCSS
*   JavaScript (Vanilla)

**Deployment & Tools:**
*   Git / GitHub
*   Render (Cloud Hosting)

## ⚙️ Local Setup

To run this project locally, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Marcelcie/pc-hardware-store.git](https://github.com/Marcelcie/pc-hardware-store.git)
   cd pc-hardware-store
2. **Create and activate a virtual environment:**

Bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
Install dependencies:

Bash
pip install -r requirements.txt
3. **Set up the environment variables: **
Create a .env file in the root directory and add your PostgreSQL database connection string:

Fragment kodu
DATABASE_URL=postgresql://user:password@localhost/dbname
Run the application:

Bash
uvicorn main:app --reload
The API will be available at http://localhost:8000.
