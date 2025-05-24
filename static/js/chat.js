// Chat functionality for AWS Bedrock Chat

document.addEventListener('DOMContentLoaded', function() {
    // Auto-scroll to bottom of chat messages
    const chatMessages = document.querySelector('.chat-messages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Add syntax highlighting for code blocks
    const messageContents = document.querySelectorAll('.message-content');
    messageContents.forEach(content => {
        // Simple code block detection and formatting
        let html = content.innerHTML;
        // Replace ```code``` blocks with <pre><code>code</code></pre>
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        // Replace `inline code` with <code>inline code</code>
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        content.innerHTML = html;
    });

    // Textarea auto-resize
    const messageTextarea = document.querySelector('textarea[name="message"]');
    if (messageTextarea) {
        messageTextarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }

    // Confirm deletion
    const deleteButtons = document.querySelectorAll('form[onsubmit*="confirm"]');
    deleteButtons.forEach(form => {
        form.addEventListener('submit', function(event) {
            const message = this.getAttribute('onsubmit').match(/confirm\('([^']+)'\)/)[1];
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });
});