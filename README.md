# Academia – Academic Journal Recommender System
### Undergraduate Project – Oloruntobi

---

## Project Overview
An intelligent information system that recommends academic journals and research articles
based on user input, using **TF-IDF vectorization** and **Cosine Similarity**.

---

## Project Structure
```
journal_recommender/
│
├── app.py                  ← Flask backend (recommendation engine)
├── articles.csv|api        ← Dataset of 25 academic articles | semantic scholar & arxiv api
├── requirements.txt        ← Python dependencies
├── README.md               ← This file
│
└── templates/
    └── html/css/JS         ← Frontend UI
```

---

## How the Recommendation Works
1. All article titles, keywords, and abstracts are combined into a single text field
2. **TF-IDF** converts all article texts into numerical vectors
3. When a user enters a query, it is also converted into a vector using the same TF-IDF model
4. **Cosine Similarity** measures the angle between the query vector and each article vector
5. Articles are ranked by similarity score and the top results are returned

**Cosine Similarity Formula:**
```
similarity(A, B) = (A · B) / (||A|| × ||B||)
```

---

## Setup & Installation

### Step 1: Install Python
Make sure Python 3.8 or higher is installed on your computer.
Download from: https://www.python.org/downloads/

### Step 2: Install Required Libraries
Open your terminal/command prompt, navigate to the project folder, then run:
```bash
pip install -r requirements.txt
```

### Step 3: Run the Application
```bash
python app.py
```

### Step 4: Open in Browser
Go to: **http://127.0.0.1:5000**

---

## How to Use
1. Open the app in your browser
2. Type a research topic (e.g., "machine learning healthcare")
3. Click **Search** or press **Enter**
4. View recommended articles with relevance scores

---

## Technologies Used
| Component       | Technology              |
|----------------|-------------------------|
| Backend         | Python, Flask           |
| Recommendation  | Scikit-learn (TF-IDF)   |
| Similarity      | Cosine Similarity       |
| Frontend        | HTML, CSS, JavaScript   |
| Dataset         | CSV (25 articles) + api |

---

## API Endpoints
| Endpoint       | Method | Description                        |
|----------------|--------|------------------------------------|
| `/`            | GET    | Loads the main UI                  |
| `/recommend`   | POST   | Returns recommendations for query  |
| `/articles`    | GET    | Returns all articles in dataset    |

---

## Future Improvements
- Add more articles to the dataset
- Implement user login and preference saving
- Add collaborative filtering
- Connect to live APIs (Semantic Scholar, arXiv)
## Future Improvements all added