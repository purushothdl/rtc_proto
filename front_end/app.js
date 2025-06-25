// --- CONFIGURATION ---
// Dynamically get the current host (e.g., 192.168.1.42)
const host = "5626-117-192-57-3.ngrok-free.app";

const API_BASE_URL = 'https://5626-117-192-57-3.ngrok-free.app';
const WEBSOCKET_URL = 'wss://5626-117-192-57-3.ngrok-free.app/ws';

const firebaseConfig = {
    apiKey: "AIzaSyBGp0cBHgNjF_a6CGRSP9jxetqNYCGiDWI",
    authDomain: "notifications-6fcca.firebaseapp.com",
    projectId: "notifications-6fcca",
    storageBucket: "notifications-6fcca.appspot.com",
    messagingSenderId: "244945588960",
    appId: "1:244945588960:web:b0762ccfe84478a01c7685"
};
const VAPID_KEY = "BB1umEaP1YwKdXOqwd3nahCcLqJ1halGVVcKmHQrNFJ5RDXAbvARV6Fui9fNzYrOfKG4P_gRTYKxi7UFCidCcHo";

// --- GLOBAL STATE ---
let state = {
    jwt: localStorage.getItem('authToken'),
    myUserId: localStorage.getItem('myUserId'),
    websocket: null,
    rooms: [],
    currentRoomId: null,
};

// --- DOM ELEMENTS ---
const authView = document.getElementById('auth-view');
const chatView = document.getElementById('chat-view');
const loginForm = document.getElementById('login-form');
const roomsList = document.getElementById('rooms-list');
const messagesDiv = document.getElementById('messages');
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const currentRoomName = document.getElementById('current-room-name');
const permissionBtn = document.getElementById('permission-btn');
const logoutBtn = document.getElementById('logout-btn');

// --- DYNAMICALLY IMPORT FIREBASE MODULES ---
let firebaseApp, getMessaging, getToken;
async function loadFirebaseModules() {
    if (firebaseApp) return;
    const { initializeApp } = await import('https://www.gstatic.com/firebasejs/9.23.0/firebase-app.js');
    const messagingModule = await import('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging.js');
    firebaseApp = initializeApp(firebaseConfig);
    getMessaging = messagingModule.getMessaging;
    getToken = messagingModule.getToken;
}

// --- API & WEBSOCKET FUNCTIONS ---
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true', // ✅ bypass the ngrok warning
        ...options.headers,
    };

    if (state.jwt) headers['Authorization'] = `Bearer ${state.jwt}`;

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            if (response.status === 401) logout();
            throw new Error(`API request failed: ${response.status}`);
        }

        return response.status === 204 ? null : response.json();
    } catch (error) {
        console.error(`Error in apiRequest for ${endpoint}:`, error);
        throw error;
    }
}


function connectWebSocket() {
    if (!state.jwt) return;
    if (state.websocket && state.websocket.readyState === WebSocket.OPEN) return;
    if (state.websocket) state.websocket.close();

    state.websocket = new WebSocket(`${WEBSOCKET_URL}?token=${state.jwt}`);
    state.websocket.onopen = () => console.log('WebSocket connected');
    state.websocket.onclose = () => console.log('WebSocket disconnected');
    state.websocket.onerror = (error) => console.error('WebSocket error:', error);
    state.websocket.onmessage = handleWebSocketMessage;
}

// --- DATA PROCESSING ---
function processRooms(rawRooms) {
    return rawRooms.map(room => {
        let displayName = room.name;
        if (room.room_type === 'private' && room.members) {
            const otherUser = room.members.find(m => m.user_id !== state.myUserId);
            displayName = otherUser ? otherUser.username : 'Private Chat';
        }
        return { ...room, display_name: displayName || 'Group Chat' };
    });
}

// --- CORE LOGIC HANDLERS ---
function handleWebSocketMessage(event) {
    const message = JSON.parse(event.data);
    console.log('Received WebSocket message:', message);

    if (message.type === 'new_message') {
        const msgData = message.data;

        // 1. If this message was not sent by me, immediately acknowledge its delivery.
        if (msgData.sender_id !== state.myUserId) {
            state.websocket.send(JSON.stringify({
                type: 'messages_delivered',
                message_ids: [msgData.id]
            }));
        }

        const room = state.rooms.find(r => r.id === msgData.room_id);
        if (room) {
            room.last_message = msgData.content;
            room.last_message_timestamp = msgData.timestamp;
            sortAndRenderRooms();
        }

        if (state.currentRoomId === msgData.room_id) {
            addMessageToView(msgData);
            // 2. If we are actively viewing the room, mark it as seen.
            if (msgData.sender_id !== state.myUserId) {
                state.websocket.send(JSON.stringify({
                    type: 'messages_seen',
                    message_ids: [msgData.id]
                }));
            }
        }
    } else if (message.type === 'message_status_update') {
        // Find the message in the DOM and update its status icon
        updateMessageStatusInView(message.data);
    }
}

async function selectRoom(roomId) {
    state.currentRoomId = roomId;
    const room = state.rooms.find(r => r.id === roomId);
    currentRoomName.textContent = room ? room.display_name : 'Select a conversation';
    renderRooms();

    messagesDiv.innerHTML = '<div class="welcome-message"><i class="fas fa-spinner fa-spin"></i><p>Loading messages...</p></div>';
    messageInput.disabled = true;
    sendBtn.disabled = true;

    if (roomId) {
        try {
            const messages = await apiRequest(`/api/messages/rooms/${roomId}`);
            renderMessages(messages);
            messageInput.disabled = false;
            sendBtn.disabled = false;
        } catch (error) {
            messagesDiv.innerHTML = '<p style="text-align: center; color: #888;">Could not load messages.</p>';
        }
    }
}

function logout() {
    localStorage.clear();
    state = { jwt: null, myUserId: null, websocket: null, rooms: [], currentRoomId: null };
    if (state.websocket) state.websocket.close();
    authView.style.display = 'flex';
    chatView.style.display = 'none';
}

// --- DOM RENDERING ---
function sortAndRenderRooms() {
    state.rooms.sort((a, b) => {
        const timeA = a.last_message_timestamp ? new Date(a.last_message_timestamp) : new Date(a.created_at);
        const timeB = b.last_message_timestamp ? new Date(b.last_message_timestamp) : new Date(b.created_at);
        return timeB - timeA;
    });
    renderRooms();
}

function renderRooms() {
    roomsList.innerHTML = '';
    state.rooms.forEach(room => {
        const li = document.createElement('li');
        li.className = 'room-item';
        if (room.id === state.currentRoomId) li.classList.add('active');
        li.dataset.roomId = room.id;
        li.onclick = () => selectRoom(room.id);

        const avatar = document.createElement('div');
        avatar.className = 'room-avatar';
        avatar.textContent = room.display_name.charAt(0).toUpperCase();

        const info = document.createElement('div');
        info.className = 'room-info';
        const name = document.createElement('p');
        name.className = 'room-name';
        name.textContent = room.display_name;
        const lastMsg = document.createElement('p');
        lastMsg.className = 'room-last-message';
        lastMsg.textContent = room.last_message ? room.last_message.substring(0, 30) : 'No messages yet...';

        info.appendChild(name);
        info.appendChild(lastMsg);
        li.appendChild(avatar);
        li.appendChild(info);
        roomsList.appendChild(li);
    });
}

function renderMessages(messages) {
    messagesDiv.innerHTML = '';
    messages.forEach(addMessageToView);

    // After rendering history, find all messages that are NOT from me and are NOT already 'seen'.
    const unreadMessageIds = messages
        .filter(m => m.sender_id !== state.myUserId && m.status !== 'seen')
        .map(m => m.id);

    // If there are any such messages, mark them all as seen now.
    if (unreadMessageIds.length > 0) {
        state.websocket.send(JSON.stringify({
            type: 'messages_seen',
            message_ids: unreadMessageIds
        }));
    }
}

function addMessageToView(msg) {
    const isMe = msg.sender_id === state.myUserId;
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${isMe ? 'message-out' : 'message-in'}`;
    bubble.dataset.messageId = msg.id;
    
    const content = document.createElement('p');
    content.textContent = msg.content;
    
    const meta = document.createElement('div');
    meta.className = 'meta';
    const time = document.createElement('span');
    time.textContent = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const status = document.createElement('span');
    status.className = 'message-status';
    if (isMe) status.textContent = ` ✓ ${msg.status}`;

    meta.appendChild(time);
    if (isMe) meta.appendChild(status);
    bubble.appendChild(content);
    bubble.appendChild(meta);
    
    const welcomeMessage = messagesDiv.querySelector('.welcome-message');
    if (welcomeMessage) welcomeMessage.remove();
    
    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function updateMessageStatusInView(statusData) {
    if (state.currentRoomId !== statusData.room_id) return;
    statusData.message_ids.forEach(msgId => {
        const msgElement = document.querySelector(`[data-message-id='${msgId}'] .message-status`);
        if (msgElement) msgElement.textContent = `✓ ${statusData.status}`;
    });
}

// --- NOTIFICATION LOGIC ---
async function enableNotifications() {
    if (!state.jwt) return alert("Please log in first.");

    try {
        await loadFirebaseModules();


        const serviceWorkerRegistration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
        console.log('Service Worker registered:', serviceWorkerRegistration);

        console.log('serviceWorker' in navigator, 'PushManager' in window, 'Notification' in window);

        const messaging = getMessaging(firebaseApp);
        const permission = await Notification.requestPermission();

        if (permission === 'granted') {
            const currentToken = await getToken(messaging, {
                vapidKey: VAPID_KEY,
                serviceWorkerRegistration,
            });

            if (currentToken) {
                await apiRequest('/api/notifications/register-fcm-token', {
                    method: 'POST',
                    body: JSON.stringify({
                        token: currentToken,
                        device_type: 'web',
                    }),
                });
                alert('Notifications enabled successfully!');
            }
        } else {
            alert('Notification permission was not granted.');
        }
    } catch (err) {
        console.error('An error occurred during notification setup.', err);
        alert('Could not enable notifications.');
    }
}


// --- INITIALIZATION ---
async function initializeApp() {
    try {
        const me = await apiRequest('/api/auth/me');
        state.myUserId = me.user_id;
        localStorage.setItem('myUserId', me.user_id);

        const rawRooms = await apiRequest('/api/rooms');
        state.rooms = processRooms(rawRooms);
        sortAndRenderRooms();

        connectWebSocket();
        authView.style.display = 'none';
        chatView.style.display = 'flex';
    } catch (error) {
        logout();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    try {
        const loginData = await apiRequest('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        state.jwt = loginData.access_token;
        localStorage.setItem('authToken', state.jwt);
        await initializeApp();
    } catch (error) {
        alert('Login failed!');
    }
}

function handleSendMessage(e) {
    e.preventDefault();
    const content = messageInput.value.trim();
    if (!content || !state.currentRoomId || !state.websocket) return;

    // 1. Find the full room object from our state
    const currentRoom = state.rooms.find(r => r.id === state.currentRoomId);
    if (!currentRoom) {
        console.error("Could not find the current room in state.");
        return;
    }

    let messagePayload;

    // 2. Construct the correct payload based on the room type
    if (currentRoom.room_type === 'group') {
        messagePayload = {
            type: 'send_message',
            room_id: state.currentRoomId,
            content: content,
        };
    } else if (currentRoom.room_type === 'private') {
        // For private rooms, we need to find the other user's ID
        const otherUser = currentRoom.members.find(m => m.user_id !== state.myUserId);
        
        if (!otherUser) {
            console.error("Could not find the other user in this private chat.");
            return;
        }

        messagePayload = {
            type: 'send_message',
            target_user_id: otherUser.user_id, // Send target_user_id, NOT room_id
            content: content,
        };
    }

    // 3. Send the correctly formatted payload
    if (messagePayload) {
        state.websocket.send(JSON.stringify(messagePayload));
        messageInput.value = '';
    }
}

// --- START THE APP ---
function main() {
    loginForm.addEventListener('submit', handleLogin);
    messageForm.addEventListener('submit', handleSendMessage);
    permissionBtn.onclick = enableNotifications;
    logoutBtn.onclick = logout;

    if (state.jwt) {
        initializeApp();
    } else {
        authView.style.display = 'flex';
        chatView.style.display = 'none';
    }
}

main();