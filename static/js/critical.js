// Critical JavaScript - Minimal functionality for fast loading

// Basic initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎮 Elite Squad - Fast mode initialized');
    
    // Initialize basic leaderboard functionality
    initializeBasicLeaderboard();
    
    // Load full functionality after page is loaded
    setTimeout(loadFullFeatures, 100);
});

function initializeBasicLeaderboard() {
    // Basic leaderboard functionality without heavy animations
    const leaderboardTable = document.querySelector('.leaderboard-table');
    if (leaderboardTable) {
        // Simple row hover effects
        const rows = leaderboardTable.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'rgba(40, 167, 69, 0.1)';
            });
            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });
    }
    
    // Initialize search functionality
    const searchInput = document.querySelector('#searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll('.leaderboard-table tbody tr');
            
            rows.forEach(row => {
                const playerName = row.querySelector('.player-name');
                if (playerName) {
                    const name = playerName.textContent.toLowerCase();
                    row.style.display = name.includes(searchTerm) ? '' : 'none';
                }
            });
        });
    }
}

function loadFullFeatures() {
    // Load full JavaScript functionality after initial load
    const script = document.createElement('script');
    script.src = '/static/js/main.js';
    script.onload = function() {
        console.log('🚀 Full features loaded');
    };
    document.head.appendChild(script);
}

// Global functions for immediate use
window.showPlayerDetails = function(playerId) {
    // Simple fallback until full features load
    console.log('Loading player details for ID:', playerId);
    if (window.showPlayerDetailsFullVersion) {
        window.showPlayerDetailsFullVersion(playerId);
    } else {
        // Show loading message
        alert('Загрузка данных игрока...');
        setTimeout(() => {
            if (window.showPlayerDetailsFullVersion) {
                window.showPlayerDetailsFullVersion(playerId);
            }
        }, 1000);
    }
};

// Basic modal functionality
function showBasicModal(title, content) {
    let modal = document.getElementById('basicModal');
    if (!modal) {
        modal = createBasicModal();
    }
    
    modal.querySelector('.modal-title').textContent = title;
    modal.querySelector('.modal-body').innerHTML = content;
    
    if (window.bootstrap) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    } else {
        modal.style.display = 'block';
        modal.classList.add('show');
    }
}

function createBasicModal() {
    const modal = document.createElement('div');
    modal.id = 'basicModal';
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"></h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body"></div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    return modal;
}

// Performance optimization - reduce DOM queries
const cache = {
    elements: new Map(),
    get: function(selector) {
        if (!this.elements.has(selector)) {
            this.elements.set(selector, document.querySelector(selector));
        }
        return this.elements.get(selector);
    }
};

// Simple animation frame batching for better performance
let scheduledUpdates = [];
let isUpdateScheduled = false;

function batchUpdate(callback) {
    scheduledUpdates.push(callback);
    if (!isUpdateScheduled) {
        isUpdateScheduled = true;
        requestAnimationFrame(() => {
            scheduledUpdates.forEach(cb => cb());
            scheduledUpdates = [];
            isUpdateScheduled = false;
        });
    }
}