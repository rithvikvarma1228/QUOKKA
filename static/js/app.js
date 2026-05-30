document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const chatMessages = document.getElementById("chat-messages");
    const chatList = document.getElementById("chat-list");
    const newChatBtn = document.getElementById("new-chat-btn");
    const modelSelect = document.getElementById("model-select");
    const privacyCheckbox = document.getElementById("private-chat-checkbox");
    const privateWarning = document.getElementById("private-warning");
    const searchInput = document.getElementById("chat-search");

    // File Upload Elements
    const fileInput = document.getElementById("file-upload");
    const fileIndicator = document.getElementById("file-upload-indicator");
    const fileNameSpan = document.getElementById("file-name");
    const clearFileBtn = document.getElementById("clear-file");

    // Settings & Export Elements
    const settingsBtn = document.getElementById("settings-btn");
    const settingsModal = document.getElementById("settings-modal");
    const closeSettings = document.getElementById("close-settings");
    const tempSlider = document.getElementById("temp-slider");
    const tempVal = document.getElementById("temp-val");
    const memoryToggle = document.getElementById("memory-toggle");
    const exportTxtBtn = document.getElementById("export-txt-btn");
    const exportPdfBtn = document.getElementById("export-pdf-btn");

    let currentSessionId = null;
    let isStreaming = false;
    let lastUserMessage = "";
    let activeStreamController = null;

    // Private mode message history (memory-less, never sent to server)
    let privateMessages = [];

    // ------------------------------------
    // Markdown rendering helper (marked.js)
    // ------------------------------------
    function renderMarkdown(text) {
        if (typeof marked !== "undefined") {
            try {
                return marked.parse(text);
            } catch (e) {
                console.warn("marked.js parse error:", e);
            }
        }
        // Fallback: safely escape HTML
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\n/g, "<br>");
    }

    // ------------------------------------
    // Settings
    // ------------------------------------
    settingsBtn.addEventListener("click", () => settingsModal.style.display = "flex");
    closeSettings.addEventListener("click", () => settingsModal.style.display = "none");
    settingsModal.addEventListener("click", (e) => {
        if (e.target === settingsModal) settingsModal.style.display = "none";
    });
    tempSlider.addEventListener("input", (e) => tempVal.textContent = e.target.value);

    exportTxtBtn.addEventListener("click", () => {
        if (!currentSessionId || privacyCheckbox.checked) return;
        window.open(`/api/chat/${currentSessionId}/export?format=txt`, "_blank");
    });

    exportPdfBtn.addEventListener("click", () => {
        if (!currentSessionId || privacyCheckbox.checked) return;
        window.open(`/api/chat/${currentSessionId}/export?format=pdf`, "_blank");
    });

    // ------------------------------------
    // Session loading
    // ------------------------------------
    async function loadSessions(query = "") {
        if (privacyCheckbox.checked) return;
        try {
            const url = query
                ? `/api/chats/search?q=${encodeURIComponent(query)}`
                : "/api/chats";
            const res = await fetch(url);
            const data = await res.json();
            if (res.ok) {
                renderSessions(data.results || data.chats || []);
            }
        } catch (e) {
            console.error("Failed to load sessions", e);
        }
    }

    searchInput.addEventListener("input", (e) => {
        loadSessions(e.target.value.trim());
    });

    function renderSessions(sessions) {
        const fragment = document.createDocumentFragment();
        sessions.forEach(session => {
            const div = document.createElement("div");
            div.className = `chat-item ${session.chat_id === currentSessionId ? "active" : ""}`;
            div.dataset.id = session.chat_id;
            const pinClass = session.is_pinned ? "pinned" : "";

            // Use textContent for title to prevent XSS
            const titleSpan = document.createElement("span");
            titleSpan.className = "chat-title";
            titleSpan.title = session.title;
            titleSpan.textContent = session.title;

            div.innerHTML = `
                <div class="chat-actions">
                    <i class="ph ph-push-pin pin-btn ${pinClass}" data-id="${session.chat_id}" title="Pin/Unpin"></i>
                    <i class="ph ph-pencil-simple rename-btn" data-id="${session.chat_id}" title="Rename"></i>
                    <i class="ph ph-trash delete-btn" data-id="${session.chat_id}" title="Delete"></i>
                </div>
            `;
            div.insertBefore(titleSpan, div.firstChild);

            div.addEventListener("click", (e) => {
                if (e.target.tagName !== "I") {
                    switchSession(session.chat_id);
                }
            });

            div.querySelector(".pin-btn").addEventListener("click", async (e) => {
                e.stopPropagation();
                await fetch(`/api/chat/${session.chat_id}/pin`, { method: "PUT" });
                loadSessions(searchInput.value.trim());
            });

            div.querySelector(".rename-btn").addEventListener("click", async (e) => {
                e.stopPropagation();
                const newTitle = prompt("Enter new chat name:", session.title);
                if (newTitle && newTitle.trim()) {
                    await fetch(`/api/chat/${session.chat_id}`, {
                        method: "PUT",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ title: newTitle.trim() })
                    });
                    loadSessions(searchInput.value.trim());
                }
            });

            div.querySelector(".delete-btn").addEventListener("click", async (e) => {
                e.stopPropagation();
                if (confirm("Delete this chat?")) {
                    await fetch(`/api/chat/${session.chat_id}`, { method: "DELETE" });
                    if (currentSessionId === session.chat_id) {
                        startNewChat();
                    } else {
                        loadSessions(searchInput.value.trim());
                    }
                }
            });

            fragment.appendChild(div);
        });
        chatList.innerHTML = "";
        chatList.appendChild(fragment);
    }

    // ------------------------------------
    // New chat — FIX: no race condition,
    // session ID only set after server responds
    // ------------------------------------
    async function startNewChat() {
        if (activeStreamController) {
            activeStreamController.abort();
            activeStreamController = null;
        }

        if (privacyCheckbox.checked) {
            chatMessages.innerHTML = `
                <div class="message bot welcome-message">
                    <div class="msg-avatar"><i class="ph-fill ph-robot"></i></div>
                    <div class="msg-bubble">You are now in Private Mode. Messages are not saved.</div>
                </div>`;
            privateMessages = [];
            currentSessionId = null;
            return;
        }

        // Disable send while waiting for server — prevents race condition
        sendBtn.disabled = true;
        currentSessionId = null;

        chatMessages.innerHTML = `
            <div class="message bot welcome-message">
                <div class="msg-avatar"><i class="ph-fill ph-robot"></i></div>
                <div class="msg-bubble">Hello! I'm Quokka, your advanced AI assistant. How can I help you today?</div>
            </div>`;

        try {
            const res = await fetch("/api/chat/new", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: "New Chat" })
            });
            const data = await res.json();
            currentSessionId = data.chat_id; // Only set AFTER server responds
            loadSessions();
        } catch (e) {
            console.error("Failed to create new chat", e);
        } finally {
            sendBtn.disabled = false;
        }
    }

    async function switchSession(id) {
        if (activeStreamController) {
            activeStreamController.abort();
            activeStreamController = null;
        }
        if (privacyCheckbox.checked) return;

        currentSessionId = id;
        chatMessages.innerHTML = "";

        try {
            const res = await fetch(`/api/chat/${id}`);
            const data = await res.json();

            if (res.ok && data.chat) {
                const messages = data.chat.messages || [];
                if (messages.length === 0) {
                    chatMessages.innerHTML = `
                        <div class="message bot welcome-message">
                            <div class="msg-avatar"><i class="ph-fill ph-robot"></i></div>
                            <div class="msg-bubble">This is an empty chat.</div>
                        </div>`;
                } else {
                    messages.forEach(msg => {
                        addMessage(msg.content, msg.role === "assistant" ? "bot" : "user", false);
                        if (msg.role === "user") lastUserMessage = msg.content;
                    });
                }
            } else {
                chatMessages.innerHTML = `<div class="message bot"><div class="msg-bubble">Failed to load chat history.</div></div>`;
            }
        } catch (e) {
            console.error("Failed to load chat", e);
        }

        loadSessions(searchInput.value.trim());
    }

    newChatBtn.addEventListener("click", () => {
        if (!privacyCheckbox.checked) startNewChat();
    });

    function updatePrivacyMode(isPrivate) {
        privacyCheckbox.checked = isPrivate;
        if (isPrivate) {
            document.body.classList.add("privacy-mode");
            privateWarning.style.display = "flex";
            chatMessages.innerHTML = "";
            privateMessages = [];
            startNewChat();
        } else {
            document.body.classList.remove("privacy-mode");
            privateWarning.style.display = "none";
            privateMessages = [];
            startNewChat();
        }
    }

    privacyCheckbox.addEventListener("change", (e) => {
        updatePrivacyMode(e.target.checked);
    });

    // ------------------------------------
    // File upload
    // ------------------------------------
    fileInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        fileIndicator.style.display = "inline-flex";
        fileNameSpan.textContent = "Uploading...";
        const formData = new FormData();
        formData.append("file", file);
        try {
            const res = await fetch("/api/upload", { method: "POST", body: formData });
            const data = await res.json();
            if (data.success) {
                fileNameSpan.textContent = file.name + " (Indexed ✓)";
            } else {
                fileNameSpan.textContent = "Error: " + (data.error || "Upload failed");
            }
        } catch (e) {
            fileNameSpan.textContent = "Upload failed";
        }
    });

    clearFileBtn.addEventListener("click", () => {
        fileInput.value = "";
        fileIndicator.style.display = "none";
    });

    // ------------------------------------
    // Textarea auto-resize
    // ------------------------------------
    chatInput.addEventListener("input", function () {
        this.style.height = "auto";
        this.style.height = this.scrollHeight + "px";
        sendBtn.style.backgroundColor = this.value.trim()
            ? "var(--accent-color)"
            : "var(--text-secondary)";
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage(chatInput.value.trim());
        }
    });

    sendBtn.addEventListener("click", () => sendMessage(chatInput.value.trim()));

    // ------------------------------------
    // Send message + stream response
    // ------------------------------------
    async function sendMessage(text) {
        if (isStreaming) return;
        if (!text) return;

        lastUserMessage = text;
        addMessage(text, "user");
        chatInput.value = "";
        chatInput.style.height = "auto";
        sendBtn.style.backgroundColor = "var(--text-secondary)";

        if (privacyCheckbox.checked) {
            privateMessages.push({ role: "user", content: text });
        }

        if (activeStreamController) activeStreamController.abort();
        activeStreamController = new AbortController();

        isStreaming = true;
        sendBtn.disabled = true;
        chatInput.disabled = true;

        // Build bot message container
        const botMsgDiv = document.createElement("div");
        botMsgDiv.className = "message bot";
        botMsgDiv.innerHTML = `
            <div class="msg-avatar"><i class="ph-fill ph-robot"></i></div>
            <div class="msg-bubble">
                <div class="text-content"><span class="typing-indicator">Thinking...</span></div>
            </div>
        `;
        chatMessages.appendChild(botMsgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        const bubbleParent = botMsgDiv.querySelector(".msg-bubble");
        const textContent = botMsgDiv.querySelector(".text-content");

        try {
            const payload = {
                message: text,
                model: modelSelect.value,
                is_private: privacyCheckbox.checked,
                temperature: parseFloat(tempSlider.value),
                memory_enabled: memoryToggle.checked
            };

            if (privacyCheckbox.checked) {
                payload.private_history = privateMessages;
            } else {
                payload.session_id = currentSessionId;
            }

            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                signal: activeStreamController.signal
            });

            // Handle plain JSON error responses (e.g. safety block, 400)
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                const data = await response.json();
                textContent.innerHTML = renderMarkdown(data.response || data.error || "Unknown error");
                return;
            }

            // Stream SSE response
            textContent.innerHTML = "";
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let fullText = "";
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.error) {
                            textContent.innerHTML = `<span style="color:#ff5555">${data.error}</span>`;
                        }

                        if (data.text) {
                            fullText += data.text;
                            // Show raw text while streaming for performance
                            textContent.textContent = fullText;

                            // Sticky scroll
                            const nearBottom =
                                chatMessages.scrollHeight - chatMessages.clientHeight <=
                                chatMessages.scrollTop + 80;
                            if (nearBottom) chatMessages.scrollTop = chatMessages.scrollHeight;
                        }

                        if (data.metadata) {
                            let metaDiv = bubbleParent.querySelector(".metadata-block");
                            if (!metaDiv) {
                                metaDiv = document.createElement("div");
                                metaDiv.className = "metadata-block";
                                metaDiv.innerHTML = `
                                    <div class="meta-header"><i class="ph ph-books"></i> Sources</div>
                                    <ul class="meta-sources"></ul>
                                    <div class="meta-confidence"></div>
                                `;
                                bubbleParent.appendChild(metaDiv);
                            }
                            const sourcesList = metaDiv.querySelector(".meta-sources");
                            sourcesList.innerHTML = data.metadata.sources
                                .map(s => `<li>${s}</li>`)
                                .join("");
                            metaDiv.querySelector(".meta-confidence").innerHTML =
                                `<i class="ph ph-chart-bar"></i> Confidence: ${data.metadata.confidence}%`;
                        }

                        if (data.title && currentSessionId) {
                            const activeTitle = document.querySelector(
                                `.chat-item[data-id="${currentSessionId}"] .chat-title`
                            );
                            if (activeTitle) {
                                activeTitle.textContent = data.title;
                                activeTitle.title = data.title;
                            } else {
                                loadSessions();
                            }
                        }

                    } catch (e) {
                        console.error("Stream parse error", e);
                    }
                }
            }

            // Render markdown once streaming is complete
            if (fullText) {
                textContent.innerHTML = renderMarkdown(fullText);
            }

            addMessageActions(botMsgDiv, fullText);

            if (privacyCheckbox.checked && fullText) {
                privateMessages.push({ role: "assistant", content: fullText });
            }

        } catch (error) {
            if (error.name === "AbortError") {
                console.log("Stream cancelled by user");
                if (textContent.textContent === "") {
                    textContent.textContent = "Response cancelled.";
                }
            } else {
                console.error("Stream error:", error);
                textContent.innerHTML = `<span style="color:#ff5555">⚠️ Error connecting to server.</span>`;
            }
        } finally {
            isStreaming = false;
            sendBtn.disabled = false;
            chatInput.disabled = false;
            chatInput.focus();
        }
    }

    // ------------------------------------
    // Add message to chat (history / user)
    // FIX: textContent for user messages prevents XSS
    // FIX: renderMarkdown for bot history messages
    // ------------------------------------
    function addMessage(text, role, animate = true) {
        const div = document.createElement("div");
        div.className = `message ${role}`;
        if (!animate) {
            div.style.animation = "none";
            div.style.opacity = "1";
        }

        const icon = role === "bot" ? "ph-robot" : "ph-user";

        if (role === "user") {
            // textContent prevents XSS — never use innerHTML for user input
            const bubble = document.createElement("div");
            bubble.className = "msg-bubble";
            bubble.textContent = text;

            const avatar = document.createElement("div");
            avatar.className = "msg-avatar";
            avatar.innerHTML = `<i class="ph-fill ${icon}"></i>`;

            div.appendChild(bubble);
            div.appendChild(avatar);
        } else {
            const avatar = document.createElement("div");
            avatar.className = "msg-avatar";
            avatar.innerHTML = `<i class="ph-fill ${icon}"></i>`;

            const bubble = document.createElement("div");
            bubble.className = "msg-bubble";
            // renderMarkdown for bot history messages
            bubble.innerHTML = renderMarkdown(text);

            div.appendChild(avatar);
            div.appendChild(bubble);
        }

        chatMessages.appendChild(div);

        if (role === "bot") {
            addMessageActions(div, text);
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // ------------------------------------
    // Message action buttons (copy / regen)
    // ------------------------------------
    function addMessageActions(messageDiv, text) {
        if (messageDiv.querySelector(".msg-action-bar")) return;

        const actionBox = document.createElement("div");
        actionBox.className = "msg-action-bar";
        actionBox.innerHTML = `
            <button class="msg-action-btn copy-btn" title="Copy"><i class="ph ph-copy"></i></button>
            <button class="msg-action-btn regen-btn" title="Regenerate"><i class="ph ph-arrows-clockwise"></i></button>
        `;

        actionBox.querySelector(".copy-btn").addEventListener("click", () => {
            navigator.clipboard.writeText(text);
            const icon = actionBox.querySelector(".copy-btn i");
            icon.className = "ph ph-check";
            setTimeout(() => icon.className = "ph ph-copy", 2000);
        });

        actionBox.querySelector(".regen-btn").addEventListener("click", () => {
            if (isStreaming || !lastUserMessage) return;
            messageDiv.remove();
            if (privacyCheckbox.checked) {
                privateMessages.pop();
                privateMessages.pop();
            }
            sendMessage(lastUserMessage);
        });

        const bubble = messageDiv.querySelector(".msg-bubble");
        if (bubble) bubble.appendChild(actionBox);
    }

    // ------------------------------------
    // Init
    // ------------------------------------
    updatePrivacyMode(privacyCheckbox.checked);

    // Sidebar user info
    fetch("/api/auth/me")
        .then(r => r.json())
        .then(data => {
            if (data.user) {
                const usernameEl = document.getElementById("sidebar-username");
                const avatarEl = document.getElementById("sidebar-avatar");
                if (usernameEl) usernameEl.textContent = data.user.name;
                if (avatarEl) avatarEl.textContent = data.user.name[0].toUpperCase();
            }
        })
        .catch(() => {});

    // Logout
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            try {
                await fetch("/api/auth/logout", { method: "POST" });
            } catch (e) {
                // Ignore network errors; still redirect to login
            }
            window.location.href = "/login";
        });
    }

    // Global 401 handler — intercept all fetch calls
    // If any API returns 401, redirect to login
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
        const response = await originalFetch(...args);
        if (response.status === 401) {
            window.location.href = "/login";
        }
        return response;
    };
});