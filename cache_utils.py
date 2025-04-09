import redis
import json
import os
import pickle
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

class RedisCache:
    """Redis caching utility for the movie recommendation system"""
    
    def __init__(self):
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)
        self.default_ttl = int(os.getenv('REDIS_DEFAULT_TTL', 86400))  # 24 hours
        self.client = None
        
    def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                decode_responses=False  # Keep as bytes for binary data
            )
            self.client.ping()  # Test connection
            return True
        except redis.ConnectionError as e:
            print(f"Error connecting to Redis: {e}")
            return False
            
    def disconnect(self):
        """Close the Redis connection"""
        if self.client:
            self.client.close()
            
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    def get(self, key):
        """Get a value from the cache"""
        if not self.client:
            return None
            
        try:
            data = self.client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            print(f"Error retrieving from cache: {e}")
            return None
            
    def set(self, key, value, ttl=None):
        """Set a value in the cache with optional TTL"""
        if not self.client:
            return False
            
        if ttl is None:
            ttl = self.default_ttl
            
        try:
            # Use pickle to serialize complex objects
            serialized_value = pickle.dumps(value)
            return self.client.setex(key, ttl, serialized_value)
        except Exception as e:
            print(f"Error setting cache: {e}")
            return False
            
    def delete(self, key):
        """Delete a key from the cache"""
        if not self.client:
            return False
            
        try:
            return self.client.delete(key) > 0
        except Exception as e:
            print(f"Error deleting from cache: {e}")
            return False
            
    def get_recommendations(self, movie_id):
        """Get cached recommendations for a movie"""
        return self.get(f"recommendations:{movie_id}")
        
    def set_recommendations(self, movie_id, recommendations, ttl=None):
        """Cache recommendations for a movie"""
        return self.set(f"recommendations:{movie_id}", recommendations, ttl)
        
    def get_visualization(self, movie_id, viz_type):
        """Get a cached visualization for a movie"""
        return self.get(f"viz:{movie_id}:{viz_type}")
        
    def set_visualization(self, movie_id, viz_type, image_data, ttl=None):
        """Cache a visualization for a movie"""
        return self.set(f"viz:{movie_id}:{viz_type}", image_data, ttl)