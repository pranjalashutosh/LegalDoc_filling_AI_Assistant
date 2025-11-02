/**
 * Preview Page Logic
 * Handles document preview display and download functionality
 */

class PreviewPage {
    constructor() {
        this.zoomLevel = 100; // Percentage
        this.previewGenerated = false;
        
        // DOM elements
        this.loadingSection = document.getElementById('loading-section');
        this.previewSection = document.getElementById('preview-section');
        this.errorSection = document.getElementById('error-section');
        this.errorMessageText = document.getElementById('error-message-text');
        
        // Preview elements
        this.documentName = document.getElementById('document-name');
        this.placeholdersFilled = document.getElementById('placeholders-filled');
        this.previewIframe = document.getElementById('preview-iframe');
        this.previewContainer = document.getElementById('preview-container');
        
        // Zoom controls
        this.zoomInBtn = document.getElementById('zoom-in-btn');
        this.zoomOutBtn = document.getElementById('zoom-out-btn');
        this.zoomLevelEl = document.getElementById('zoom-level');
        
        // Action buttons
        this.editValuesBtn = document.getElementById('edit-values-btn');
        this.downloadBtn = document.getElementById('download-btn');
        this.returnConversationBtn = document.getElementById('return-conversation-btn');
        this.returnHomeBtn = document.getElementById('return-home-btn');
        
        // Success message
        this.downloadSuccess = document.getElementById('download-success');
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadPreview();
    }

    setupEventListeners() {
        // Zoom controls
        this.zoomInBtn.addEventListener('click', () => this.zoomIn());
        this.zoomOutBtn.addEventListener('click', () => this.zoomOut());
        
        // Action buttons
        this.editValuesBtn.addEventListener('click', () => this.editValues());
        this.downloadBtn.addEventListener('click', () => this.downloadDocument());
        
        // Error section buttons
        this.returnConversationBtn.addEventListener('click', () => this.returnToConversation());
        this.returnHomeBtn.addEventListener('click', () => this.returnToHome());
    }

    /**
     * Load and display the document preview
     */
    async loadPreview() {
        try {
            // Check if preview already exists
            const statusResponse = await api.get('/api/preview/status');
            
            if (statusResponse.has_preview) {
                // Preview already generated, just load it
                await this.displayPreview();
            } else {
                // Generate new preview
                await this.generateAndDisplayPreview();
            }
            
        } catch (error) {
            console.error('Error loading preview:', error);
            this.showError(
                error instanceof APIError 
                    ? error.getUserMessage() 
                    : 'Failed to load preview. Please try again.'
            );
        }
    }

    /**
     * Generate a new preview from the server
     */
    async generateAndDisplayPreview() {
        try {
            // Call API to generate preview
            const response = await api.post('/api/preview/generate', {});
            
            if (response.success) {
                this.previewGenerated = true;
                
                // Update document info
                const filename = response.filename || 'document.docx';
                const totalReplacements = response.total_replacements || 0;
                
                this.documentName.textContent = filename;
                this.placeholdersFilled.textContent = totalReplacements;
                
                // Load and display the HTML preview
                await this.displayPreview();
            } else {
                throw new Error(response.error || 'Failed to generate preview');
            }
            
        } catch (error) {
            console.error('Error generating preview:', error);
            throw error;
        }
    }

    /**
     * Display the HTML preview in the iframe
     */
    async displayPreview() {
        try {
            // Fetch the HTML content
            const response = await fetch('/api/preview/html');
            
            if (!response.ok) {
                throw new Error('Failed to load preview HTML');
            }
            
            const htmlContent = await response.text();
            
            // Write HTML to iframe
            const iframeDoc = this.previewIframe.contentDocument || this.previewIframe.contentWindow.document;
            iframeDoc.open();
            iframeDoc.write(htmlContent);
            iframeDoc.close();
            
            // Get document info if not already set
            if (this.documentName.textContent === '-') {
                const answers = session.getSessionData('answers') || {};
                const detectionResult = session.getSessionData('detection_result') || {};
                
                this.documentName.textContent = detectionResult.filename || 'document.docx';
                this.placeholdersFilled.textContent = Object.keys(answers).length;
            }
            
            // Show preview section
            this.showPreview();
            
        } catch (error) {
            console.error('Error displaying preview:', error);
            throw error;
        }
    }

    /**
     * Zoom in on the preview
     */
    zoomIn() {
        if (this.zoomLevel < 200) {
            this.zoomLevel += 10;
            this.applyZoom();
        }
    }

    /**
     * Zoom out on the preview
     */
    zoomOut() {
        if (this.zoomLevel > 50) {
            this.zoomLevel -= 10;
            this.applyZoom();
        }
    }

    /**
     * Apply current zoom level to iframe
     */
    applyZoom() {
        const scale = this.zoomLevel / 100;
        
        // Update iframe scale
        this.previewIframe.style.transform = `scale(${scale})`;
        this.previewIframe.style.transformOrigin = 'top left';
        
        // Adjust container height to accommodate scaling
        const baseHeight = 60; // vh
        const scaledHeight = baseHeight * scale;
        this.previewContainer.style.maxHeight = `${scaledHeight}vh`;
        
        // Update zoom level display
        this.zoomLevelEl.textContent = `${this.zoomLevel}%`;
    }

    /**
     * Edit values - return to conversation page
     */
    editValues() {
        // Don't clear session, just navigate back
        window.location.href = '/static/conversation.html';
    }

    /**
     * Download the completed document
     */
    async downloadDocument() {
        try {
            loading.show(this.downloadBtn, { text: 'Preparing download...' });
            
            // Check download status
            const statusResponse = await api.get('/api/download/status');
            
            if (!statusResponse.is_available) {
                throw new Error('Document not available for download. Please regenerate preview.');
            }
            
            // Initiate download by opening the download URL
            const downloadUrl = '/api/download';
            
            // Create a temporary link and click it
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = statusResponse.filename || 'document.docx';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            loading.hide(this.downloadBtn);
            
            // Show success message
            Utils.show(this.downloadSuccess);
            
            // Hide success message after 5 seconds
            setTimeout(() => {
                Utils.hide(this.downloadSuccess);
            }, 5000);
            
            logger.info('Document download initiated');
            
        } catch (error) {
            console.error('Error downloading document:', error);
            loading.hide(this.downloadBtn);
            
            alert(
                error instanceof APIError 
                    ? error.getUserMessage() 
                    : 'Failed to download document. Please try again.'
            );
        }
    }

    /**
     * Show preview section
     */
    showPreview() {
        Utils.hide(this.loadingSection);
        Utils.hide(this.errorSection);
        Utils.show(this.previewSection);
    }

    /**
     * Show error section
     */
    showError(message) {
        this.errorMessageText.textContent = message;
        
        Utils.hide(this.loadingSection);
        Utils.hide(this.previewSection);
        Utils.show(this.errorSection);
    }

    /**
     * Return to conversation page
     */
    returnToConversation() {
        window.location.href = '/static/conversation.html';
    }

    /**
     * Return to home page
     */
    returnToHome() {
        window.location.href = '/static/index.html';
    }
}

// Initialize preview page when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new PreviewPage();
});

