// script.js

// ...existing code...

async function createJiraStory() {
    // ...existing code...
    
    try {
        showLoading();
        
        // Add retry logic for network requests
        const response = await fetchWithRetry('/create_story', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                summary: summary,
                description: description,
                story_points: storyPoints
            })
        }, 3); // Retry up to 3 times

        // ...existing code...
    } catch (error) {
        console.error('Error creating JIRA story:', error);
        showError('Failed to create JIRA story. Please check if the server is running and try again.');
    } finally {
        hideLoading();
    }
}

// Add retry function for network requests
async function fetchWithRetry(url, options, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(url, options);
            if (response.ok) {
                return response;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        } catch (error) {
            console.log(`Attempt ${i + 1} failed:`, error.message);
            
            if (i === maxRetries - 1) {
                throw error;
            }
            
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 1.5; // Exponential backoff
        }
    }
}

// ...existing code...