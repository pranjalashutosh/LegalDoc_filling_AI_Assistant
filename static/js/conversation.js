/**
 * Conversation Page Logic
 * Handles the conversational flow for filling placeholders
 */

class ConversationPage {
    constructor() {
        this.placeholders = [];
        this.currentIndex = 0;
        this.answers = {};
        this.useLLM = true;
        this.currentQuestion = null;
        
        // DOM elements
        this.loadingSection = document.getElementById('loading-section');
        this.conversationSection = document.getElementById('conversation-section');
        this.errorSection = document.getElementById('error-section');
        this.errorMessageText = document.getElementById('error-message-text');
        
        // Progress elements
        this.currentIndexEl = document.getElementById('current-index');
        this.totalCountEl = document.getElementById('total-count');
        this.progressBarFill = document.getElementById('progress-bar-fill');
        
        // Question and answer elements
        this.questionText = document.getElementById('question-text');
        this.answerInput = document.getElementById('answer-input');
        this.inputHint = document.getElementById('input-hint');
        this.answerError = document.getElementById('answer-error');
        this.answerErrorText = document.getElementById('answer-error-text');
        
        // LLM status
        this.llmStatus = document.getElementById('llm-status');
        
        // Buttons
        this.backBtn = document.getElementById('back-btn');
        this.nextBtn = document.getElementById('next-btn');
        this.returnHomeBtn = document.getElementById('return-home-btn');
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadSessionData();
    }

    setupEventListeners() {
        // Answer input
        this.answerInput.addEventListener('input', () => this.handleInputChange());
        this.answerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.nextBtn.disabled) {
                this.handleNext();
            }
        });
        
        // Navigation buttons
        this.backBtn.addEventListener('click', () => this.handleBack());
        this.nextBtn.addEventListener('click', () => this.handleNext());
        
        // Error section
        this.returnHomeBtn.addEventListener('click', () => this.returnToHome());
    }

    /**
     * Load session data and initialize conversation
     */
    async loadSessionData() {
        try {
            // Get placeholders from session
            const placeholders = session.getSessionData('placeholders');
            const enableLLM = session.getSessionData('enable_llm');
            
            if (!placeholders || placeholders.length === 0) {
                throw new Error('No placeholders found. Please upload a document first.');
            }
            
            this.placeholders = placeholders;
            this.useLLM = enableLLM !== false; // Default to true if not set
            
            // Get existing answers if any
            const existingAnswers = session.getSessionData('answers');
            if (existingAnswers) {
                this.answers = existingAnswers;
            }
            
            // Show LLM status if enabled
            if (this.useLLM) {
                Utils.show(this.llmStatus);
            }
            
            // Start conversation
            this.showConversation();
            await this.loadQuestion();
            
        } catch (error) {
            console.error('Error loading session:', error);
            this.showError(error.message);
        }
    }

    /**
     * Load question for current placeholder
     */
    async loadQuestion() {
        const currentPlaceholder = this.placeholders[this.currentIndex];
        
        try {
            // Update UI
            this.updateProgress();
            this.answerInput.value = this.answers[currentPlaceholder] || '';
            this.handleInputChange(); // Update button state
            
            // Show loading state in question
            this.questionText.textContent = 'Loading question...';
            
            // Fetch question from API
            const response = await api.get(
                `/api/conversation/next?placeholder=${encodeURIComponent(currentPlaceholder)}&use_llm=${this.useLLM}`
            );
            
            if (response.success) {
                this.currentQuestion = response.question;
                this.questionText.textContent = response.question;
                
                // Focus on input
                this.answerInput.focus();
            } else {
                throw new Error(response.error || 'Failed to load question');
            }
            
        } catch (error) {
            console.error('Error loading question:', error);
            
            // Fallback to simple question
            const fallbackQuestion = `Please provide: ${currentPlaceholder}`;
            this.currentQuestion = fallbackQuestion;
            this.questionText.textContent = fallbackQuestion;
            
            this.answerInput.focus();
        }
    }

    /**
     * Update progress bar and counters
     */
    updateProgress() {
        const current = this.currentIndex + 1;
        const total = this.placeholders.length;
        const percentage = (this.currentIndex / total) * 100;
        
        this.currentIndexEl.textContent = current;
        this.totalCountEl.textContent = total;
        this.progressBarFill.style.width = `${percentage}%`;
        
        // Update back button state
        this.backBtn.disabled = this.currentIndex === 0;
    }

    /**
     * Handle input change
     */
    handleInputChange() {
        const value = this.answerInput.value.trim();
        
        // Enable/disable next button
        this.nextBtn.disabled = value.length === 0;
        
        // Hide error
        if (value.length > 0) {
            this.hideAnswerError();
        }
    }

    /**
     * Handle next button click
     */
    async handleNext() {
        const value = this.answerInput.value.trim();
        
        // Validate input
        if (value.length === 0) {
            this.showAnswerError('Please provide an answer');
            return;
        }
        
        // Store answer
        const currentPlaceholder = this.placeholders[this.currentIndex];
        this.answers[currentPlaceholder] = value;
        
        // Save to session
        session.setSessionData('answers', this.answers);
        
        try {
            // Submit answer to server
            loading.show(this.nextBtn, { text: 'Saving...' });
            
            await api.post('/api/conversation/answer', {
                placeholder: currentPlaceholder,
                answer: value
            });
            
            loading.hide(this.nextBtn);
            
            // Move to next question or finish
            if (this.currentIndex < this.placeholders.length - 1) {
                this.currentIndex++;
                await this.loadQuestion();
            } else {
                // All done, navigate to preview
                this.navigateToPreview();
            }
            
        } catch (error) {
            console.error('Error submitting answer:', error);
            loading.hide(this.nextBtn);
            
            // Still proceed locally even if server fails
            if (this.currentIndex < this.placeholders.length - 1) {
                this.currentIndex++;
                await this.loadQuestion();
            } else {
                this.navigateToPreview();
            }
        }
    }

    /**
     * Handle back button click
     */
    async handleBack() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            await this.loadQuestion();
        }
    }

    /**
     * Show answer validation error
     */
    showAnswerError(message) {
        this.answerErrorText.textContent = message;
        Utils.show(this.answerError);
        this.answerInput.classList.add('error');
    }

    /**
     * Hide answer validation error
     */
    hideAnswerError() {
        Utils.hide(this.answerError);
        this.answerInput.classList.remove('error');
    }

    /**
     * Navigate to preview page
     */
    navigateToPreview() {
        session.setSessionData('current_index', this.currentIndex);
        window.location.href = '/static/preview.html';
    }

    /**
     * Show conversation section
     */
    showConversation() {
        Utils.hide(this.loadingSection);
        Utils.hide(this.errorSection);
        Utils.show(this.conversationSection);
    }

    /**
     * Show error section
     */
    showError(message) {
        this.errorMessageText.textContent = message;
        
        Utils.hide(this.loadingSection);
        Utils.hide(this.conversationSection);
        Utils.show(this.errorSection);
    }

    /**
     * Return to home page
     */
    returnToHome() {
        window.location.href = '/static/index.html';
    }
}

// Initialize conversation page when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ConversationPage();
});

