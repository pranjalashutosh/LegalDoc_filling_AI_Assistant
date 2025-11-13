/**
 * Upload Page Logic
 * Handles file selection, validation, upload, and placeholder detection
 */

class UploadPage {
    constructor() {
        this.selectedFile = null;
        this.placeholderData = null;
        
        // DOM elements
        this.dropZone = document.getElementById('drop-zone');
        this.fileInput = document.getElementById('file-input');
        this.selectedFileDisplay = document.getElementById('selected-file');
        this.fileName = document.getElementById('file-name');
        this.fileSize = document.getElementById('file-size');
        this.removeFileBtn = document.getElementById('remove-file');
        this.uploadBtn = document.getElementById('upload-btn');
        this.errorMessage = document.getElementById('error-message');
        this.errorText = document.getElementById('error-text');
        
        // Sections
        this.uploadSection = document.getElementById('upload-section');
        this.processingSection = document.getElementById('processing-section');
        this.resultsSection = document.getElementById('results-section');
        
        // Processing elements
        this.processingTitle = document.getElementById('processing-title');
        this.processingDescription = document.getElementById('processing-description');
        
        // Results elements
        this.uniqueCount = document.getElementById('unique-count');
        this.totalCount = document.getElementById('total-count');
        this.patternsDetected = document.getElementById('patterns-detected');
        this.llmToggle = document.getElementById('llm-toggle');
        this.startFillingBtn = document.getElementById('start-filling-btn');
        this.uploadAnotherBtn = document.getElementById('upload-another-btn');
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkExistingSession();
    }

    setupEventListeners() {
        // File input
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag and drop
        this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Remove file
        this.removeFileBtn.addEventListener('click', () => this.clearSelectedFile());
        
        // Upload button
        this.uploadBtn.addEventListener('click', () => this.handleUpload());
        
        // Results actions
        this.startFillingBtn.addEventListener('click', () => this.navigateToConversation());
        this.uploadAnotherBtn.addEventListener('click', () => this.resetToUpload());
    }

    /**
     * Check if there's an existing session with detected placeholders
     */
    checkExistingSession() {
        const placeholders = session.getSessionData('placeholders');
        if (placeholders && placeholders.length > 0) {
            // Session exists, show results
            this.placeholderData = session.getSessionData('detection_result');
            this.showResults();
        }
    }

    /**
     * Handle file selection from input
     */
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.validateAndSetFile(file);
        }
    }

    /**
     * Handle drag over event
     */
    handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dropZone.classList.add('drag-over');
    }

    /**
     * Handle drag leave event
     */
    handleDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dropZone.classList.remove('drag-over');
    }

    /**
     * Handle file drop event
     */
    handleDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dropZone.classList.remove('drag-over');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.validateAndSetFile(files[0]);
        }
    }

    /**
     * Validate file and set as selected
     */
    validateAndSetFile(file) {
        this.hideError();
        
        // Validate extension
        if (!Utils.validateFileExtension(file.name, ['.docx'])) {
            this.showError('Invalid file type. Please upload a .docx file.');
            return;
        }
        
        // Validate size (5 MB)
        if (!Utils.validateFileSize(file.size, 5)) {
            this.showError('File is too large. Maximum size is 5 MB.');
            return;
        }
        
        // Set as selected file
        this.selectedFile = file;
        this.displaySelectedFile(file);
    }

    /**
     * Display selected file information
     */
    displaySelectedFile(file) {
        this.fileName.textContent = file.name;
        this.fileSize.textContent = Utils.formatFileSize(file.size);
        
        Utils.hide(this.dropZone);
        Utils.show(this.selectedFileDisplay);
        
        this.uploadBtn.disabled = false;
    }

    /**
     * Clear selected file
     */
    clearSelectedFile() {
        this.selectedFile = null;
        this.fileInput.value = '';
        
        Utils.hide(this.selectedFileDisplay);
        Utils.show(this.dropZone);
        
        this.uploadBtn.disabled = true;
        this.hideError();
    }

    /**
     * Show error message
     */
    showError(message) {
        this.errorText.textContent = message;
        Utils.show(this.errorMessage);
    }

    /**
     * Hide error message
     */
    hideError() {
        Utils.hide(this.errorMessage);
        this.errorText.textContent = '';
    }

    /**
     * Handle upload button click
     */
    async handleUpload() {
        if (!this.selectedFile) return;
        
        this.hideError();
        this.showProcessing('Uploading your document...', 'Please wait while we upload and analyze your file');
        
        try {
            // Step 1: Upload file
            await this.uploadFile();
            
            // Step 2: Detect placeholders
            this.updateProcessing('Analyzing document...', 'Detecting placeholders in your document');
            await this.detectPlaceholders();
            
            // Step 3: Show results
            this.showResults();
            
        } catch (error) {
            console.error('Upload error:', error);
            this.handleUploadError(error);
        }
    }

    /**
     * Upload file to server
     */
    async uploadFile() {
        const formData = new FormData();
        formData.append('file', this.selectedFile);
        
        const response = await api.post('/api/upload', formData);
        
        if (response.success) {
            // Store filename in session
            session.setSessionData('filename', response.filename);
            return response;
        } else {
            throw new Error(response.error || 'Upload failed');
        }
    }

    /**
     * Detect placeholders in uploaded file
     */
    async detectPlaceholders() {
        const response = await api.post('/api/detect', {});
        
        if (response.success) {
            // Normalize API response for frontend usage
            // Extract placeholder names array from object map
            const placeholderMap = response.placeholders || {};
            const placeholderNames = Array.isArray(placeholderMap)
                ? placeholderMap
                : Object.keys(placeholderMap);

            // Persist in session for conversation flow
            session.setSessionData('placeholders', placeholderNames);
            session.setSessionData('detection_result', response);

            // Cache locally
            this.placeholderData = response;
            return response;
        } else {
            throw new Error(response.error || 'Detection failed');
        }
    }

    /**
     * Show processing section
     */
    showProcessing(title, description) {
        this.processingTitle.textContent = title;
        this.processingDescription.textContent = description;
        
        Utils.hide(this.uploadSection);
        Utils.hide(this.resultsSection);
        Utils.show(this.processingSection);
    }

    /**
     * Update processing text
     */
    updateProcessing(title, description) {
        this.processingTitle.textContent = title;
        this.processingDescription.textContent = description;
    }

    /**
     * Show results section
     */
    showResults() {
        if (!this.placeholderData) {
            console.error('No placeholder data available');
            return;
        }
        
        // Update counts from API summary shape
        const summary = this.placeholderData.summary || {};
        this.uniqueCount.textContent = summary.total_unique || 0;
        this.totalCount.textContent = summary.total_occurrences || 0;

        // Aggregate pattern types from grouped metadata
        const grouped = this.placeholderData.grouped || (summary.grouped || {});
        const patternSet = new Set();
        Object.values(grouped || {}).forEach(g => {
            (g.patterns || []).forEach(p => patternSet.add(p));
        });
        const patterns = Array.from(patternSet);
        this.patternsDetected.textContent = patterns.length > 0 ? patterns.join(', ') : 'None';
        
        // Show results section
        Utils.hide(this.uploadSection);
        Utils.hide(this.processingSection);
        Utils.show(this.resultsSection);
    }

    /**
     * Handle upload errors
     */
    handleUploadError(error) {
        // Return to upload section
        Utils.hide(this.processingSection);
        Utils.show(this.uploadSection);
        
        // Show error message
        let errorMessage = 'An error occurred during upload. Please try again.';
        
        if (error instanceof APIError) {
            errorMessage = error.getUserMessage();
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        this.showError(errorMessage);
    }

    /**
     * Navigate to conversation page
     */
    navigateToConversation() {
        // Store LLM preference
        const useLLM = this.llmToggle.checked;
        session.setSessionData('enable_llm', useLLM);
        
        // Navigate to conversation page
        window.location.href = '/static/conversation.html';
    }

    /**
     * Reset to upload state
     */
    async resetToUpload() {
        // Clear session
        try {
            await api.post('/api/upload/clear', {});
        } catch (error) {
            console.error('Error clearing session:', error);
        }
        
        session.clearSession();
        
        // Reset UI
        this.clearSelectedFile();
        this.placeholderData = null;
        
        Utils.hide(this.resultsSection);
        Utils.hide(this.processingSection);
        Utils.show(this.uploadSection);
    }
}

// Initialize upload page when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new UploadPage();
});

