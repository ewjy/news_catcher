// Main JavaScript for News Story Analyzer

document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('errorMessage');
    const results = document.getElementById('results');
    const searchBtn = document.getElementById('searchBtn');
    const btnText = document.getElementById('btnText');
    const btnLoading = document.getElementById('btnLoading');

    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get form data
        const keyword = document.getElementById('keyword').value.trim();
        const daysBack = parseInt(document.getElementById('days_back').value);
        const maxArticles = parseInt(document.getElementById('max_articles').value);

        if (!keyword) {
            showError('Please enter a search keyword');
            return;
        }

        // Show loading state
        showLoading();
        hideError();
        hideResults();

        try {
            // Make API request
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    keyword: keyword,
                    days_back: daysBack,
                    max_articles: maxArticles
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Search failed');
            }

            // Display results
            displayResults(data);

        } catch (error) {
            console.error('Error:', error);
            showError(error.message || 'An error occurred while searching. Please try again.');
        } finally {
            hideLoading();
        }
    });

    function showLoading() {
        loadingIndicator.classList.remove('hidden');
        searchBtn.disabled = true;
        btnText.classList.add('hidden');
        btnLoading.classList.remove('hidden');
    }

    function hideLoading() {
        loadingIndicator.classList.add('hidden');
        searchBtn.disabled = false;
        btnText.classList.remove('hidden');
        btnLoading.classList.add('hidden');
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    function hideResults() {
        results.classList.add('hidden');
    }

    function displayResults(data) {
        // Display story summary
        displayStorySummary(data.story_summary, data.coverage_stats);

        // Display timeline
        displayTimeline(data.timeline);

        // Display articles
        displayArticles(data.articles);

        // Show results section
        results.classList.remove('hidden');

        // Scroll to results
        results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function displayStorySummary(summary, stats) {
        const storySummary = document.getElementById('storySummary');
        
        let html = `
            <div class="summary-text">
                <p>${escapeHtml(summary.summary)}</p>
            </div>
        `;

        if (summary.key_points && summary.key_points.length > 0) {
            html += `
                <div class="key-points">
                    <h3>🔑 Key Topics</h3>
                    <div class="tags">
                        ${summary.key_points.map(point => `<span class="tag">${escapeHtml(point)}</span>`).join('')}
                    </div>
                </div>
            `;
        }

        storySummary.innerHTML = html;

        // Display coverage stats
        const coverageStats = document.getElementById('coverageStats');
        coverageStats.innerHTML = `
            <div class="stat-item">
                <div class="stat-value">${stats.total_articles}</div>
                <div class="stat-label">Articles</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.unique_sources}</div>
                <div class="stat-label">Sources</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.date_span_days}</div>
                <div class="stat-label">Days</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.avg_articles_per_day}</div>
                <div class="stat-label">Avg/Day</div>
            </div>
        `;
    }

    function displayTimeline(timeline) {
        // Display Plotly chart
        if (timeline.chart_json) {
            const chartData = JSON.parse(timeline.chart_json);
            Plotly.newPlot('timelineChart', chartData.data, chartData.layout, {responsive: true});
        }

        // Display timeline events
        const timelineEvents = document.getElementById('timelineEvents');
        
        if (timeline.events && timeline.events.length > 0) {
            let html = '<h3 style="margin-bottom: 20px; color: var(--text-color);">📍 Key Events</h3>';
            
            timeline.events.forEach(event => {
                html += `
                    <div class="timeline-event">
                        <div class="event-date">${escapeHtml(event.date_formatted)}</div>
                        <div class="event-headline">${escapeHtml(event.main_headline)}</div>
                        <div class="event-meta">
                            ${event.article_count} article${event.article_count !== 1 ? 's' : ''} 
                            | ${escapeHtml(event.main_source)}
                        </div>
                `;
                
                if (event.articles && event.articles.length > 1) {
                    html += '<div class="event-articles">';
                    event.articles.forEach((article, idx) => {
                        if (idx < 3) { // Show max 3 articles per event
                            html += `
                                <a href="${escapeHtml(article.url)}" target="_blank" class="event-article-link">
                                    📄 ${escapeHtml(article.title)} (${escapeHtml(article.source)})
                                </a>
                            `;
                        }
                    });
                    html += '</div>';
                }
                
                html += '</div>';
            });
            
            timelineEvents.innerHTML = html;
        } else {
            timelineEvents.innerHTML = '<p>No timeline events available.</p>';
        }
    }

    function displayArticles(articles) {
        const articlesList = document.getElementById('articlesList');
        
        if (!articles || articles.length === 0) {
            articlesList.innerHTML = '<p>No articles found.</p>';
            return;
        }

        let html = '';
        articles.forEach(article => {
            html += `
                <div class="article-card">
                    <div class="article-header">
                        <div style="flex: 1;">
                            <h3 class="article-title">${escapeHtml(article.title)}</h3>
                        </div>
                        <div class="article-source">${escapeHtml(article.publisher)}</div>
                    </div>
                    <div class="article-date">📅 ${escapeHtml(article.published_date)}</div>
                    <div class="article-summary">
                        ${escapeHtml(article.summary || article.description)}
                    </div>
                    <a href="${escapeHtml(article.url)}" target="_blank" class="article-link">
                        Read Full Article →
                    </a>
                </div>
            `;
        });

        articlesList.innerHTML = html;
    }

    function escapeHtml(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
