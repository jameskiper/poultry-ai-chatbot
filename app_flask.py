from flask import Flask, request, render_template_string, session
import asyncio
import main
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-later"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Poultry AI Chatbot</title>
    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.4)), url("/static/new%20chicken%20chatbox%20piture.png");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-repeat: no-repeat;
            min-height: 100vh;
            color: #1f2a1f;
        }

        .page {
            max-width: 980px;
            margin: 0 auto;
            padding: 24px 24px 8px 24px;
            position: relative;
            z-index: 1;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

       .hero {
    background: linear-gradient(to bottom, #8ec5e8, #dff4ff);
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 12px 35px rgba(0,0,0,0.25);
    margin-bottom: 20px;
    backdrop-filter: blur(4px);
}

        .hero h1 {
            margin: 0 0 10px 0;
            font-size: 2rem;
        }

        .hero p {
            margin: 0;
            font-size: 1rem;
            color: #425342;
        }

        .farm-strip {
            margin-top: 18px;
            padding: 12px 16px;
            border-radius: 14px;
            background: linear-gradient(90deg, #f7f2d9, #fff9ec);
            border: 1px solid #eadfb0;
            font-size: 0.95rem;
        }

       .chat-shell {
    background: rgba(255,255,255,0.85); /* slightly transparent */
    border-radius: 22px;
    box-shadow: 0 15px 40px rgba(0,0,0,0.25); /* stronger shadow */
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.6);
    backdrop-filter: blur(8px); /* 🔥 glass effect */
}

        .chat-header {
            background: linear-gradient(135deg, #5a8f4d, #7fb069);
            color: white;
            padding: 18px 22px;
        }

        .chat-header h2 {
            margin: 0;
            font-size: 1.2rem;
        }

        .chat-header p {
            margin: 6px 0 0 0;
            font-size: 0.92rem;
            opacity: 0.95;
        }

        .chat-history {
            padding: 20px;
            padding-bottom: 55px;
            max-height: 45vh;
            overflow-y: auto;
            background: linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(248,252,245,0.95));
        }

        .empty-state {
            padding: 32px 20px;
            text-align: center;
            color: #556655;
            font-size: 1rem;
        }

        .message-row {
            display: flex;
            margin-bottom: 10px;
        }

        .message-row.user {
            justify-content: flex-end;
        }

        .message-row.bot {
            justify-content: flex-start;
        }

        .bubble {
            max-width: 72%;
            padding: 11px 14px;
            border-radius: 18px;
            line-height: 1.35;
            box-shadow: 0 4px 14px rgba(0,0,0,0.08);
            white-space: pre-wrap;
        }

        .user .bubble {
            background: linear-gradient(135deg, #d7f0ff, #bce4ff);
            color: #163447;
            border-bottom-right-radius: 6px;
        }

        .bot .bubble {
            background: linear-gradient(135deg, #f7f6ef, #fffdf7);
            color: #2d3528;
            border: 1px solid #ece6cf;
            border-bottom-left-radius: 6px;
        }

        .label {
            font-size: 0.7rem;
            font-weight: bold;
            margin-bottom: 4px;
            opacity: 0.8;
        }

        .form-area {
            padding: 14px 18px 10px 18px;
            border-top: 1px solid #e5eadf;
            background: #f7fbf3;
        }

        .input-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .input-row input[type="text"] {
            flex: 1;
            min-width: 260px;
            padding: 14px 16px;
            border-radius: 14px;
            border: 1px solid #cfd8c3;
            font-size: 1rem;
            outline: none;
        }

        .input-row input[type="text"]:focus {
            border-color: #7fb069;
            box-shadow: 0 0 0 3px rgba(127,176,105,0.15);
        }

        .btn {
            padding: 13px 18px;
            border: none;
            border-radius: 14px;
            font-size: 0.95rem;
            font-weight: bold;
            cursor: pointer;
        }

        .btn-send {
            background: linear-gradient(135deg, #5a8f4d, #7fb069);
            color: white;
        }

        .btn-clear {
            background: #efe8d2;
            color: #5a4c2d;
        }

        .hint-row {
            margin-top: 12px;
            font-size: 0.9rem;
            color: #5c6b57;
        }

        .hint-row span {
            display: inline-block;
            margin-right: 10px;
            margin-top: 6px;
            padding: 6px 10px;
            background: #eef5e7;
            border-radius: 999px;
            border: 1px solid #dbe8cf;
        }

        .typing-bubble {
            min-height: 40px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 11px 14px;
        }

        .typing-dots {
            display: flex;
            gap: 5px;
            align-items: center;
            margin-top: 8px;
        }

        .typing-dots span {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #7fb069;
            animation: typing-bounce 1.4s infinite;
        }

        .typing-dots span:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-dots span:nth-child(3) {
            animation-delay: 0.4s;
        }

        #typing {
            margin-bottom: 16px;
        }

        @keyframes typing-bounce {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.7;
            }
            30% {
                transform: translateY(-6px);
                opacity: 1;
            }
        }

        @media (max-width: 700px) {
            .page {
                padding: 14px;
            }

            .bubble {
                max-width: 92%;
            }

            .hero h1 {
                font-size: 1.6rem;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="hero">
            <h1>🐔 Poultry AI Chatbot</h1>
            <p>AI-powered poultry assistant using local knowledge and real-time research for accurate answers.</p>
            <div class="farm-strip">
                Ask about symptoms, treatment basics, safe foods, chick care, housing, worms, mites, and coccidiosis.
            </div>
        </div>

        <div class="chat-shell">
            <div class="chat-header">
                <h2>Backyard Flock Assistant</h2>
                <p>Hybrid AI system combining a local knowledge base with external data sources to deliver reliable poultry guidance.</p>
            </div>

            <div id="chat-history" class="chat-history">
                {% if history %}
                    {% for item in history %}
                        <div class="message-row user">
                            <div class="bubble">
                                <div class="label">You</div>
                                {{ item.user }}
                            </div>
                        </div>

                        <div class="message-row bot{% if loop.last %} last-bot-message{% endif %}">
                            <div class="bubble">
                                <div class="label">Poultry Bot</div>
                                {{ item.bot }}
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        Start the conversation with a poultry question.
                    </div>
                {% endif %}
                <div id="typing" class="message-row bot" style="display:none;">
                    <div class="bubble typing-bubble">
                        <div class="label">Poultry Bot</div>
                        <div class="typing-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
            </div>

            <div id="form-area" class="form-area">
                <form method="post">
                    <div class="input-row">
                        <input type="text" name="message" placeholder="Ask about chickens..." autocomplete="off" required>
                        <button class="btn btn-send" type="submit">Send</button>
                        <button class="btn btn-clear" type="submit" name="clear" value="1" formnovalidate>Clear Chat</button>
                    </div>
                </form>

                <div class="hint-row">
                    <span>What are symptoms of Marek's disease?</span>
                    <span>How do you treat red mites?</span>
                    <span>What foods are unsafe for chickens?</span>
                </div>
            </div>
        </div>
    </div>
    <script>
        const form = document.querySelector("form");
        const typing = document.getElementById("typing");
        const chatHistory = document.getElementById("chat-history");

        form.addEventListener("submit", function() {
            if (typing) {
                typing.style.display = "flex";
            }

            if (chatHistory) {
                chatHistory.scrollTop = chatHistory.scrollHeight - 80;
            }
        });

        window.onload = function() {
            const lastBotMessage = document.querySelector(".last-bot-message");
            if (lastBotMessage) {
                lastBotMessage.scrollIntoView({ behavior: "auto", block: "start" });
            }
        };
    </script>
</body>
</html>
"""

load_dotenv()
chat_graph = asyncio.run(main.initialize_chatbot())

async def ask_bot(conversation_state):
    async for chunk in chat_graph.astream(conversation_state, stream_mode="updates"):
        for node_name, node_update in chunk.items():
            if isinstance(node_update, dict):
                conversation_state.update(node_update)

    return conversation_state["messages"][-1].content, conversation_state


@app.route("/", methods=["GET", "POST"])
def home():
    if "history" not in session:
        session["history"] = []

    if request.method == "POST":
        if request.form.get("clear") == "1":
            session["history"] = []
            session.modified = True
            return render_template_string(HTML, history=session["history"])

        user_input = request.form.get("message", "").strip()
        lower_input = user_input.lower()

        POULTRY_KEYWORDS = [
            "chicken", "chickens", "chick", "chicks", "hen", "hens",
            "rooster", "roosters", "poultry", "egg", "eggs", "coop",
            "flock", "brooder", "marek", "coccidiosis", "mites",
            "worms", "feed", "layer", "broiler", "water",
            "disease", "symptom", "symptoms", "nest", "nesting"
        ]

        if user_input and not any(word in lower_input for word in POULTRY_KEYWORDS):
            session["history"].append({
                "user": user_input,
                "bot": (
                    "Direct Answer: I’m designed specifically for poultry and chicken care questions.\n\n"
                    "Important Details: This chatbot only answers poultry-related topics.\n\n"
                    "Simple Next Step: Please ask a chicken-related question."
                )
            })
            session.modified = True
            return render_template_string(HTML, history=session["history"])

        if user_input:
            conversation_state = {"messages": []}

            for item in session["history"]:
                conversation_state["messages"].append(HumanMessage(content=item["user"]))
                conversation_state["messages"].append(AIMessage(content=item["bot"]))

            conversation_state["messages"].append(HumanMessage(content=user_input))

            bot_reply, _ = asyncio.run(ask_bot(conversation_state))

            session["history"].append({
                "user": user_input,
                "bot": bot_reply
            })
            session.modified = True

    return render_template_string(HTML, history=session["history"])


if __name__ == "__main__":
    app.run(debug=True)