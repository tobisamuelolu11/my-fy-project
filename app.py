from flask import Flask, render_template, request, jsonify, session
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import init_db, get_all_articles, create_user, verify_user, log_search, get_user_history, get_connection
import os
import random

app = Flask(__name__)
app.secret_key = 'scholorfind-secret-2024'

init_db()

def build_tfidf_model():
    articles = get_all_articles()
    if not articles:
        return None, None, None
    df = pd.DataFrame(articles)
    vec  = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
    mat  = vec.fit_transform(df['content'])
    return df, vec, mat

df, vectorizer, tfidf_matrix = build_tfidf_model()


def recommend_articles(query):
    if vectorizer is None:
        return []
    target = random.randint(10, 20)
    qv    = vectorizer.transform([query])
    sims  = cosine_similarity(qv, tfidf_matrix).flatten()
    # Sort all by score descending
    ranked = sims.argsort()[::-1]
    results = []
    for idx in ranked:
        score = sims[idx]
        if len(results) >= target:
            break
        # Always include up to target; stop early only if score is 0 and we have at least 10
        if score == 0 and len(results) >= 10:
            break
        a = df.iloc[idx]
        results.append({
            'title':    a['title'],
            'authors':  a['authors'],
            'journal':  a['journal'],
            'year':     int(a['year']),
            'keywords': a['keywords'],
            'abstract': a['abstract'],
            'url':      a.get('url', '') or '',
            'score':    round(float(score) * 100, 1)
        })
    return results


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/recommend', methods=['POST'])
def recommend():
    data  = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Please enter a research topic.'}), 400
    results = recommend_articles(query)
    if not results:
        return jsonify({'error': 'No relevant articles found. Try different keywords.'}), 404
    if 'user_id' in session:
        log_search(session['user_id'], query, len(results))
    return jsonify({'results': results, 'query': query})


@app.route('/register', methods=['POST'])
def register():
    data     = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
    if '@' not in email:
        return jsonify({'error': 'Enter a valid email address.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400
    ok, result = create_user(email, password)
    if not ok:
        return jsonify({'error': result}), 409
    session['user_id']      = result['id']
    session['email']        = result['email']
    session['display_name'] = result['display_name']
    return jsonify({'message': f"Welcome, {result['display_name']}!", 'user': result})


@app.route('/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()
    user = verify_user(email, password)
    if not user:
        return jsonify({'error': 'Incorrect email or password.'}), 401
    session['user_id']      = user['id']
    session['email']        = user['email']
    session['display_name'] = user['display_name']
    return jsonify({'message': f"Welcome back, {user['display_name']}!", 'user': user})


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out.'})


@app.route('/history/delete', methods=['POST'])
def delete_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in.'}), 401
    data  = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'No query provided.'}), 400
    conn = get_connection()
    conn.execute(
        "DELETE FROM search_history WHERE user_id = ? AND query = ?",
        (session['user_id'], query)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted.'})


@app.route('/history')
def history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in.'}), 401
    rows = get_user_history(session['user_id'])
    return jsonify({'history': rows})


@app.route('/me')
def me():
    if 'user_id' in session:
        return jsonify({
            'logged_in':    True,
            'email':        session.get('email'),
            'display_name': session.get('display_name')
        })
    return jsonify({'logged_in': False})


@app.route('/reload-model', methods=['POST'])
def reload_model():
    global df, vectorizer, tfidf_matrix
    df, vectorizer, tfidf_matrix = build_tfidf_model()
    count = len(df) if df is not None else 0
    return jsonify({'message': f'Model rebuilt with {count} articles.'})


@app.route('/stats')
def stats():
    return jsonify({'total_articles': len(get_all_articles())})


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def all_articles():
    arts = get_all_articles()
    return jsonify({'articles': arts, 'total': len(arts)})


@app.route('/browse')
def browse():
    """Return articles grouped by randomly chosen topics for the homepage."""
    import random
    articles = get_all_articles()
    if not articles:
        return jsonify({'groups': []})

    # Build topic -> articles map using the first keyword of each article
    topic_map = {}
    for a in articles:
        kws = [k.strip() for k in (a.get('keywords') or '').split(';') if k.strip()]
        topic = kws[0].title() if kws else (a.get('journal') or 'General')
        topic_map.setdefault(topic, []).append(a)

    # Pick up to 10 random topics
    topics = list(topic_map.keys())
    chosen = random.sample(topics, min(10, len(topics)))

    groups = []
    for topic in chosen:
        picks = random.sample(topic_map[topic], min(3, len(topic_map[topic])))
        groups.append({
            'topic': topic,
            'articles': [{
                'title':    a['title'],
                'authors':  a['authors'],
                'journal':  a['journal'],
                'year':     int(a['year']),
                'keywords': a['keywords'],
                'abstract': a['abstract'],
                'url':      a.get('url', '') or '',
            } for a in picks]
        })

    return jsonify({'groups': groups})


if __name__ == '__main__':
    app.run(debug=True)
