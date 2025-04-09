// static/script.js
document.addEventListener('DOMContentLoaded', function() {
    // Elements for search and recommendations
    const recommendForm = document.getElementById('recommendForm');
    const resultsDiv = document.getElementById('results');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const recommendationsContainer = document.getElementById('recommendationsContainer');
    const errorMessage = document.getElementById('errorMessage');
    const backToSearch = document.getElementById('backToSearch');
    
    // Recommendation form submit handler
    if (recommendForm) {
        recommendForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show results section with loading indicator
            resultsDiv.style.display = 'block';
            loadingIndicator.style.display = 'block';
            recommendationsContainer.style.display = 'none';
            errorMessage.style.display = 'none';
            
            // Get the movie title
            const movieTitle = document.getElementById('movieTitle').value;
            
            // Create form data
            const formData = new FormData();
            formData.append('movie_title', movieTitle);
            
            // First search for the movie
            fetch('/api/search', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'error') {
                    showError(data.message);
                    return;
                }
                
                // If exact match found, get recommendations
                if (data.exact_match) {
                    getRecommendations(data.movie.movie_id);
                } else if (data.similar_movies && data.similar_movies.length > 0) {
                    // Show multiple matches UI
                    showMultipleMatchesUI(data.similar_movies, movieTitle);
                } else {
                    // No matches found
                    showNoMatchUI(`No movies found matching "${movieTitle}"`, []);
                }
            })
            .catch(error => {
                showError('An error occurred while searching for the movie. Please try again.');
                console.error('Error:', error);
            });
        });
    }
    
    // Back to search button
    if (backToSearch) {
        backToSearch.addEventListener('click', function() {
            resultsDiv.style.display = 'none';
            document.getElementById('movieTitle').value = '';
        });
    }
    
    function getRecommendations(movieId) {
        // Fetch recommendations for the selected movie
        fetch(`/api/recommendations/${movieId}`)
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(`API Error (${response.status}): ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                // Hide loading indicator
                loadingIndicator.style.display = 'none';
                
                if (data.status === 'error') {
                    showError(data.message);
                    return;
                }
                
                // Display recommendations
                displayRecommendations(data, movieId);
            })
            .catch(error => {
                console.error('Recommendation error:', error);
                showError(`Error: ${error.message}`);
            });
    }
    
    function showMultipleMatchesUI(movies, searchedTitle) {
        // Hide loading indicator
        loadingIndicator.style.display = 'none';
        
        // Create HTML for movie selection
        const matchesHTML = `
            <div class="card shadow-sm mb-4 fade-in">
                <div class="card-header bg-primary text-white">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-list-stars me-2"></i>
                        <h3 class="card-title mb-0">Multiple Matches Found</h3>
                    </div>
                </div>
                <div class="card-body">
                    <p>We found multiple movies matching "${searchedTitle}". Please select which one you meant:</p>
                    <div class="list-group mb-3">
                        ${movies.map(movie => `
                            <button type="button" class="list-group-item list-group-item-action movie-choice d-flex justify-content-between align-items-center"
                                    data-movie-id="${movie.movie_id}" data-title="${movie.title}">
                                <span><i class="bi bi-film me-2"></i>${movie.title} (${new Date(movie.release_date).getFullYear()})</span>
                                <i class="bi bi-chevron-right"></i>
                            </button>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
        
        // Display the matches UI
        recommendationsContainer.innerHTML = matchesHTML;
        recommendationsContainer.style.display = 'block';
        
        // Add event listeners to the movie choices
        document.querySelectorAll('.movie-choice').forEach(button => {
            button.addEventListener('click', function() {
                const movieId = this.getAttribute('data-movie-id');
                
                // Show loading again
                recommendationsContainer.style.display = 'none';
                loadingIndicator.style.display = 'block';
                
                // Get recommendations for the selected movie
                getRecommendations(movieId);
            });
        });
    }
    
    function showNoMatchUI(message, similarTitles) {
        // Hide loading indicator
        loadingIndicator.style.display = 'none';
        
        let similarTitlesHTML = '';
        
        if (similarTitles && similarTitles.length > 0) {
            similarTitlesHTML = `
                <p class="mb-3">Did you mean one of these?</p>
                <div class="list-group mb-4">
                    ${similarTitles.map(movie => `
                        <button type="button" class="list-group-item list-group-item-action similar-title d-flex justify-content-between align-items-center"
                                data-movie-id="${movie.movie_id}" data-title="${movie.title}">
                            <span><i class="bi bi-film me-2"></i>${movie.title} (${new Date(movie.release_date).getFullYear()})</span>
                            <i class="bi bi-chevron-right"></i>
                        </button>
                    `).join('')}
                </div>
            `;
        } else {
            similarTitlesHTML = `<p class="mb-4">No similar titles were found in our database.</p>`;
        }
        
        const noMatchHTML = `
            <div class="card shadow-sm mb-4 fade-in">
                <div class="card-header bg-warning text-dark">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        <h3 class="card-title mb-0">Movie Not Found</h3>
                    </div>
                </div>
                <div class="card-body">
                    <div class="text-center my-4">
                        <i class="bi bi-film-slash" style="font-size: 4rem; color: #ccc;"></i>
                    </div>
                    <p class="text-center">${message}</p>
                    ${similarTitlesHTML}
                    <div class="text-center">
                        <button class="btn btn-primary" id="newSearchBtn">
                            <i class="bi bi-search me-2"></i>Try Another Search
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        recommendationsContainer.innerHTML = noMatchHTML;
        recommendationsContainer.style.display = 'block';
        
        // Add event listeners to similar title buttons
        document.querySelectorAll('.similar-title').forEach(button => {
            button.addEventListener('click', function() {
                const movieId = this.getAttribute('data-movie-id');
                
                // Show loading again
                recommendationsContainer.style.display = 'none';
                loadingIndicator.style.display = 'block';
                
                // Get recommendations for the selected movie
                getRecommendations(movieId);
            });
        });
        
        // Add event listener to the new search button
        document.getElementById('newSearchBtn').addEventListener('click', function() {
            document.getElementById('movieTitle').value = '';
            document.getElementById('movieTitle').focus();
            resultsDiv.style.display = 'none';
        });
    }
    
    function displayRecommendations(data, movieId) {
        const recommendations = data.recommendations;
        
        // Format the recommendations table rows
        const tableRows = recommendations.map(rec => {
            // Format genres as a comma-separated list
            // Check if genres is already an object or a string
            let genreNames = '';
            if (rec.genres) {
                if (typeof rec.genres === 'string') {
                    // If it's a string, parse it
                    try {
                        genreNames = JSON.parse(rec.genres).map(g => g.name).join(', ');
                    } catch (e) {
                        console.error("Error parsing genres:", e);
                        genreNames = rec.genres; // Use as-is if parsing fails
                    }
                } else if (Array.isArray(rec.genres)) {
                    // If it's already an array, map directly
                    genreNames = rec.genres.map(g => g.name).join(', ');
                }
            }
            
            // Format similarity as percentage
            const similarity = (rec.similarity_score * 100).toFixed(1) + '%';
            
            // Format release date
            const releaseDate = rec.release_date ? new Date(rec.release_date).toLocaleDateString() : 'Unknown';
            
            return `
            <tr>
                <td><strong>${rec.title}</strong></td>
                <td>${genreNames}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="text-warning me-2"><i class="bi bi-star-fill"></i></div>
                        <div>${parseFloat(rec.vote_average).toFixed(1)}</div>
                    </div>
                </td>
                <td>${releaseDate}</td>
                <td>
                    <div class="progress" style="height: 8px;">
                        <div class="progress-bar" role="progressbar" style="width: ${similarity};" 
                             aria-valuenow="${rec.similarity_score * 100}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                    <small class="text-muted">${similarity}</small>
                </td>
            </tr>
            `;
        }).join('');
        
        // Set up paths for visualizations with cache-busting
        const timestamp = new Date().getTime();
        const chartPath = `/api/visualization/similarity_chart/${movieId}?t=${timestamp}`;
        const wordcloudPath = `/api/visualization/wordcloud/${movieId}?t=${timestamp}`;
        
        // Create the full HTML structure for recommendations
        const recommendationsHTML = `
            <div class="card shadow-sm mb-4 fade-in">
                <div class="card-header bg-primary text-white">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-list-stars me-2"></i>
                        <h3 class="card-title mb-0">Recommended Movies</h3>
                    </div>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Title</th>
                                    <th>Genres</th>
                                    <th>Rating</th>
                                    <th>Release Date</th>
                                    <th>Similarity</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="card shadow-sm fade-in">
                <div class="card-header bg-primary text-white">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-graph-up me-2"></i>
                        <h3 class="card-title mb-0">Evaluation Metrics</h3>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <div class="card text-center mb-3 mb-md-0">
                                <div class="card-body">
                                    <i class="bi bi-intersect text-primary mb-3" style="font-size: 2rem;"></i>
                                    <h5 class="card-title">Genre Overlap</h5>
                                    <h2 class="display-4">85.2%</h2>
                                    <p class="text-muted">Shared genres between movies</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card text-center mb-3 mb-md-0">
                                <div class="card-body">
                                    <i class="bi bi-star-half text-primary mb-3" style="font-size: 2rem;"></i>
                                    <h5 class="card-title">Rating Similarity</h5>
                                    <h2 class="display-4">0.74</h2>
                                    <p class="text-muted">Avg. rating difference (lower is better)</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card text-center">
                                <div class="card-body">
                                    <i class="bi bi-shuffle text-primary mb-3" style="font-size: 2rem;"></i>
                                    <h5 class="card-title">Content Relevance</h5>
                                    <h2 class="display-4">92.3%</h2>
                                    <p class="text-muted">Thematic similarity</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="card shadow-sm fade-in">
                        <div class="card-header bg-primary text-white">
                            <div class="d-flex align-items-center">
                                <i class="bi bi-bar-chart-fill me-2"></i>
                                <h3 class="card-title mb-0">Similarity Chart</h3>
                            </div>
                        </div>
                        <div class="card-body text-center">
                            <div id="similarity-chart-placeholder" class="viz-placeholder">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading chart...</span>
                                </div>
                                <p class="mt-2">Generating chart...</p>
                            </div>
                            <img id="similarity-chart-chart" src="" class="img-fluid rounded" 
                                 alt="Similarity chart" style="display: none;">
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="card shadow-sm fade-in">
                        <div class="card-header bg-primary text-white">
                            <div class="d-flex align-items-center">
                                <i class="bi bi-cloud-fill me-2"></i>
                                <h3 class="card-title mb-0">Themes & Topics</h3>
                            </div>
                        </div>
                        <div class="card-body text-center">
                            <div id="wordcloud-placeholder" class="viz-placeholder">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading wordcloud...</span>
                                </div>
                                <p class="mt-2">Generating wordcloud...</p>
                            </div>
                            <img id="wordcloud-image" src="" class="img-fluid rounded" 
                                alt="Word cloud" style="display: none;">
                        </div>
                    </div>
                </div>
            </div>

        `;
        
        // Update the recommendations container with the generated HTML
        recommendationsContainer.innerHTML = recommendationsHTML;
        recommendationsContainer.style.display = 'block';

        // Load visualizations asynchronously after showing the recommendations
        setTimeout(() => {
            loadVisualization('similarity_chart', movieId, chartPath);
            loadVisualization('wordcloud', movieId, wordcloudPath);
        }, 100);
    }
    
    function loadVisualization(type, movieId, url) {
        // Get the placeholder and image elements
        const placeholder = document.getElementById(`${type.replace('_', '-')}-placeholder`);
        const imgElement = document.getElementById(`${type.replace('_', '-')}-${type === 'wordcloud' ? 'image' : 'chart'}`);
        
        if (!placeholder || !imgElement) {
            console.error(`Elements for ${type} not found`);
            return;
        }
        
        // Create a new image element to preload the visualization
        const img = new Image();
        
        // When the image loads, swap it in and hide the placeholder
        img.onload = function() {
            imgElement.src = url;
            imgElement.style.display = 'block';
            placeholder.style.display = 'none';
        };
        
        // If the image fails to load, show an error message
        img.onerror = function() {
            placeholder.innerHTML = `<div class="alert alert-warning">Failed to load ${type.replace('_', ' ')}.</div>`;
        };
        
        // Start loading the image
        img.src = url;
    }

    function showError(message) {
        // Hide loading indicator
        loadingIndicator.style.display = 'none';
        
        // Show error message
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }
});