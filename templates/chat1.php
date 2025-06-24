<?php
session_start();

// Check if the user is logged in (replace with your login check logic)
if (!isset($_SESSION['username'])) {
    header('Location: index.php'); // Redirect to login page if not logged in
    exit();
}

// Define a basic response for the chatbot (can be expanded with your chatbot logic)
function getBotResponse($userMsg) {
    // Simple example response logic
    if (strpos(strtolower($userMsg), "how are you") !== false) {
        return "I'm doing well, thank you for asking! How can I assist you today?";
    } elseif (strpos(strtolower($userMsg), "hello") !== false) {
        return "Hi there! How can I help you?";
    } else {
        return "I'm here to listen. Tell me what's on your mind.";
    }
}

// Check if the message is being sent via POST request
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Get the message sent by the user
    $userMsg = isset($_POST['msg']) ? $_POST['msg'] : '';

    // Get the bot's response
    $botResponse = getBotResponse($userMsg);

    // Return the response in JSON format
    echo json_encode(['response' => $botResponse]);
    exit();
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mental Health Chatbot</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-image: url('https://t4.ftcdn.net/jpg/07/67/39/37/360_F_767393773_ku3EXghSvq8oCHjWcxHRrKCiHwXRFr9l.jpg');
            background-size: cover;
            background-position: center;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }

        .chat-container {
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 600px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            height: 80vh;
        }

        .chat-header {
            text-align: center;
            font-size: 20px;
            margin-bottom: 10px;
            font-weight: bold;
            color: #444;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .chat-header img {
            width: 30px;
            height: 30px;
            margin-right: 10px;
            border-radius: 50%;
        }

        .header-buttons {
            display: flex;
            gap: 10px;
        }

        .profile-link, .dashboard-link {
            font-size: 14px;
            padding: 8px 15px;
            border: none;
            background-color: #66b3ff;
            color: white;
            border-radius: 5px;
            text-decoration: none;
            display: flex;
            align-items: center;
        }

        .profile-link img, .dashboard-link img {
            width: 20px;
            height: 20px;
            margin-right: 8px;
        }

        .profile-link:hover, .dashboard-link:hover {
            background-color: #3399ff;
        }

        .chat-box {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 8px;
            border: 1px solid #e1e1e1;
        }

        .message {
            display: flex;
            align-items: flex-start;
            margin: 10px 0;
        }

        .bot-message {
            flex-direction: row;
        }

        .user-message {
            flex-direction: row-reverse;
        }

        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin: 0 10px;
        }

        .message-content {
            background-color: #66b3ff;
            color: white;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 70%;
            word-wrap: break-word;
            font-size: 14px;
        }

        .bot-message .message-content {
            background-color: #e0e0e0;
            color: #333;
        }

        .input-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid #e1e1e1;
            padding-top: 10px;
        }

        input[type="text"] {
            width: 70%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 20px;
            font-size: 16px;
            outline: none;
        }

        input[type="text"]:focus {
            border-color: #66b3ff;
        }

        button {
            padding: 10px;
            background-color: #66b3ff;
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 18px;
            cursor: pointer;
        }

        button:hover {
            background-color: #3399ff;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <div style="display: flex; align-items: center;">
                <img src="https://t4.ftcdn.net/jpg/04/21/38/37/360_F_421383729_XSnMHrKGQKPge4eXUXZTIaas50HzEZdb.jpg" alt="Logo">
                Mindo
            </div>
            <div class="header-buttons">
                <!-- Updated Dashboard Button -->
                <a href="dashboard.php" class="dashboard-link">
                    <img src="https://example.com/dashboard-icon.png" alt="Dashboard Icon">
                    Dashboard
                </a>
                <!-- Existing Profile Button -->
                <a href="profile.php" class="profile-link">
                    <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRNKfj6RsyRZqO4nnWkPFrYMmgrzDmyG31pFQ&s" alt="Profile Icon">
                    View Profile
                </a>
            </div>
        </div>

        <div id="chat-box" class="chat-box">
            <!-- Bot's initial message -->
            <div class="message bot-message">
                <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTlCh2mPp5DnsSsDTUFRNrk2KOROxeBVSEX5g&s" alt="Bot" class="avatar">
                <div class="message-content">Hi! How are you feeling today?</div>
            </div>
        </div>

        <div class="input-container">
            <input type="text" id="user-msg" placeholder="Type your answer..." autocomplete="off">
            <button id="mic-button" onclick="startListening()">🎤</button>
            <button onclick="sendMessage()">&#9658;</button>
        </div>
    </div>

    <script>
        function sendMessage() {
            const msg = document.getElementById("user-msg").value.trim();
            if (!msg) return;

            const chatBox = document.getElementById("chat-box");

            // Display the user's message
            const userMessage = document.createElement("div");
            userMessage.classList.add("message", "user-message");
            userMessage.innerHTML = `
                <img src="https://t4.ftcdn.net/jpg/07/67/39/37/360_F_767393773_ku3EXghSvq8oCHjWcxHRrKCiHwXRFr9l.jpg" alt="User" class="avatar">
                <div class="message-content">${msg}</div>
            `;
            chatBox.appendChild(userMessage);
            chatBox.scrollTop = chatBox.scrollHeight;

            // Send the message to the server
            fetch("<?php echo $_SERVER['PHP_SELF']; ?>", {
                method: "POST",
                body: new URLSearchParams({ "msg": msg }),
                headers: { "Content-Type": "application/x-www-form-urlencoded" }
            })
            .then(response => response.json())
            .then(data => {
                if (data.response) {
                    const botMessage = document.createElement("div");
                    botMessage.classList.add("message", "bot-message");
                    botMessage.innerHTML = `
                        <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTlCh2mPp5DnsSsDTUFRNrk2KOROxeBVSEX5g&s" alt="Bot" class="avatar">
                        <div class="message-content">${data.response}</div>
                    `;
                    chatBox.appendChild(botMessage);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
            });

            document.getElementById("user-msg").value = "";
        }

        function startListening() {
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                console.log('Voice recognition started.');
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById("user-msg").value = transcript;
            };

            recognition.onerror = (event) => {
                console.error('Error during speech recognition:', event.error);
            };

            recognition.start();
        }
    </script>
</body>
</html>
