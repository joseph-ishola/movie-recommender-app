# Movie Recommender System

![Movie Recommender](https://img.shields.io/badge/Movie-Recommender-blue) ![Python](https://img.shields.io/badge/Python-3.10+-green) ![Flask](https://img.shields.io/badge/Flask-2.2.3-red) ![Docker](https://img.shields.io/badge/Docker-Ready-blue)

A scalable, production-ready content-based movie recommendation app that uses machine learning techniques to provide personalized movie suggestions based on movie content features.

Visit https://app.josephishola.com and search for your favorite films and discover new movies you might love.

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technical Details](#technical-details)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Deployment](#deployment)
- [Future Improvements](#future-improvements)
- [Contributing](#contributing)
- [License](#license)

## 🎬 Overview

This Movie Recommender System uses content-based filtering techniques to suggest movies similar to ones a user already enjoys. Unlike collaborative filtering systems that rely on user behavior patterns, this system analyzes movie features such as:

- Genres
- Plot descriptions
- Collections/series information
- Numerical attributes (budget, revenue, runtime)

The system is designed with scalability and production readiness in mind, featuring a modern web interface, optimized backend with caching, and containerized deployment capabilities.

## ✨ Features

- **Content-based movie recommendations** with high accuracy
- **Modern web interface** with responsive design
- **Real-time similarity visualization** including similarity charts and wordclouds
- **Robust search functionality** with partial matching and disambiguation
- **Multi-layered caching** system using Redis and database storage
- **Evaluation metrics** for recommendation quality (genre overlap, rating similarity, content relevance)
- **Containerized architecture** for easy deployment
- **API-based design** allowing for easy integration with other systems

## 🏗️ Architecture

The system follows a modern microservices architecture:

![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)

```
                   ┌─────────────┐
                   │    Client   │
                   └──────┬──────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │    Web Server   │
                 │    (Flask)      │
                 └────────┬────────┘
                          │
                          ▼
         ┌───────────────────────────────┐
         │         API Service           │
         │         (Flask)               │
         └┬──────────────┬──────────────┬┘
          │              │              │
          ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │     Redis    │ │Visualization │
│   Database   │ │     Cache    │ │   Storage    │
└──────────────┘ └──────────────┘ └──────────────┘
```

- **Web Frontend**: Responsive UI built with Bootstrap and custom JavaScript
- **API Layer**: RESTful Flask API with caching strategies
- **Database**: PostgreSQL for storing movie data and similarities
- **Caching**: Redis for high-performance response caching
- **Visualization**: Dynamic chart generation with Matplotlib and WordCloud

## 🔧 Technical Details

### Content-Based Filtering Algorithm

The recommendation engine uses a sophisticated approach combining multiple features:

1. **Genre Processing**: Uses MultiLabelBinarizer to convert categorical genre data into a numerical format
2. **Text Analysis**: Applies TF-IDF vectorization to movie overviews
3. **Numerical Features**: Standardizes and normalizes budget, revenue, and runtime data
4. **Collection Information**: Applies weight multipliers to movie collection data
5. **Dimensionality Reduction**: Uses TruncatedSVD to reduce feature dimensionality while preserving similarity relationships
6. **Similarity Computation**: Calculates cosine similarity between movie feature vectors

### Performance Optimizations

- **Pre-computed similarities**: Calculates and stores movie similarities in advance
- **Multi-level caching**: Uses Redis for in-memory caching and database for persistent storage
- **Asynchronous image loading**: Loads visualizations asynchronously to improve response time
- **Optimized visualization generation**: Configures matplotlib for fastest rendering with appropriate resolution

### Evaluation Metrics

The system evaluates recommendations using three key metrics:

1. **Genre Overlap**: Measures the Jaccard similarity between genre sets
2. **Rating Similarity**: Calculates the average rating difference between movies
3. **Content Relevance**: Uses TF-IDF and cosine similarity on genre features

## 📷 Screenshots

*[Screenshot ]*

## 🚀 Installation

### Prerequisites
- Python 3.10+
- PostgreSQL
- Redis
- Docker (optional)

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/joseph-ishola/movie-recommender-app.git
cd movie-recommender-app
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements-dataimport.txt
pip install -r requirements-api.txt
pip install -r requirements-webapp.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
python import_movies.py
```

6. Start the services:
```bash
# In separate terminals:
python api.py
python app.py
```

7. Access the web interface at http://localhost:8080

### Docker Setup

1. Build and start services with Docker Compose:
```bash
docker-compose up -d
```

2. Access the web interface at http://localhost:8080

## 🌐 Deployment

### AWS Deployment (Free Tier)

The system was deployed to AWS EC2 using the following steps:

1. Launch an EC2 t2.micro instance with Amazon Linux 2
2. Install Docker and Docker Compose
3. Clone the repository and configure environment variables
4. Build and start the services with Docker Compose
5. Access the application via the EC2 public DNS

## 🔮 Future Improvements

- Integration of collaborative filtering methods
- User account system with personalized recommendations
- A/B testing framework for algorithm improvements
- Real-time recommendation updates
- Integration with external movie APIs for up-to-date information
- Mobile application

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created by [Joseph Kehinde Ishola](https://github.com/joseph-ishola) | [LinkedIn](https://www.linkedin.com/in/joseph-ishola)

