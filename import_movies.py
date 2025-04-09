import pandas as pd
import numpy as np
import ast
import json
import os
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import hstack, csr_matrix
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from db_utils import Database
import time
import psycopg2.extras

def preprocess_movie_data(csv_path):
    """Process the movie data CSV file and prepare it for database import"""
    print(f"Loading data from {csv_path}...")
    movies_df = pd.read_csv(csv_path, low_memory=False)
    
    # Clean text fields to remove problematic characters
    movies_df['title'] = movies_df['title'].apply(
        lambda x: str(x).replace('\r', ' ').replace('\n', ' ').strip() if pd.notnull(x) else '')
    
    movies_df['overview'] = movies_df['overview'].apply(
        lambda x: str(x).replace('\r', ' ').replace('\n', ' ').strip() if pd.notnull(x) else '')

    # Convert string representations to Python objects
    movies_df['genres'] = movies_df['genres'].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else []
    )
    
    # Extract collection names
    def extract_collection_name(x):
        if pd.isna(x) or x == "" or x == "NaN":
            return None
        try:
            data = ast.literal_eval(x)
            return data.get("name", None)
        except Exception:
            return None
            
    movies_df['collection_name'] = movies_df['belongs_to_collection'].apply(extract_collection_name)
    
    # Convert genres to a more database-friendly format
    movies_df['genres_json'] = movies_df['genres'].apply(lambda x: json.dumps(x))
    
    # Fill NaN values in overview
    movies_df['overview'] = movies_df['overview'].fillna("")
    
    # Select and rename columns for the database
    db_movies = movies_df[[
        'id', 'title', 'release_date', 'overview', 'vote_average',
        'budget', 'revenue', 'runtime', 'collection_name', 'genres_json'
    ]].copy()
    
    db_movies.rename(columns={
        'id': 'tmdb_id',
        'genres_json': 'genres'
    }, inplace=True)
    
    # Handle numerical features
    for col in ['budget', 'revenue', 'runtime']:
        db_movies[col] = pd.to_numeric(db_movies[col], errors='coerce')
        # Replace 0s with NaN
        db_movies[col] = db_movies[col].replace(0, np.nan)
    
    # Parse release dates
    db_movies['release_date'] = pd.to_datetime(db_movies['release_date'], errors='coerce')

    # Convert NaT values to None (will become NULL in PostgreSQL)
    db_movies['release_date'] = db_movies['release_date'].astype(object).where(~db_movies['release_date'].isna(), None)

    
    print(f"Processed {len(db_movies)} movies.")
    return db_movies, movies_df

def compute_movie_similarities(movies_df, batch_size=100):
    """Compute and store movie similarities in batches"""
    
    print("Starting similarity computation...")
    start_time = time.time()
    
    # First, get the list of movie IDs that were successfully imported into the database
    with Database() as db:
        db.execute("SELECT movie_id, tmdb_id FROM movies")
        valid_movies = {row['tmdb_id']: row['movie_id'] for row in db.fetchall()}
        
        if not valid_movies:
            print("No movies found in database. Please import movies first.")
            return
            
        print(f"Found {len(valid_movies)} valid movies in database.")
    
    # Make sure IDs are comparable between dataframe and database
    # Ensure tmdb_id in movies_df is integer type to match database
    movies_df['id'] = pd.to_numeric(movies_df['id'], errors='coerce').fillna(0).astype(int)
    
    # Debug: Print some IDs from both sources to diagnose the mismatch
    print("Sample tmdb_ids from database:", list(valid_movies.keys())[:5])
    print("Sample ids from dataframe:", list(movies_df['id'].iloc[:5]))
    
    # Filter the movies_df to only include movies that exist in the database
    valid_movies_df = movies_df[movies_df['id'].isin(valid_movies.keys())].copy()
    print(f"Using {len(valid_movies_df)} movies for similarity computation.")
    
    # If we still have no matches, try a more lenient approach
    if len(valid_movies_df) == 0:
        print("No matches found with exact ID matching. Trying alternative approach...")
        # Create a set of all tmdb_ids in the database
        db_tmdb_ids = set(valid_movies.keys())
        
        # Create a set of all ids in the dataframe
        df_ids = set(movies_df['id'].astype(int).values)
        
        # Show the intersection
        common_ids = db_tmdb_ids.intersection(df_ids)
        print(f"Found {len(common_ids)} common IDs between database and dataframe.")
        
        if len(common_ids) == 0:
            print("ERROR: No common IDs found. Cannot compute similarities.")
            print("Database may have used a different ID field than expected.")
            return
        
        # Use the common IDs
        valid_movies_df = movies_df[movies_df['id'].isin(common_ids)].copy()
        print(f"Using {len(valid_movies_df)} movies for similarity computation.")
    
    # If we don't have enough movies, exit
    if len(valid_movies_df) < 10:
        print("Error: Not enough valid movies for meaningful similarity computation.")
        return
    
    # Create a mapping from TMDB ID to database movie_id
    tmdb_to_movie_id = valid_movies
    
    # Extract features for similarity computation
    # 1. Process Genres
    print("Processing genres...")
    valid_movies_df['genre_names'] = valid_movies_df['genres'].apply(
        lambda x: [genre['name'] for genre in x] if isinstance(x, list) else []
    )
    
    mlb = MultiLabelBinarizer()
    genres_matrix = mlb.fit_transform(valid_movies_df['genre_names'])
    
    # 2. Process Text Features
    print("Processing text features...")
    # Make sure we have text to process
    valid_movies_df['overview'] = valid_movies_df['overview'].fillna('')
    
    # Check if we have any non-empty overviews
    non_empty_count = (valid_movies_df['overview'].str.strip() != '').sum()
    print(f"Found {non_empty_count} movies with non-empty overviews")
    
    if non_empty_count == 0:
        print("Error: No movies with text in overview field.")
        return
    
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(valid_movies_df['overview'])
    
    # 3. Process Numerical Features
    print("Processing numerical features...")
    numerical_features = ['budget', 'revenue', 'runtime']
    numerical_df = valid_movies_df[numerical_features].apply(pd.to_numeric, errors='coerce')
    
    # Replace 0s with the median
    for col in numerical_df.columns:
        numerical_df[col] = numerical_df[col].replace(0, numerical_df[col].median())
    
    # Fill remaining NaNs with the median
    numerical_df = numerical_df.fillna(numerical_df.median())
    
    # Normalize the numerical features
    scaler = StandardScaler()
    normalized_numerical_df = pd.DataFrame(
        scaler.fit_transform(numerical_df),
        columns=numerical_df.columns
    )
    
    # Convert to sparse matrix
    numerical_sparse = csr_matrix(normalized_numerical_df.values)
    
    # 4. Process Collection Information
    print("Processing collection information...")
    # Create dummy variables for collection names
    collection_dummies = pd.get_dummies(valid_movies_df['collection_name'], prefix='collection', dummy_na=True)
    
    # Convert to sparse matrix and apply weighting
    collection_sparse = csr_matrix(collection_dummies.values) * 2  # Apply weight multiplier
    
    # 5. Create Combined Features
    print("Combining all features...")
    combined_features = hstack([
        genres_matrix,               # Genre features
        tfidf_matrix,                # Text features
        numerical_sparse,            # Numerical features
        collection_sparse            # Collection features
    ])
    
    # Use dimensionality reduction to make computation more efficient
    print("Performing dimensionality reduction...")
    #svd = TruncatedSVD(n_components=min(2000, combined_features.shape[1] - 1), random_state=42)
    svd = TruncatedSVD(n_components=2000, random_state=42)
    reduced_features = svd.fit_transform(combined_features)
    print(f"Explained variance ratio: {svd.explained_variance_ratio_.sum():.2f}")
    
    # Compute similarities in batches and store in database
    with Database() as db:
        num_movies = len(valid_movies_df)
        
        for i in range(0, num_movies, batch_size):
            batch_end = min(i + batch_size, num_movies)
            print(f"Processing batch {i+1} to {batch_end} of {num_movies}...")
            
            # Compute similarities for this batch
            batch_similarities = cosine_similarity(
                reduced_features[i:batch_end], 
                reduced_features
            )
            
            # Store top similarities for each movie in the batch
            for idx, similarities in enumerate(batch_similarities):
                movie_idx = i + idx
                tmdb_id = valid_movies_df.iloc[movie_idx]['id']
                
                # Get the database movie_id for this movie
                movie_id = tmdb_to_movie_id[tmdb_id]
                
                # Get indices of top similar movies (excluding self)
                top_indices = similarities.argsort()[::-1][1:11]  # Top 10 excluding self
                
                # Batch insert similarities
                similarity_data = []
                for target_idx in top_indices:
                    target_tmdb_id = valid_movies_df.iloc[target_idx]['id']
                    target_movie_id = tmdb_to_movie_id[target_tmdb_id]
                    score = similarities[target_idx]
                    
                    similarity_data.append((movie_id, target_movie_id, score))
                
                # Use executemany for better performance
                if similarity_data:
                    try:
                        db.cursor.executemany(
                            """
                            INSERT INTO movie_similarities 
                            (source_movie_id, target_movie_id, similarity_score)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (source_movie_id, target_movie_id) 
                            DO UPDATE SET similarity_score = EXCLUDED.similarity_score
                            """,
                            similarity_data
                        )
                        db.conn.commit()
                    except Exception as e:
                        db.conn.rollback()
                        print(f"Error inserting similarities for movie {tmdb_id}: {e}")
            
            # Calculate and print progress
            progress = min(100, (batch_end / num_movies) * 100)
            elapsed = time.time() - start_time
            est_total = elapsed / (progress / 100)
            est_remaining = est_total - elapsed
            
            print(f"Progress: {progress:.1f}% - Time elapsed: {elapsed:.1f}s - Est. remaining: {est_remaining:.1f}s")
    
    print(f"Similarity computation completed in {time.time() - start_time:.1f} seconds.")

def import_movies_to_db(db_movies):
    """Import the processed movies into the database with enhanced error handling"""
    print("Importing movies to database...")
    start_time = time.time()
    
    # Ensure data types are appropriate
    db_movies['tmdb_id'] = pd.to_numeric(db_movies['tmdb_id'], errors='coerce').fillna(0).astype(int)
    
    # Additional preprocessing to handle problematic data
    # Convert NaN values to None (NULL in database)
    """for col in db_movies.columns:
        if db_movies[col].dtype == 'float64' or db_movies[col].dtype == 'int64':
            db_movies[col] = db_movies[col].where(pd.notnull(db_movies[col]), None)"""
    
    # Handle duplicate tmdb_ids by keeping the first occurrence
    db_movies = db_movies.drop_duplicates(subset=['tmdb_id'], keep='first')
    print(f"After removing duplicates, {len(db_movies)} unique movies remain")

    # Convert dataframe to list of dictionaries
    movies_records = db_movies.to_dict('records')
    
    with Database() as db:
        # Use individual inserts with detailed error reporting
        success_count = 0
        error_count = 0
        
        for i, movie in enumerate(movies_records):
            if i % 1000 == 0:
                print(f"Processing movie {i+1} of {len(movies_records)}...")
            
            try:
                # Explicitly prepare each value to ensure types are correct
                # Handle potential NULL values
                tmdb_id = int(movie['tmdb_id']) if pd.notnull(movie['tmdb_id']) else None
                title = str(movie['title']) if pd.notnull(movie['title']) else ''
                release_date = movie['release_date'] if pd.notnull(movie['release_date']) else None
                overview = str(movie['overview']) if pd.notnull(movie['overview']) else ''
                vote_average = float(movie['vote_average']) if pd.notnull(movie['vote_average']) else None
                budget = float(movie['budget']) if pd.notnull(movie['budget']) else None
                revenue = float(movie['revenue']) if pd.notnull(movie['revenue']) else None
                runtime = float(movie['runtime']) if pd.notnull(movie['runtime']) else None
                collection_name = movie['collection_name'] if pd.notnull(movie['collection_name']) else None
                genres = movie['genres'] if pd.notnull(movie['genres']) else '[]'
                
                # Execute the insert
                db.execute(
                    """
                    INSERT INTO movies 
                    (tmdb_id, title, release_date, overview, vote_average, 
                    budget, revenue, runtime, collection_name, genres)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (tmdb_id) DO NOTHING
                    """,
                    (
                        tmdb_id, title, release_date, overview, vote_average,
                        budget, revenue, runtime, collection_name, genres
                    ),
                    commit=(i % 100 == 99)  # Commit every 100 rows
                )
                
                success_count += 1
            except Exception as e:
                error_count += 1
                if error_count < 5:  # Only show first few errors
                    print(f"Error importing movie {i+1}:")
                    print(f"  tmdb_id: {movie.get('tmdb_id', 'unknown')}")
                    print(f"  title: {movie.get('title', 'unknown')}")
                    print(f"  Error: {str(e)}")
                elif error_count == 5:
                    print("Too many errors, suppressing further error messages...")
        
        # Final commit
        db.conn.commit()
        
        # Count how many movies are actually in the database
        db.execute("SELECT COUNT(*) FROM movies")
        actual_count = db.fetchone()['count']
        
        print(f"Successfully processed {success_count} movies.")
        print(f"Failed to process {error_count} movies.")
        print(f"Actual number of movies in database: {actual_count}")
    
    print(f"Movie import completed in {time.time() - start_time:.1f} seconds.")
    return success_count

def main():
    """Main function to import data and compute similarities"""
    # Setup database tables
    with Database() as db:
        with open('db_schema.sql', 'r') as f:
            db.execute(f.read(), commit=True)
        print("Database schema created successfully.")
    
    # Process and import movies
    db_movies, movies_df = preprocess_movie_data('data/movies_metadata.csv')
    success_count = import_movies_to_db(db_movies)
    
    # Only compute similarities if we have successfully imported movies
    if success_count > 0:
        print("Computing movie similarities...")
        compute_movie_similarities(movies_df)
        print("Data import and similarity computation completed successfully!")
    else:
        print("No movies were imported, skipping similarity computation.")

if __name__ == "__main__":
    main()