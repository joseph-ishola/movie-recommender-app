import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_secret(secret_name):
    secret_file = f"/run/secrets/{secret_name}"
    if os.path.exists(secret_file):
        with open(secret_file, 'r') as f:
            return f.read().strip()
    return os.getenv(secret_name.upper().replace('-', '_'), '')

class Database:
    """Database connection utility for the movie recommendation system"""
    
    def __init__(self):
        self.conn_params = {
            'dbname': os.getenv('DB_NAME', 'movie_recommender'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': get_secret('db_password'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432')
        }
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to the PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False
            
    def disconnect(self):
        """Close the database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    def execute(self, query, params=None, commit=False):
        """Execute a query and optionally commit the transaction"""
        try:
            self.cursor.execute(query, params or ())
            if commit:
                self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error executing query: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            return False
            
    def fetchall(self):
        """Fetch all results from the last query"""
        return self.cursor.fetchall()
        
    def fetchone(self):
        """Fetch one result from the last query"""
        return self.cursor.fetchone()
        
    def get_movie_by_title(self, title):
        """Get a movie by its title (case insensitive)"""
        query = "SELECT * FROM movies WHERE LOWER(title) = LOWER(%s)"
        self.execute(query, (title,))
        return self.fetchone()
        
    def get_movies_by_partial_title(self, partial_title):
        """Get movies that contain the partial title"""
        query = "SELECT * FROM movies WHERE LOWER(title) LIKE LOWER(%s) LIMIT 5"
        self.execute(query, (f'%{partial_title}%',))
        return self.fetchall()
        
    def get_similar_movies(self, movie_id, limit=5):
        """Get the most similar movies for a given movie ID"""
        query = """
        SELECT m.*, ms.similarity_score
        FROM movie_similarities ms
        JOIN movies m ON ms.target_movie_id = m.movie_id
        WHERE ms.source_movie_id = %s
        ORDER BY ms.similarity_score DESC
        LIMIT %s
        """
        self.execute(query, (movie_id, limit))
        return self.fetchall()
        
    def store_movie_similarity(self, source_id, target_id, score):
        """Store a similarity score between two movies"""
        query = """
        INSERT INTO movie_similarities (source_movie_id, target_movie_id, similarity_score)
        VALUES (%s, %s, %s)
        ON CONFLICT (source_movie_id, target_movie_id) 
        DO UPDATE SET similarity_score = %s
        """
        return self.execute(query, (source_id, target_id, score, score), commit=True)
        
    def get_visualization(self, movie_id, viz_type):
        """Get a stored visualization for a movie"""
        query = """
        SELECT * FROM visualizations
        WHERE movie_id = %s AND visualization_type = %s
        """
        self.execute(query, (movie_id, viz_type))
        return self.fetchone()
        
    def store_visualization(self, movie_id, viz_type, image_data):
        """Store a visualization image for a movie"""
        query = """
        INSERT INTO visualizations (movie_id, visualization_type, image_data)
        VALUES (%s, %s, %s)
        ON CONFLICT (movie_id, visualization_type) 
        DO UPDATE SET image_data = image_data = EXCLUDED.image_data, created_at = CURRENT_TIMESTAMP
        """
        return self.execute(query, (movie_id, viz_type, psycopg2.Binary(image_data), 
                                   psycopg2.Binary(image_data)), commit=True)