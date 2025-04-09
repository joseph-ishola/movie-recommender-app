-- Drop existing objects if they exist
DROP MATERIALIZED VIEW IF EXISTS top_genres;
DROP INDEX IF EXISTS idx_visualizations_movie;
DROP INDEX IF EXISTS idx_similarities_score;
DROP INDEX IF EXISTS idx_similarities_source;
DROP INDEX IF EXISTS idx_movies_title;
DROP TABLE IF EXISTS visualizations;
DROP TABLE IF EXISTS movie_similarities;
DROP TABLE IF EXISTS movies;

-- Create tables for our movie recommendation system
CREATE TABLE IF NOT EXISTS movies (
    movie_id SERIAL PRIMARY KEY,
    tmdb_id INTEGER UNIQUE NOT NULL,  -- This is the ID from TMDB
    title VARCHAR(255) NOT NULL,
    release_date TIMESTAMP,  -- Allow NULL dates
    overview TEXT,
    vote_average FLOAT,
    genres JSONB,
    budget FLOAT,
    revenue FLOAT,
    runtime FLOAT,
    collection_name VARCHAR(255)
);

-- Table to store pre-computed similarities between movies
CREATE TABLE IF NOT EXISTS movie_similarities (
    id SERIAL PRIMARY KEY,
    source_movie_id INTEGER REFERENCES movies(movie_id),
    target_movie_id INTEGER REFERENCES movies(movie_id),
    similarity_score FLOAT NOT NULL,
    UNIQUE(source_movie_id, target_movie_id)
);

-- Table to cache visualization images
CREATE TABLE IF NOT EXISTS visualizations (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER REFERENCES movies(movie_id),
    visualization_type VARCHAR(50) NOT NULL, -- 'similarity_chart' or 'wordcloud'
    image_data BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(movie_id, visualization_type)
);

-- Create indexes for faster queries
CREATE INDEX idx_movies_title ON movies(LOWER(title));
CREATE INDEX idx_similarities_source ON movie_similarities(source_movie_id);
CREATE INDEX idx_similarities_score ON movie_similarities(similarity_score DESC);
CREATE INDEX idx_visualizations_movie ON visualizations(movie_id);

-- Create a materialized view for top genres
CREATE MATERIALIZED VIEW top_genres AS
SELECT 
    genre->>'name' as genre_name,
    COUNT(*) as count
FROM movies, jsonb_array_elements(genres) as genre
GROUP BY genre_name
ORDER BY count DESC;