document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const chatMessages = document.getElementById('chatMessages');
    const sendBtn = document.getElementById('sendBtn');
    const clearBtn = document.getElementById('clearBtn');

    // Make markdown links open in new tab
    const renderer = new marked.Renderer();
    renderer.link = function(href, title, text) {
        return `<a target="_blank" href="${href}">${text}</a>`;
    };
    marked.setOptions({ renderer: renderer });

    // Handle suggestion clicks
    window.useSuggestion = (element) => {
        userInput.value = element.innerText;
        userInput.focus();
    };

    // Auto scroll down
    const scrollToBottom = () => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    // Add a message to the UI
    const addMessage = (message, sender, meta = null) => {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender);
        
        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('avatar');
        
        if (sender === 'user') {
            avatarDiv.innerHTML = '<i class="ph ph-user"></i>';
        } else {
            avatarDiv.innerHTML = '<i class="ph ph-robot"></i>';
        }

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('content');
        
        // Parse markdown immediately for bot if present, raw text for user
        if (sender === 'bot') {
            contentDiv.innerHTML = marked.parse(message);
            
            // Append Raw Data & SQL if provided
            if (meta && (meta.sql_query || meta.raw_data)) {
                const details = document.createElement('details');
                details.classList.add('meta-details');
                details.innerHTML = `<summary><i class="ph ph-code"></i> View Source Query & Data</summary>`;
                
                if (meta.sql_query) {
                    // Extract query from dict string if it resembles {'query': 'SELECT...'}
                    let sqlStr = meta.sql_query;
                    try {
                         // LangChain tool_input sometimes comes as a stringified dict
                         if(sqlStr.startsWith("{") && sqlStr.includes("query")) {
                             const parseAttempt = sqlStr.replace(/'/g, '"');
                             const obj = JSON.parse(parseAttempt);
                             if(obj.query) sqlStr = obj.query;
                         }
                    } catch(e) {}
                    
                    details.innerHTML += `<h4>Generated SQL</h4><pre><code>${sqlStr}</code></pre>`;
                }
                
                if (meta.raw_data) {
                    details.innerHTML += `<h4>Raw Execution Result</h4><pre><code>${meta.raw_data}</code></pre>`;
                }
                contentDiv.appendChild(details);
            }
        } else {
            const p = document.createElement('p');
            p.textContent = message;
            contentDiv.appendChild(p);
        }

        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
        
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    };

    const toggleLoading = (show) => {
        if (show) {
            const loadingDiv = document.createElement('div');
            loadingDiv.classList.add('message', 'bot');
            loadingDiv.id = 'loadingIndicator';
            
            loadingDiv.innerHTML = `
                <div class="avatar"><i class="ph ph-robot"></i></div>
                <div class="content">
                    <div class="typing-indicator">
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                    </div>
                </div>
            `;
            chatMessages.appendChild(loadingDiv);
            scrollToBottom();
        } else {
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.remove();
            }
        }
    };

    clearBtn.addEventListener('click', () => {
        if(confirm("Apakah Anda yakin ingin menghapus semua pesan?")) {
            // Keep the first welcome message
            const welcome = chatMessages.firstElementChild;
            chatMessages.innerHTML = '';
            chatMessages.appendChild(welcome);
        }
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const question = userInput.value.trim();
        if (!question) return;

        // UI updates
        addMessage(question, 'user');
        userInput.value = '';
        sendBtn.disabled = true;
        toggleLoading(true);

        try {
            // Adjust port logic depending on how UI is served.
            // If served via the same FastAPI instance, we can use relative path "/query"
            const baseUrl = window.location.origin;
            
            const response = await fetch(`${baseUrl}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: question })
            });
            
            const data = await response.json();
            toggleLoading(false);
            
            if (data.error) {
                let errText = `**Error:** ${data.error}`;
                if (data.detail) errText += `\n\n*Detail: ${data.detail}*`;
                addMessage(errText, 'bot', data);
            } else {
                addMessage(data.answer, 'bot', data);
            }

        } catch (error) {
            console.error("Fetch Error:", error);
            toggleLoading(false);
            addMessage("**Error:** Koneksi ke server gagal. Pastikan aplikasi berjalan dan port sudah benar.", 'bot');
        } finally {
            sendBtn.disabled = false;
            userInput.focus();
        }
    });
});
