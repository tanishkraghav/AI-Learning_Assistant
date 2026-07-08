// Tab Navigation
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName)?.classList.add('active');

    // Add active class to clicked nav item
    document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');
}

// Update current time
function updateTime() {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
    });
    const date = now.toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
    });
    document.getElementById('current-time').textContent = `${date} at ${time}`;
}

// Roadmap Form Handler
document.getElementById('roadmap-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const skillsInput = document.getElementById('skills').value.trim();
    const skillsList = skillsInput ? skillsInput.split(',').map(s => s.trim()) : ['None'];

    const formData = {
        goal_title: document.getElementById('goal').value,
        experience: document.getElementById('level').value,
        weekly_hours: parseInt(document.getElementById('hours').value),
        known_skills: skillsList,
        learning_style: "Mixed"
    };

    try {
        const response = await fetch('/roadmap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate roadmap');
        }

        const data = await response.json();
        displayRoadmap(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error: ' + error.message);
    }
});

function displayRoadmap(data) {
    const result = document.getElementById('roadmap-result');
    const content = document.getElementById('roadmap-content');

    const tasksList = (data.tasks || []).map(t => `
        <li style="margin: 10px 0;">
            <strong>${t.title}</strong> (${t.estimated_hours || 0} hours)
            ${t.subtasks && t.subtasks.length > 0 ? `
                <ul style="margin-left: 20px; margin-top: 5px;">
                    ${t.subtasks.map(s => `<li>${s.title}</li>`).join('')}
                </ul>
            ` : ''}
        </li>
    `).join('');

    content.innerHTML = `
        <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <p><strong>Roadmap ID:</strong> ${data.roadmap_id || 'N/A'}</p>
            <p><strong>Total Hours:</strong> ${data.estimated_hours || 0} hours</p>
            <p><strong>Recommended Skills:</strong> ${(data.skills || []).join(', ') || 'Various'}</p>
        </div>
        <h4>Learning Tasks:</h4>
        <ol style="margin-left: 20px;">
            ${tasksList}
        </ol>
    `;

    result.classList.remove('hidden');
    result.scrollIntoView({ behavior: 'smooth' });
}

// Project Form Handler
document.getElementById('project-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        goal_title: document.getElementById('project-topic').value,
        skills: ["Learning", "Development", "Problem-Solving"]
    };

    try {
        const response = await fetch('/project', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to get recommendations');
        }

        const data = await response.json();
        displayProjects(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error: ' + error.message);
    }
});

function displayProjects(data) {
    const result = document.getElementById('project-result');
    const content = document.getElementById('project-content');

    const featuresList = (data.features || []).map(f => `<li>${f}</li>`).join('');

    content.innerHTML = `
        <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h4>${data.title || 'Recommended Project'}</h4>
            <p><strong>Difficulty:</strong> ${data.difficulty || 'Intermediate'}</p>
            <p><strong>Time Required:</strong> ${data.estimated_hours || '20'} hours</p>
            <p><strong>Tech Stack:</strong> ${(data.tech_stack || []).join(', ') || 'Various'}</p>
        </div>
        <div style="margin: 15px 0;">
            <h4>Key Features to Build:</h4>
            <ul style="margin-left: 20px;">
                ${featuresList}
            </ul>
        </div>
        <div style="background: #ede9fe; padding: 15px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
            <h4>Why This Project?</h4>
            <p>${data.why_this_project || 'This project will help you practice and strengthen your skills.'}</p>
        </div>
    `;

    result.classList.remove('hidden');
    result.scrollIntoView({ behavior: 'smooth' });
}

// Chat Form Handler
document.getElementById('chat-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    // Add user message to chat
    addChatMessage(message, 'user');
    input.value = '';

    try {
        const response = await fetch('/chat/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: message })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to get response');
        }

        const data = await response.json();
        addChatMessage(data.answer || 'I understand your question. Let me help you with that.', 'bot');
    } catch (error) {
        console.error('Error:', error);
        addChatMessage('Sorry, I encountered an error: ' + error.message, 'bot');
    }
});

function addChatMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const p = document.createElement('p');
    p.textContent = text;

    messageDiv.appendChild(p);
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Nav Item Click Handlers
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = item.dataset.tab;
        switchTab(tab);
    });
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateTime();
    setInterval(updateTime, 60000); // Update time every minute

    // Set dashboard as active tab
    switchTab('dashboard');

    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            target?.scrollIntoView({ behavior: 'smooth' });
        });
    });
});

// API Health Check
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        console.log('API Health:', data);
        return true;
    } catch (error) {
        console.error('API Health Check Failed:', error);
        return false;
    }
}

// Check API on load
window.addEventListener('load', checkHealth);
