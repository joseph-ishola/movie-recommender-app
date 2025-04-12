from flask import Flask, request, jsonify, send_file
from db_utils import Database
from cache_utils import RedisCache
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import io
import psycopg2
import os
import json
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure application
app.config['CACHE_ENABLED'] = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

@app.route('/api/status', methods=['GET'])
def status():
    """Check API status"""
    # Test database connection
    db_status = False
    with Database() as db:
        db_status = db.connect()
    
    # Test cache connection if enabled
    cache_status = True
    if app.config['CACHE_ENABLED']:
        with RedisCache() as cache:
            cache_status = cache.connect()
    
    return jsonify({
        'status': 'ok',
        'database': 'connected' if db_status else 'disconnected',
        'cache': 'connected' if cache_status else 'disconnected',
        'cache_enabled': app.config['CACHE_ENABLED']
    })

@app.route('/api/search', methods=['GET', 'POST'])
def search_movies():
    """Search for movies by title"""
    # Handle both GET and POST requests
    if request.method == 'POST':
        query = request.form.get('movie_title', '').strip()
    else:
        query = request.args.get('q', '').strip()
    
    app.logger.info(f"Searching for movie: '{query}'")

    if not query:
        return jsonify({
            'status': 'error',
            'message': 'Search query is required'
        }), 400
    
    with Database() as db:
        # Check for exact matches (could be multiple)
        db.execute("SELECT * FROM movies WHERE LOWER(title) = LOWER(%s)", (query,))
        exact_matches = db.fetchall()
        
        app.logger.info(f"Found {len(exact_matches)} exact matches for '{query}'")

        if exact_matches:
            # If there's only one exact match, return it as an exact match
            if len(exact_matches) == 1:
                app.logger.info(f"Returning single exact match: {exact_matches[0]['title']}")
                return jsonify({
                    'status': 'success',
                    'exact_match': True,
                    'movie': exact_matches[0]
                })
            else:
                # If there are multiple exact matches, return them as multiple matches
                app.logger.info(f"Returning {len(exact_matches)} exact matches as similar_movies")
                return jsonify({
                    'status': 'success',
                    'exact_match': False,
                    'similar_movies': exact_matches
                })
        
        # If no exact match, try partial match
        db.execute("SELECT * FROM movies WHERE LOWER(title) LIKE LOWER(%s) LIMIT 10", (f'%{query}%',))
        similar_movies = db.fetchall()
        
        app.logger.info(f"Found {len(similar_movies)} partial matches for '{query}'")

        if similar_movies:
            return jsonify({
                'status': 'success',
                'exact_match': False,
                'similar_movies': similar_movies
            })
        
        # No matches found
        return jsonify({
            'status': 'success',
            'exact_match': False,
            'similar_movies': []
        })

@app.route('/api/recommendations/<int:movie_id>', methods=['GET'])
def get_recommendations(movie_id):
    """Get movie recommendations based on movie ID"""
    limit = int(request.args.get('limit', 5))
    
    try:
        # First, get the source movie regardless of cache status
        with Database() as db:
            # Check if the movie exists
            db.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
            source_movie = db.fetchone()
            
            if not source_movie:
                app.logger.error(f"Movie with ID {movie_id} not found")
                return jsonify({
                    'status': 'error',
                    'message': f'Movie with ID {movie_id} not found'
                }), 404
        
        # Now check cache for recommendations
        recommendations = None
        if app.config['CACHE_ENABLED']:
            with RedisCache() as cache:
                cached_recs = cache.get_recommendations(movie_id)
                if cached_recs:
                    app.logger.info(f"Cache hit for recommendations of movie {movie_id}")
                    # Filter to requested limit
                    recommendations = cached_recs[:limit]
        
        # If not in cache, get from database
        if recommendations is None:
            with Database() as db:
                # Log the query we're about to execute
                app.logger.info(f"Fetching recommendations for movie_id: {movie_id}")
                
                # Get recommendations
                recommendations = db.get_similar_movies(movie_id, limit)
                
                # Log how many recommendations we found
                app.logger.info(f"Found {len(recommendations)} recommendations for movie_id: {movie_id}")

                # Store in cache if enabled
                if app.config['CACHE_ENABLED'] and recommendations:
                    with RedisCache() as cache:
                        cache.set_recommendations(movie_id, recommendations)
        
        if not recommendations:
            app.logger.warning(f"No recommendations found for movie ID {movie_id}")
            return jsonify({
                'status': 'error',
                'message': f'No recommendations found for movie ID {movie_id}'
            }), 404
        
        # Calculate evaluation metrics - now source_movie is always defined
        metrics = calculate_evaluation_metrics(source_movie, recommendations)

        return jsonify({
            'status': 'success',
            'movie_id': movie_id,
            'source_movie': source_movie,
            'recommendations': recommendations,
            'metrics': metrics
        })
    
    except Exception as e:
        app.logger.error(f"Error generating recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/visualization/<string:viz_type>/<int:movie_id>', methods=['GET'])
def get_visualization(viz_type, movie_id):
    """Get visualization for a movie (similarity chart or wordcloud)"""
    if viz_type not in ['similarity_chart', 'wordcloud']:
        return jsonify({
            'status': 'error',
            'message': f'Invalid visualization type: {viz_type}'
        }), 400
    
    try:
        # Check Redis cache first if enabled
        image_data = None
        if app.config.get('CACHE_ENABLED', True):
            with RedisCache() as cache:
                if cache.client:
                    cached_viz = cache.get_visualization(movie_id, viz_type)
                    if cached_viz:
                        app.logger.info(f"Redis cache hit for {viz_type} of movie {movie_id}")
                        image_data = cached_viz
        
        # If not in Redis, check database
        if image_data is None:
            with Database() as db:
                db.execute("""
                    SELECT image_data FROM visualizations
                    WHERE movie_id = %s AND visualization_type = %s
                """, (movie_id, viz_type))
                
                viz_record = db.fetchone()
                
                if viz_record and viz_record['image_data']:
                    app.logger.info(f"Database cache hit for {viz_type} of movie {movie_id}")
                    image_data = viz_record['image_data']
                    
                    # Store in Redis for future faster access
                    if app.config.get('CACHE_ENABLED', True):
                        with RedisCache() as cache:
                            if cache.client:
                                cache.set_visualization(movie_id, viz_type, image_data)
        
        # If still not found, generate the visualization
        if image_data is None:
            app.logger.info(f"Generating {viz_type} for movie {movie_id}")
            
            # Get the movie and its recommendations
            with Database() as db:
                # First check if the movie exists
                db.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
                movie = db.fetchone()
                
                if not movie:
                    return jsonify({
                        'status': 'error',
                        'message': f'Movie with ID {movie_id} not found'
                    }), 404
                
                # Get recommendations
                db.execute("""
                    SELECT m.*, ms.similarity_score
                    FROM movie_similarities ms
                    JOIN movies m ON ms.target_movie_id = m.movie_id
                    WHERE ms.source_movie_id = %s
                    ORDER BY ms.similarity_score DESC
                    LIMIT 5
                """, (movie_id,))
                
                recommendations = db.fetchall()
                
                if not recommendations:
                    return jsonify({
                        'status': 'error',
                        'message': f'No recommendations found for movie ID {movie_id}'
                    }), 404
                
                # Generate visualization
                if viz_type == 'similarity_chart':
                    image_data = generate_similarity_chart(movie, recommendations)
                else:  # wordcloud
                    image_data = generate_wordcloud(movie, recommendations)
                
                # Store visualization in database
                try:
                    db.execute("""
                        INSERT INTO visualizations (movie_id, visualization_type, image_data)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (movie_id, visualization_type) 
                        DO UPDATE SET image_data = EXCLUDED.image_data, created_at = CURRENT_TIMESTAMP
                    """, (movie_id, viz_type, psycopg2.Binary(image_data)))
                    
                    db.conn.commit()
                    app.logger.info(f"Stored {viz_type} visualization in database for movie {movie_id}")
                    
                    # Also cache in Redis
                    if app.config.get('CACHE_ENABLED', True):
                        with RedisCache() as cache:
                            if cache.client:
                                cache.set_visualization(movie_id, viz_type, image_data)
                                app.logger.info(f"Cached {viz_type} visualization in Redis for movie {movie_id}")
                except Exception as e:
                    app.logger.error(f"Error storing visualization: {str(e)}")
                    # Continue even if storage fails - we can still return the generated image
        
        # Return the visualization
        return send_file(
            io.BytesIO(image_data),
            mimetype='image/png',
            as_attachment=False
        )
            
    except Exception as e:
        app.logger.error(f"Error generating visualization: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Error generating visualization: {str(e)}'
        }), 500

def generate_similarity_chart(movie, recommendations):
    """Generate a similarity chart for a movie and its recommendations"""
    plt.figure(figsize=(12, 8))
    
    # Extract titles and scores
    titles = [rec['title'] for rec in recommendations]
    scores = [rec['similarity_score'] for rec in recommendations]
    
    # Check if we have valid data
    if not titles or not scores:
        plt.text(0.5, 0.5, "No similarity data available", 
                 horizontalalignment='center', verticalalignment='center', 
                 fontsize=20, color='gray')
        plt.axis('off')
    else:
        # Create the chart with bright colors and clear labels
        bars = plt.barh(titles, scores, color='#4299e1')
        
        # Add percentage labels to the bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            label_position = width - 0.05  # Position label inside the bar
            plt.text(label_position, bar.get_y() + bar.get_height()/2, 
                    f'{width:.1%}', va='center', ha='right', color='white', fontweight='bold', fontsize=14)
        
        plt.xlabel('Similarity Score', fontsize=18)
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=16)
        plt.ylabel('Movie Title', fontsize=18)
        plt.title(f'Movies Similar to "{movie["title"]}"', fontsize=20, fontweight='bold')
        plt.xlim(0, 1.0)  # Set x-axis from 0 to 1
        plt.gca().invert_yaxis()  # Highest similarity at top
        plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    # Save to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close()
    
    buf.seek(0)
    return buf.getvalue()

def generate_wordcloud(movie, recommendations):
    """Generate a wordcloud for a movie and its recommendations"""
    # Combine overviews, filtering out empty or "No overview found" placeholders
    overviews = []
    if movie['overview'] and not movie['overview'].lower().strip() == "no overview found":
        overviews.append(movie['overview'])
    
    for rec in recommendations:
        if rec['overview'] and not rec['overview'].lower().strip() == "no overview found":
            overviews.append(rec['overview'])
    
    combined_text = ' '.join(overviews)
    
    if not combined_text.strip():
        # If no real text available, return an informative image
        plt.figure(figsize=(10, 7))
        plt.text(0.5, 0.5, "No meaningful text available for wordcloud", 
                 horizontalalignment='center', verticalalignment='center', 
                 fontsize=20, color='gray')
        plt.axis('off')
    else:
        # Create the wordcloud with better settings
        wordcloud = WordCloud(
            width=800,
            height=500,
            background_color='white',
            max_words=200,  
            contour_width=3,
            contour_color='steelblue',
            collocations=False,  # Avoid repeating word pairs
            random_state=42  # For reproducibility
        ).generate(combined_text)
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
    
    plt.tight_layout()
    
    # Save to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close()
    
    buf.seek(0)
    return buf.getvalue()

def calculate_evaluation_metrics(source_movie, recommendations):
    """Calculate evaluation metrics for recommendations"""
    # 1. Calculate genre overlap
    try:
        source_genres = json.loads(source_movie['genres']) if isinstance(source_movie['genres'], str) else source_movie['genres']
        source_genre_names = [g['name'] for g in source_genres]
        
        genre_overlaps = []
        for rec in recommendations:
            rec_genres = json.loads(rec['genres']) if isinstance(rec['genres'], str) else rec['genres']
            rec_genre_names = [g['name'] for g in rec_genres]
            
            # Calculate Jaccard similarity for genres
            if source_genre_names and rec_genre_names:
                overlap = len(set(source_genre_names) & set(rec_genre_names)) / len(set(source_genre_names) | set(rec_genre_names))
            else:
                overlap = 0
                
            genre_overlaps.append(overlap)
            
        avg_genre_overlap = sum(genre_overlaps) / len(genre_overlaps) if genre_overlaps else 0
        
        # 2. Calculate rating difference
        source_rating = float(source_movie['vote_average']) if source_movie['vote_average'] is not None else 0
        rating_diffs = []
        
        for rec in recommendations:
            rec_rating = float(rec['vote_average']) if rec['vote_average'] is not None else 0
            rating_diffs.append(abs(source_rating - rec_rating))
            
        avg_rating_diff = sum(rating_diffs) / len(rating_diffs) if rating_diffs else 0
        
        # 3. Calculate content relevance using TF-IDF + Cosine Similarity based on genres
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Create genre feature strings
        source_genre_feature = ' '.join(source_genre_names)
        rec_genre_features = [' '.join([g['name'] for g in (json.loads(rec['genres']) if isinstance(rec['genres'], str) else rec['genres'])]) for rec in recommendations]
        
        # Combine all genre features for TF-IDF
        all_genre_features = [source_genre_feature] + rec_genre_features
        
        # Check if we have valid genre data
        if any(all_genre_features) and len(all_genre_features) > 1:
            # Fit TF-IDF vectorizer on all genre features
            tfidf = TfidfVectorizer(stop_words='english')
            tfidf_matrix = tfidf.fit_transform(all_genre_features)
            
            # Get similarity between source movie and each recommendation
            source_vector = tfidf_matrix[0:1]
            rec_vectors = tfidf_matrix[1:]
            
            content_similarities = cosine_similarity(source_vector, rec_vectors)[0]
            avg_content_relevance = sum(content_similarities) / len(content_similarities) if len(content_similarities) > 0 else 0
        else:
            avg_content_relevance = 0
        
        return {
            'average_genre_overlap': avg_genre_overlap * 100,  # Convert to percentage
            'average_rating_difference': avg_rating_diff,
            'average_content_relevance': avg_content_relevance * 100  # Convert to percentage
        }
    except Exception as e:
        app.logger.error(f"Error calculating metrics: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'average_genre_overlap': 0,
            'average_rating_difference': 0,
            'average_content_relevance': 0
        }

@app.route('/api/clear-visualization-cache', methods=['POST'])
def clear_visualization_cache():
    """Admin endpoint to clear all visualization caches"""
    try:
        # Clear database cache
        with Database() as db:
            db.execute("DELETE FROM visualizations")
            db.conn.commit()
            
        # Clear Redis cache if enabled
        if app.config.get('CACHE_ENABLED', True):
            with RedisCache() as cache:
                if cache.client:
                    # Delete all keys matching viz:*
                    keys = cache.client.keys("viz:*")
                    if keys:
                        cache.client.delete(*keys)
        
        return jsonify({
            'status': 'success',
            'message': 'Visualization cache cleared successfully'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error clearing cache: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    )