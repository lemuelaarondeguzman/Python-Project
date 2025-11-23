// Main JavaScript for Survey System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Survey form progress tracking
    const surveyForm = document.getElementById('surveyForm');
    if (surveyForm) {
        const questions = surveyForm.querySelectorAll('.survey-question');
        const progressBar = document.createElement('div');
        progressBar.className = 'progress mb-3';
        progressBar.innerHTML = '<div class="progress-bar" role="progressbar" style="width: 0%"></div>';
        surveyForm.insertBefore(progressBar, surveyForm.firstChild);

        function updateProgress() {
            const answeredQuestions = Array.from(questions).filter(question => {
                const inputs = question.querySelectorAll('input, textarea');
                return Array.from(inputs).some(input => input.value.trim() !== '');
            }).length;

            const progress = (answeredQuestions / questions.length) * 100;
            const progressBarElement = progressBar.querySelector('.progress-bar');
            progressBarElement.style.width = progress + '%';
            progressBarElement.textContent = Math.round(progress) + '% Complete';
        }

        // Update progress on input change
        surveyForm.addEventListener('input', updateProgress);
        updateProgress(); // Initial progress
    }

    // Confirm survey submission
    const surveySubmitBtn = document.querySelector('button[type="submit"]');
    if (surveySubmitBtn && surveyForm) {
        surveyForm.addEventListener('submit', function(e) {
            const unansweredRequired = Array.from(surveyForm.querySelectorAll('[required]')).filter(input => !input.value.trim());
            if (unansweredRequired.length > 0) {
                e.preventDefault();
                alert('Please answer all required questions before submitting.');
                unansweredRequired[0].focus();
            }
        });
    }

    // Dynamic question type handling
    const questionTypeSelect = document.querySelector('select[name="question_type"]');
    if (questionTypeSelect) {
        questionTypeSelect.addEventListener('change', function() {
            const questionText = document.querySelector('textarea[name="question_text"]');
            if (questionText && !questionText.value.trim()) {
                const type = this.value;
                let placeholder = '';
                
                switch(type) {
                    case 'multiple_choice':
                        placeholder = 'What is your favorite color?\n\nOptions:\n- Red\n- Blue\n- Green\n- Yellow';
                        break;
                    case 'likert_scale':
                        placeholder = 'How satisfied are you with our service?\n\nScale: 1 (Very Dissatisfied) to 5 (Very Satisfied)';
                        break;
                    case 'short_answer':
                        placeholder = 'Please provide any additional comments or feedback.';
                        break;
                }
                
                questionText.placeholder = placeholder;
            }
        });
    }

    // Search functionality enhancement
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (this.value.length >= 2) {
                    // Auto-search after 2 characters
                    this.form.submit();
                }
            }, 500);
        });
    }

    // Chart responsiveness
    window.addEventListener('resize', function() {
        Chart.helpers.each(Chart.instances, function(chart) {
            chart.resize();
        });
    });

    // Delete confirmation
    window.deleteQuestion = function(questionId) {
        if (confirm('Are you sure you want to delete this question? This action cannot be undone.')) {
            fetch(`/teacher/question/${questionId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error deleting question. Please try again.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error deleting question. Please try again.');
            });
        }
    };

    // View response details (placeholder only if not provided elsewhere)
    if (typeof window.viewResponse !== 'function') {
        window.viewResponse = function(responseId) {
            const modal = new bootstrap.Modal(document.getElementById('responseModal'));
            const modalBody = document.getElementById('responseDetails');
            
            modalBody.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Loading response details...</p>
                </div>
            `;
            
            modal.show();
            
            // Simulate loading response details
            setTimeout(() => {
                modalBody.innerHTML = `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i>
                        <strong>Note:</strong> This is a placeholder for response details. 
                        In a full implementation, you would see the detailed answers to each question here.
                    </div>
                `;
            }, 1000);
        };
    }

    // Auto-refresh analytics (if on analytics page)
    if (window.location.pathname.includes('/analytics/')) {
        setInterval(() => {
            // Refresh analytics data every 30 seconds
            location.reload();
        }, 30000);
    }
});

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}
