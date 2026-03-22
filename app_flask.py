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
            background: linear-gradient(rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0.25)), url("/static/farm-bg.jpg");
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
            padding: 24px;
            position: relative;
            z-index: 1;
        }

        .hero {
    background: linear-gradient(to bottom, #8ec5e8, #dff4ff);
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.12);
    margin-bottom: 20px;
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
            background: rgba(255,255,255,0.97);
            border-radius: 22px;
            box-shadow: 0 12px 35px rgba(0,0,0,0.14);
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.75);
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
            max-height: 520px;
            overflow-y: auto;
            background:
                linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(248,252,245,0.95));
        }

        .empty-state {
            padding: 32px 20px;
            text-align: center;
            color: #556655;
            font-size: 1rem;
        }

        .message-row {
            display: flex;
            margin-bottom: 16px;
        }

        .message-row.user {
            justify-content: flex-end;
        }

        .message-row.bot {
            justify-content: flex-start;
        }

        .bubble {
            max-width: 78%;
            padding: 14px 16px;
            border-radius: 18px;
            line-height: 1.45;
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
            font-size: 0.8rem;
            font-weight: bold;
            margin-bottom: 6px;
            opacity: 0.8;
        }

        .form-area {
            padding: 18px;
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
            <p>
                <p>AI-powered poultry assistant using local knowledge and real-time research for accurate answers.</p>
            </p>
            <div class="farm-strip">
                Ask about symptoms, treatment basics, safe foods, chick care, worms, mites, coccidiosis, and Marek's disease.
            </div>
        </div>

        <div class="chat-shell">
            <div class="chat-header">
                <h2>Backyard Flock Assistant</h2>
                <p><p>Hybrid AI system combining a local knowledge base with external data sources to deliver reliable poultry guidance.</p></p>
            </div>

            <div class="chat-history">
                {% if history %}
                    {% for item in history %}
                        <div class="message-row user">
                            <div class="bubble">
                                <div class="label">You</div>
                                {{ item.user }}
                            </div>
                        </div>

                        <div class="message-row bot">
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
                    <div class="bubble">
                        <div class="label">Poultry Bot</div>
                        Poultry Bot is typing...
                    </div>
                </div>
            </div>

            <div class="form-area">
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

        form.addEventListener("submit", function() {
            if (typing) {
                typing.style.display = "flex";
                typing.scrollIntoView({ behavior: "smooth" });
            }
        });
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