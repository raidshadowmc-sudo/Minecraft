// Gallery functionality
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = uploadProgress.querySelector('.progress-bar');
    const fileInput = document.getElementById('fileInput');
    const imageModal = new bootstrap.Modal(document.getElementById('imageModal'));
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    const gridViewBtn = document.getElementById('gridView');
    const listViewBtn = document.getElementById('listView');
    const imageGrid = document.getElementById('imageGrid');
    
    let currentImageFilename = null;
    
    // View mode handling
    if (gridViewBtn && listViewBtn) {
        gridViewBtn.addEventListener('click', function() {
            setViewMode('grid');
        });
        
        listViewBtn.addEventListener('click', function() {
            setViewMode('list');
        });
        
        // Initialize with grid view
        setViewMode('grid');
    }
    
    function setViewMode(mode) {
        if (mode === 'grid') {
            imageGrid.classList.remove('list-view');
            gridViewBtn.classList.add('active');
            listViewBtn.classList.remove('active');
        } else {
            imageGrid.classList.add('list-view');
            listViewBtn.classList.add('active');
            gridViewBtn.classList.remove('active');
        }
        localStorage.setItem('galleryViewMode', mode);
    }
    
    // Restore view mode from localStorage
    const savedViewMode = localStorage.getItem('galleryViewMode');
    if (savedViewMode && (gridViewBtn && listViewBtn)) {
        setViewMode(savedViewMode);
    }
    
    // File input validation
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (!file) return;
        
        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            showAlert('Invalid file type. Please select a PNG, JPG, JPEG, or GIF image.', 'danger');
            this.value = '';
            return;
        }
        
        // Validate file size (16MB)
        const maxSize = 16 * 1024 * 1024;
        if (file.size > maxSize) {
            showAlert('File is too large. Maximum file size is 16MB.', 'danger');
            this.value = '';
            return;
        }
        
        // Update upload button text
        uploadBtn.innerHTML = `<i class="fas fa-upload me-2"></i>Upload "${file.name}"`;
    });
    
    // Upload form handling
    uploadForm.addEventListener('submit', function(e) {
        const file = fileInput.files[0];
        if (!file) {
            e.preventDefault();
            showAlert('Please select a file to upload.', 'danger');
            return;
        }
        
        // Show upload progress
        showUploadProgress();
        
        // Simulate progress (since we can't track actual progress with form submission)
        simulateProgress();
    });
    
    function showUploadProgress() {
        uploadProgress.style.display = 'block';
        uploadBtn.disabled = true;
        fileInput.disabled = true;
        document.body.classList.add('uploading');
    }
    
    function hideUploadProgress() {
        uploadProgress.style.display = 'none';
        progressBar.style.width = '0%';
        uploadBtn.disabled = false;
        fileInput.disabled = false;
        document.body.classList.remove('uploading');
        uploadBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Upload Image';
    }
    
    function simulateProgress() {
        let progress = 0;
        const interval = setInterval(function() {
            progress += Math.random() * 30;
            if (progress > 90) progress = 90;
            progressBar.style.width = progress + '%';
            
            if (progress >= 90) {
                clearInterval(interval);
            }
        }, 200);
        
        // Hide progress after form submission is complete
        setTimeout(hideUploadProgress, 3000);
    }
    
    // Image modal handling
    document.addEventListener('click', function(e) {
        if (e.target.matches('.card-img-top')) {
            const imgSrc = e.target.dataset.src;
            const filename = e.target.dataset.filename;
            
            document.getElementById('modalImage').src = imgSrc;
            document.getElementById('modalImageTitle').textContent = filename;
            currentImageFilename = filename;
        }
    });
    
    // Modal delete button
    document.getElementById('modalDeleteBtn').addEventListener('click', function() {
        if (currentImageFilename) {
            showDeleteConfirmation(currentImageFilename);
            imageModal.hide();
        }
    });
    
    // Delete button handling
    document.addEventListener('click', function(e) {
        if (e.target.matches('.delete-btn') || e.target.closest('.delete-btn')) {
            e.stopPropagation();
            const btn = e.target.matches('.delete-btn') ? e.target : e.target.closest('.delete-btn');
            const filename = btn.dataset.filename;
            showDeleteConfirmation(filename);
        }
    });
    
    function showDeleteConfirmation(filename) {
        document.getElementById('deleteImageName').textContent = filename;
        currentImageFilename = filename;
        deleteModal.show();
    }
    
    // Confirm delete
    document.getElementById('confirmDeleteBtn').addEventListener('click', function() {
        if (currentImageFilename) {
            deleteImage(currentImageFilename);
        }
    });
    
    function deleteImage(filename) {
        const deleteBtn = document.getElementById('confirmDeleteBtn');
        const originalText = deleteBtn.innerHTML;
        
        // Show loading state
        deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Deleting...';
        deleteBtn.disabled = true;
        
        fetch(`/delete/${filename}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove the image card from DOM
                const imageCards = document.querySelectorAll('.image-card');
                imageCards.forEach(card => {
                    const img = card.querySelector('img');
                    if (img && img.dataset.filename === filename) {
                        card.closest('.image-item').remove();
                    }
                });
                
                showAlert('Image deleted successfully!', 'success');
                
                // Check if no images left
                if (document.querySelectorAll('.image-item').length === 0) {
                    location.reload();
                }
            } else {
                showAlert(data.message || 'Failed to delete image.', 'danger');
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            showAlert('An error occurred while deleting the image.', 'danger');
        })
        .finally(() => {
            // Reset button state
            deleteBtn.innerHTML = originalText;
            deleteBtn.disabled = false;
            deleteModal.hide();
            currentImageFilename = null;
        });
    }
    
    function showAlert(message, type) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            <i class="fas fa-${type === 'danger' ? 'exclamation-circle' : 'check-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Find container to insert alert
        const container = document.querySelector('.container');
        const firstRow = container.querySelector('.row');
        
        // Create wrapper for alert
        const alertWrapper = document.createElement('div');
        alertWrapper.className = 'row mb-3';
        alertWrapper.innerHTML = '<div class="col-12"></div>';
        alertWrapper.querySelector('.col-12').appendChild(alertDiv);
        
        // Insert after header
        firstRow.parentNode.insertBefore(alertWrapper, firstRow.nextSibling);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                const alert = new bootstrap.Alert(alertDiv);
                alert.close();
            }
        }, 5000);
    }
    
    // Handle page load completion
    window.addEventListener('load', function() {
        hideUploadProgress();
    });
    
    // Handle back/forward navigation
    window.addEventListener('pageshow', function() {
        hideUploadProgress();
        fileInput.value = '';
    });
});
