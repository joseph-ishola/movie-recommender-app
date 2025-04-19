// static/script.js
document.addEventListener('DOMContentLoaded', function() {
    //console.log("Script loaded - version 1.6");
    
    // Elements for search and recommendations
    const recommendForm = document.getElementById('recommendForm');
    const resultsDiv = document.getElementById('results');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const recommendationsContainer = document.getElementById('recommendationsContainer');
    const errorMessage = document.getElementById('errorMessage');
    const backToSearch = document.getElementById('backToSearch');
    
    // Add event listener for form submission
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
            //console.log("Searching for:", movieTitle);
            
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
                //console.log("Search response:", data);
                
                // Hide loading indicator
                loadingIndicator.style.display = 'none';
                
                if (data.status === 'error') {
                    showError(data.message);
                    return;
                }
                
                // If exact match found, get recommendations directly
                if (data.exact_match) {
                    console.log("Exact match found, getting recommendations");
                    getRecommendations(data.movie.movie_id);
                }
                // If multiple exact matches found (same title as search term), go directly to multiple matches UI
                else if (data.similar_movies && data.similar_movies.length > 0) {
                    // Check if these are exact matches for the search term
                    const exactMatches = data.similar_movies.filter(movie => 
                        movie.title.toLowerCase() === movieTitle.toLowerCase());
                    
                    if (exactMatches.length > 1) {
                        // Multiple exact matches (like "The Avengers"), use multiple matches UI directly
                        //console.log("Multiple exact matches found:", exactMatches.length);
                        showMultipleMatchesUI(exactMatches, movieTitle);
                    } 
                    else if (exactMatches.length === 1) {
                        // Single exact match with the title, get recommendations
                        console.log("Single exact match found in similar movies");
                        getRecommendations(exactMatches[0].movie_id);
                    }
                    else {
                        // Partial matches (like "game"), show search results
                        //console.log("Partial matches found:", data.similar_movies.length);
                        showSearchResultsUI(data.similar_movies, movieTitle);
                    }
                }
                else {
                    // No matches found
                    showNoMatchUI(`No movies found matching "${movieTitle}"`, []);
                }
            })
            .catch(error => {
                console.error("Search error:", error);
                showError('An error occurred while searching for the movie. Please try again.');
            });
        });
    }
    
    // Event delegation for all button clicks
    document.addEventListener('click', function(event) {
        const targetElement = event.target.closest('button');
        if (!targetElement) return;

        // Get data attributes
        const movieId = targetElement.getAttribute('data-movie-id');
        const movieTitle = targetElement.getAttribute('data-title');
        
        // 1. CASE: Initial search results (when user searches for "game" and gets a list of similar titles)
        if (targetElement.classList.contains('similar-title')) {
            //console.log("Similar title clicked:", movieTitle);
            event.preventDefault();
            
            // Show loading
            recommendationsContainer.style.display = 'none';
            loadingIndicator.style.display = 'block';
            
            // Do a new search for this exact title
            const formData = new FormData();
            formData.append('movie_title', movieTitle);
            
            fetch('/api/search', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loadingIndicator.style.display = 'none';
                //console.log("Search for exact title result:", data);
                
                if (data.status === 'error') {
                    showError(data.message);
                    return;
                }
                
                // If exact match, get recommendations directly
                if (data.exact_match) {
                    console.log("Single exact match found");
                    getRecommendations(data.movie.movie_id);
                }
                // If multiple similar movies with the exact title, show multiple matches UI
                else if (data.similar_movies && data.similar_movies.length > 0) {
                    // Filter to only exact title matches
                    const exactMatches = data.similar_movies.filter(movie => 
                        movie.title.toLowerCase() === movieTitle.toLowerCase());
                    
                    if (exactMatches.length > 0) {
                        console.log("Multiple exact matches found for title");
                        showMultipleMatchesUI(exactMatches, movieTitle);
                    } else {
                        // This should rarely happen - fall back to showing all similar movies
                        console.log("No exact matches found, showing similar movies");
                        showMultipleMatchesUI(data.similar_movies, movieTitle);
                    }
                }
                else {
                    showNoMatchUI(`No movies found matching "${movieTitle}"`, []);
                }
            })
            .catch(error => {
                loadingIndicator.style.display = 'none';
                showError('An error occurred. Please try again.');
                console.error(error);
            });
            return;
        }
        
        // 2. CASE: Multiple matches selection (when user has selected a movie and there are multiple versions)
        if (targetElement.classList.contains('movie-choice')) {
            //console.log("Specific movie version selected:", movieTitle, "ID:", movieId);
            event.preventDefault();
            
            // Show loading
            recommendationsContainer.style.display = 'none';
            loadingIndicator.style.display = 'block';
            
            // Get recommendations directly
            getRecommendations(movieId);
            return;
        }
        
        // 3. CASE: New search button
        if (targetElement.id === 'newSearchBtn') {
            document.getElementById('movieTitle').value = '';
            document.getElementById('movieTitle').focus();
            resultsDiv.style.display = 'none';
        }
    });
    
    // Back to search button
    if (backToSearch) {
        backToSearch.addEventListener('click', function() {
            resultsDiv.style.display = 'none';
            document.getElementById('movieTitle').value = '';
        });
    }
    
    // Function to fetch and display recommendations
    function getRecommendations(movieId) {
        //console.log("Getting recommendations for movie ID:", movieId);
        
        // Show loading indicator
        recommendationsContainer.style.display = 'none';
        loadingIndicator.style.display = 'block';
        
        // Fetch recommendations
        fetch(`/api/recommendations/${movieId}`)
            .then(response => {
                console.log("Recommendations response status:", response.status);
                return response.json();
            })
            .then(data => {
                //console.log("Recommendations data:", data);
                loadingIndicator.style.display = 'none';
                
                if (data.status === 'error') {
                    showError(data.message);
                    return;
                }
                
                // Display recommendations
                displayRecommendations(data, movieId);
            })
            .catch(error => {
                console.error("Error fetching recommendations:", error);
                loadingIndicator.style.display = 'none';
                showError('An error occurred while fetching recommendations. Please try again.');
            });
    }
    
    // Function to display recommendation results
    function displayRecommendations(data, movieId) {
        const recommendations = data.recommendations;
        const metrics = data.metrics;
        const sourceMovie = data.source_movie;
        
        // Get source movie title and release year for the header
        const movieTitle = sourceMovie.title;
        const releaseYear = sourceMovie.release_date ? new Date(sourceMovie.release_date).getFullYear() : '';
        const titleDisplay = releaseYear ? `${movieTitle} (${releaseYear})` : movieTitle;
        
        // Format the recommendations table rows
        const tableRows = recommendations.map(rec => {
            // Format genres
            let genreNames = '';
            if (rec.genres) {
                if (typeof rec.genres === 'string') {
                    try {
                        const genres = JSON.parse(rec.genres);
                        genreNames = genres.map(g => g.name).join(', ');
                    } catch (e) {
                        console.error('Error parsing genres:', e);
                        genreNames = rec.genres;
                    }
                } else if (Array.isArray(rec.genres)) {
                    genreNames = rec.genres.map(g => g.name || g).join(', ');
                }
            }
            
            // Format similarity score as percentage
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
        
        // Create metrics HTML
        const metricsHTML = `
            <div class="row">
                <div class="col-md-4">
                    <div class="card text-center mb-3 mb-md-0">
                        <div class="card-body">
                            <i class="bi bi-intersect text-primary mb-3" style="font-size: 2rem;"></i>
                            <h5 class="card-title">Genre Overlap</h5>
                            <h2 class="display-4">${metrics.average_genre_overlap.toFixed(1)}%</h2>
                            <p class="text-muted">Shared genres between movies</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center mb-3 mb-md-0">
                        <div class="card-body">
                            <i class="bi bi-star-half text-primary mb-3" style="font-size: 2rem;"></i>
                            <h5 class="card-title">Rating Similarity</h5>
                            <h2 class="display-4">${metrics.average_rating_difference.toFixed(2)}</h2>
                            <p class="text-muted">Avg. rating difference (lower is better)</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <i class="bi bi-shuffle text-primary mb-3" style="font-size: 2rem;"></i>
                            <h5 class="card-title">Content Relevance</h5>
                            <h2 class="display-4">${metrics.average_content_relevance.toFixed(1)}%</h2>
                            <p class="text-muted">Thematic similarity</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Create the full HTML structure for recommendations
        const recommendationsHTML = `
            <div class="card shadow-sm mb-4 fade-in">
                <div class="card-header bg-primary text-white">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-list-stars me-2"></i>
                        <h3 class="card-title mb-0">Recommended Movies for "${titleDisplay}"</h3>
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
                            <img id="similarity-chart-chart" class="img-fluid rounded" src="${chartPath}" style="display: none;" alt="Similarity chart">
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
                            <img id="wordcloud-image" class="img-fluid rounded" src="${wordcloudPath}" style="display: none;" alt="Word cloud">
                        </div>
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
                    ${metricsHTML}
                </div>
            </div>
        `;
        
        // Update the recommendations container
        recommendationsContainer.innerHTML = recommendationsHTML;
        recommendationsContainer.style.display = 'block';
        
        // Load visualizations
        loadVisualization('similarity-chart-chart', 'similarity-chart-placeholder', chartPath);
        loadVisualization('wordcloud-image', 'wordcloud-placeholder', wordcloudPath);
    }
    
    // Function to display initial search results
    function showSearchResultsUI(movies, searchTerm) {
        console.log("Showing search results for:", searchTerm);
        //console.log("Found movies:", movies);
        
        // Create HTML for movie options - using similar-title class for initial search results
        const moviesHtml = movies.map(movie => {
            const releaseDate = movie.release_date ? new Date(movie.release_date).getFullYear() : 'Unknown';
            
            return `
                <button type="button" class="list-group-item list-group-item-action similar-title d-flex justify-content-between align-items-center"
                        data-movie-id="${movie.movie_id}" 
                        data-title="${movie.title}">
                    <span><i class="bi bi-film me-2"></i>${movie.title}</span>
                    <i class="bi bi-chevron-right"></i>
                </button>
            `;
        }).join('');
        
        // Create the selection UI
        const resultsHTML = `
            <div class="card shadow-sm mb-4 fade-in">
                <div class="card-header bg-info text-white">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-search me-2"></i>
                        <h3 class="card-title mb-0">Search Results</h3>
                    </div>
                </div>
                <div class="card-body">
                    <p>We found these movies matching your search for "${searchTerm}":</p>
                    <div class="list-group mb-3">
                        ${moviesHtml}
                    </div>
                </div>
            </div>
        `;
        
        // Update the recommendations container
        recommendationsContainer.innerHTML = resultsHTML;
        recommendationsContainer.style.display = 'block';
    }
    
    // Function to display multiple matches UI
    function showMultipleMatchesUI(movies, searchedTitle) {
        console.log("Showing multiple matches UI for:", searchedTitle);
        //console.log("Movies:", movies);
        
        // Create HTML for movie options
        const moviesHtml = movies.map(movie => {
            const releaseDate = movie.release_date ? new Date(movie.release_date).getFullYear() : 'Unknown';
            
            // All buttons in the multiple matches UI should use the class "movie-choice"
            return `
                <button type="button" class="list-group-item list-group-item-action movie-choice d-flex justify-content-between align-items-center"
                        data-movie-id="${movie.movie_id}" 
                        data-title="${movie.title}">
                    <span><i class="bi bi-film me-2"></i>${movie.title} (${releaseDate})</span>
                    <i class="bi bi-chevron-right"></i>
                </button>
            `;
        }).join('');
        
        // Create the selection UI
        const matchesHTML = `
            <div class="card shadow-sm mb-4 fade-in">
                <div class="card-header bg-primary text-white">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-list-stars me-2"></i>
                        <h3 class="card-title mb-0">Multiple Matches Found</h3>
                    </div>
                </div>
                <div class="card-body">
                    <p>We found multiple movies with the title "${searchedTitle}". Please select which one you meant:</p>
                    <div class="list-group mb-3">
                        ${moviesHtml}
                    </div>
                </div>
            </div>
        `;
        
        // Update the recommendations container
        recommendationsContainer.innerHTML = matchesHTML;
        recommendationsContainer.style.display = 'block';
    }
    
    // Function to show no matches UI
    function showNoMatchUI(message, similarTitles) {
        console.log("Showing no matches UI with message:", message);
        console.log("Similar titles:", similarTitles);
        
        let similarTitlesHTML = '';
        if (similarTitles && similarTitles.length > 0) {
            const titlesHTML = similarTitles.map((movie, index) => {
                const releaseDate = movie.release_date ? new Date(movie.release_date).getFullYear() : 'Unknown';
                return `
                    <button type="button" class="list-group-item list-group-item-action similar-title d-flex justify-content-between align-items-center"
                            id="similar-title-${index}" 
                            data-movie-id="${movie.movie_id}"
                            data-title="${movie.title}">
                        <span><i class="bi bi-film me-2"></i>${movie.title} (${releaseDate})</span>
                        <i class="bi bi-chevron-right"></i>
                    </button>
                `;
            }).join('');
            
            similarTitlesHTML = `
                <p class="mb-3">Did you mean one of these?</p>
                <div class="list-group mb-4">
                    ${titlesHTML}
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
        
        // Update recommendations container
        recommendationsContainer.innerHTML = noMatchHTML;
        recommendationsContainer.style.display = 'block';
    }
    
    // Function to show error message
    function showError(message) {
        console.error("Error:", message);
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }
    
    // Function to load visualizations with fixed IDs
    function loadVisualization(imgId, placeholderId, url) {
        const imgElement = document.getElementById(imgId);
        const placeholder = document.getElementById(placeholderId);
        
        if (!imgElement || !placeholder) {
            console.error(`Elements not found. Image: ${imgId}, Placeholder: ${placeholderId}`);
            return;
        }
        
        //console.log(`Loading visualization for ${imgId} from ${url}`);
        
        // Create a new image element to preload the image
        const img = new Image();
        
        img.onload = function() {
            imgElement.src = url;
            imgElement.style.display = 'block';
            placeholder.style.display = 'none';
            console.log(`${imgId} loaded successfully`);
        };
        
        img.onerror = function(error) {
            console.error(`Error loading ${imgId}:`, error);
            placeholder.innerHTML = `<div class="alert alert-warning">Failed to load visualization</div>`;
        };
        
        // Start loading the image
        img.src = url;
    }
});