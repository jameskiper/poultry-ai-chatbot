from flask import Flask, request, render_template_string
import asyncio
import main
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Poultry AI Chatbot</title>
</head>
<body>
    <h2>Poultry AI Chatbot</h2>
    <form method="post">
        <input type="text" name="message" placeholder="Ask about chickens..." style="width:300px;">
        <button type="submit">Send</button>
    </form>

    {% if response %}
        <h3>Response:</h3>
        <pre>{{ response }}</pre>
    {% endif %}
</body>
</html>
"""

load_dotenv()
chat_graph = asyncio.run(main.initialize_chatbot())

async def ask_bot(question):
    state = {"messages": [HumanMessage(content=question)]}

    async for chunk in chat_graph.astream(state, stream_mode="updates"):
        for node_name, node_update in chunk.items():
            if isinstance(node_update, dict):
                state.update(node_update)

    return state["messages"][-1].content

@app.route("/", methods=["GET", "POST"])
def home():
    response = None

    if request.method == "POST":
        user_input = request.form.get("message", "").strip()
        if user_input:
            response = asyncio.run(ask_bot(user_input))

    return render_template_string(HTML, response=response)

if __name__ == "__main__":
    app.run(debug=True)