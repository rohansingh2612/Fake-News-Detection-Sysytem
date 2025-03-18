# Fake News Detection System

## Overview
The **Fake News Detection System** is a web-based application that uses machine learning to classify news articles as either **Fake** or **Real**. It provides users with an intuitive interface to check the authenticity of news articles by entering their URLs. The system also includes features like user authentication, prediction history, and a comments section for user feedback.

---

## Features
1. **User Authentication**:
   - Users can register, log in, and log out securely.
   - Passwords are hashed for security.

2. **Fake News Prediction**:
   - Users can input a news article URL to check its authenticity.
   - The system uses a trained machine learning model to classify the news.

3. **Prediction History**:
   - Logged-in users can view their prediction history, including URLs, outcomes, and timestamps.

4. **Comments Section**:
   - Users can leave comments and feedback on the platform.

5. **Responsive Design**:
   - The application is mobile-friendly and adapts to various screen sizes.

---

## Architecture
The system is built using the following components:

### 1. **Frontend**:
   - HTML, CSS, and JavaScript are used for the user interface.
   - Templates are rendered using Flask's Jinja2 templating engine.

### 2. **Backend**:
   - Flask is used as the web framework.
   - MySQL is used as the database for storing user data, prediction history, and comments.

### 3. **Machine Learning**:
   - A **Passive Aggressive Classifier** is trained using the **TF-IDF Vectorizer** to classify news articles.
   - The model is saved and loaded using `pickle`.

### 4. **APIs**:
   - **NewsAPI** is used to fetch top news headlines for the homepage.

---

## Workflow Diagram
Below is the workflow of the system:

```plaintext
User -> [Frontend (HTML/CSS/JS)] -> [Flask Backend] -> [MySQL Database]
     -> [Prediction Request] -> [Machine Learning Model] -> [Prediction Result]
```

---

## Database Schema
### 1. **Users Table**:
   - `id`: Primary key.
   - `email`: User's email.
   - `username`: User's username.
   - `password_hash`: Hashed password.

### 2. **History Table**:
   - `id`: Primary key.
   - `historyURL`: URL of the news article.
   - `historyLabel`: Prediction result (Fake/Real).
   - `userID`: Foreign key referencing the `Users` table.
   - `historyDate`: Timestamp of the prediction.

### 3. **Comments Table**:
   - `id`: Primary key.
   - `userID`: Foreign key referencing the `Users` table.
   - `commentText`: User's comment.
   - `commentDate`: Timestamp of the comment.

---

## Machine Learning Model
### 1. **Dataset**:
   - The model is trained on a dataset of news articles labeled as **Fake** or **Real**.

### 2. **Preprocessing**:
   - Text data is vectorized using **TF-IDF Vectorizer**.

### 3. **Classifier**:
   - A **Passive Aggressive Classifier** is used for training and prediction.

### 4. **Performance**:
   - Accuracy: ~90%
   - K-Fold Cross-Validation Accuracy: ~88%

### Confusion Matrix:
[image](https://github.com/user-attachments/assets/6ad8a1fe-8db8-412d-a94e-d73a6f16b5ab)
)

---

## Installation and Setup
### Prerequisites:
- Python 3.8+
- MySQL
- Flask

### Steps:
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/Fake-News-Detection-System.git
   cd Fake-News-Detection-System
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   - Import the provided SQL schema into MySQL.
   - Update the database credentials in `config.py`.

4. Train the model (optional):
   ```bash
   python model.py
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Access the application at:
   ```
   http://127.0.0.1:5000
   ```

---

## Usage
1. **Register**:
   - Create an account to access all features.

2. **Login**:
   - Log in to view prediction history and leave comments.

3. **Predict**:
   - Enter a news article URL to check its authenticity.

4. **View History**:
   - Access your prediction history.

5. **Leave Comments**:
   - Share feedback or discuss with other users.

---

## Screenshots
### 1. **Homepage**:
![image](https://github.com/user-attachments/assets/c3f4eb51-b5ce-4fa4-8d88-fd1d37dfb654)

### 2. **Prediction Result**:
![image](https://github.com/user-attachments/assets/ca30b9fb-d39c-4dfe-80fd-eff9c2718d9f)

![image](https://github.com/user-attachments/assets/84904a32-5b51-48ae-aaaa-1d039fa98bbf)

### 3. **History Page**:
![image](https://github.com/user-attachments/assets/c36bfa6f-60b8-4b54-8aa0-5d8e28ed9afe)

---

## Future Enhancements
1. Support for multiple languages.
2. Integration with more news APIs.
3. Advanced analytics for user predictions.
4. Improved UI/UX design.

---

## Contributors
- **Rohan** - Developer

---

## License
This project is licensed under the MIT License. See the [`LICENSE`](https://github.com/rohansingh2612/Fake-News-Detection-Sysytem/blob/main/LICENSE)
 file for details.
