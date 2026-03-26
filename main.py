import os
import asyncio
import json
from typing import Annotated, Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import html
# Imports for Python, environment setup, AI (LangChain/LangGraph), RAG (FAISS), and Wikipedia cleanup


# State object (stores chat messages)
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Load API keys
load_dotenv()

# Global placeholders
assistant_agent = None
retriever = None
vectorstore = None
wiki_tools = None
llm = None
graph = None

# Build local RAG (load → split → embed → store)
def build_retriever():
    loader = TextLoader("data/chicken_guide.md", encoding="utf-8")
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n## ", "\n### ", "\n- ", "\n\n", "\n", " "],
        chunk_size=400,
        chunk_overlap=60
    )

    splits = text_splitter.split_documents(documents)
    print(f"Built {len(splits)} chunks")

    for i, doc in enumerate(splits[:5], 1):
        print(f"\n--- Chunk {i} ---")
        print(doc.page_content[:300])

    # Create embeddings + vector DB
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        base_url="https://models.github.ai/inference",
        api_key=os.getenv("GITHUB_TOKEN")
    )

    vectorstore = FAISS.from_documents(splits, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    
    return vectorstore, retriever

# Clean Wikipedia text (remove junk lines)
def clean_wikipedia_text(text: str) -> str:
    lines = text.splitlines()
    filtered = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue
        if stripped.startswith("記事ID:"):
            continue
        if stripped.startswith("最終更新:"):
            continue
        if stripped.startswith("記事サイズ:"):
            continue
        if stripped.startswith("URL:"):
            continue

        filtered.append(line)

    return "\n".join(filtered)

# Wikipedia fallback search
async def wikipedia_search(query: str):
    """Fetch a cleaner Wikipedia article snippet for poultry fallback."""
    global wiki_tools

    search_tool = next(
        (t for t in wiki_tools if t.name == "search_wikipedia"),
        None
    )

    article_tool = next(
        (t for t in wiki_tools if t.name == "get_wikipedia_article"),
        None
    )

    if not search_tool:
        return "No Wikipedia search tool available."

    cleaned_query = query.lower()

    if "marek" in cleaned_query:
        wiki_query = "Marek's disease"
        article_title = "Marek's disease"

    elif "worm" in cleaned_query or "worms" in cleaned_query:
        wiki_query = "Parasitic worm"
        article_title = "Parasitic worm"

    elif "mite" in cleaned_query or "mites" in cleaned_query:
        wiki_query = "Poultry red mite"
        article_title = "Poultry red mite"

    elif "coccidiosis" in cleaned_query:
        wiki_query = "Coccidiosis"
        article_title = "Coccidiosis"

    else:
        wiki_query = (
            query.replace("What are symptoms of", "")
                 .replace("How to treat", "")
                 .replace("How do you treat", "")
                 .replace("How do I treat", "")
                 .replace("What is", "")
                 .replace("What are", "")
                 .replace("in chickens", "")
                 .replace("in poultry", "")
                 .replace("my chickens", "")
                 .replace("?", "")
                 .strip()
        )
        article_title = wiki_query

    print(f"\nWikipedia query: {wiki_query}")
    print(f"Wikipedia article title: {article_title}")

    results = await search_tool.ainvoke({"query": wiki_query})
    if isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
        results_text = html.unescape(results[0].get("text", str(results)))
    else:
        results_text = html.unescape(str(results))

    if article_tool:
        try:
            article = await article_tool.ainvoke({"title": article_title})
            if isinstance(article, list) and len(article) > 0 and isinstance(article[0], dict):
                article_text = html.unescape(article[0].get("text", str(article)))
            else:
                article_text = html.unescape(str(article))
                
                article_text = clean_wikipedia_text(article_text)
                
            return article_text[:1800]
        except Exception as e:
            print(f"Wikipedia article fetch failed: {e}")

    return results_text[:1200]

# Main assistant logic (RAG first → fallback if needed)
async def assistant_node(state: State) -> Command[Literal["__end__"]]:
    """Single backyard poultry assistant node with hybrid local RAG + Wikipedia fallback."""
    global retriever, vectorstore, llm

    print("\n" + "=" * 50)
    print("POULTRY ASSISTANT NODE")
    print("=" * 50)

    user_question = state["messages"][-1].content

    # Handle short follow-up questions by using the previous user message for context
    if user_question.lower().strip() in ["it", "that", "this"] or len(user_question.split()) <= 4:
        for msg in reversed(state["messages"][:-1]):
            if isinstance(msg, HumanMessage):
                user_question = msg.content + " " + user_question
                break

    # Search local knowledge base first, with scores
    scored_docs = vectorstore.similarity_search_with_score(user_question, k=2)

    docs = [doc for doc, score in scored_docs]
    scores = [score for doc, score in scored_docs]

    print(f"\nLocal search scores: {scores}")

    # Lower score = better match
    is_short_followup = len(user_question.split()) <= 4
    
    # Decide: local or fallback
    use_local_rag = len(scores) > 0 and (scores[0] < 0.9) #or is_short_followup)

    recent_history = "\n".join(
        [
            f"{msg.__class__.__name__}: {getattr(msg, 'content', '')}"
            for msg in state["messages"][-4:]
        ]
    )

    if use_local_rag:
        retrieved_context = "\n\n".join(doc.page_content for doc in docs)

        print("\nUsing LOCAL knowledge base")
        print("\nRetrieved Context:")
        print(retrieved_context)
        
        # Use local poultry knowledge (RAG)
        rag_message = HumanMessage(
            content=f"""
Answer only from the poultry knowledge base below.
Use the recent conversation to understand follow-up questions.
If the answer is not clearly contained in the knowledge base, say you do not have enough local information.
Do not guess.
Keep the answer beginner-friendly and structured.

RECENT CONVERSATION:
{recent_history}

Format:
Direct Answer:
Important Details:
Safety Notes:
Simple Next Step:

POULTRY KNOWLEDGE BASE:
{retrieved_context}

USER QUESTION:
{user_question}
"""
        )
        # Send RAG prompt to agent
        response = await assistant_agent.ainvoke({"messages": [rag_message]})
        final_message = response["messages"][-1]
        
    # If local match is weak, fallback to Wikipedia
    else:
        print("\nLocal match weak. Falling back to Wikipedia.")

        wiki_result = await wikipedia_search(user_question)
        clean_preview = clean_wikipedia_text(wiki_result)

        print("\nWikipedia Result Preview:")
        print(clean_preview[:500])
        
        # Build prompt using Wikipedia data
        fallback_message = HumanMessage(
            content=f"""
The local poultry knowledge base did not contain a strong match.

Use the Wikipedia information below to answer the user's poultry question in English.
Use only clearly relevant facts from the Wikipedia data.
Keep the answer beginner-friendly.

WIKIPEDIA DATA:
{wiki_result}

Format:
Direct Answer:
Important Details:
Safety Notes:
Simple Next Step:

RECENT CONVERSATION:
{recent_history}

USER QUESTION:
{user_question}
"""
        )
        
        # Send fallback prompt to base LLM
        response = await llm.ainvoke([fallback_message])
        final_message = response
        
    # Print final response for debugging
    print("\nAssistant Output:")
    print(final_message.content)
    print("\n" + "=" * 50 + "\n")
    
    # Return updated conversation state
    return Command(
        update={"messages": state["messages"] + [final_message]},
        goto="__end__"
    )
    
# Initialize the chatbot once (sets up model, data, tools, and workflow)
async def initialize_chatbot():
    """Initialize LLM, retriever, tools, and graph once."""
    global assistant_agent, retriever, vectorstore, wiki_tools, llm, graph

    if graph is not None:
        return graph

    if not os.getenv("GITHUB_TOKEN"):
        raise ValueError("GITHUB_TOKEN not found. Add it to your .env file.")

    if not os.getenv("TAVILY_API_KEY"):
        raise ValueError("TAVILY_API_KEY not found. Add it to your .env file.")

    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0.7,
        base_url="https://models.github.ai/inference",
        api_key=os.getenv("GITHUB_TOKEN")
    )

    vectorstore, retriever = build_retriever()
    print("Retriever loaded from data/chicken_guide.md")

    with open("templates/assistant.json", "r") as f:
        assistant_data = json.load(f)
        assistant_prompt = assistant_data.get(
            "template",
            "You are a helpful backyard poultry assistant."
        )
        
    # MCP tools (Tavily + Wikipedia)
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    research_client = MultiServerMCPClient({
        "tavily": {
            "transport": "http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}",
        },
        "wikipedia": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "wikipedia-mcp-server"],
        }
    })

    researcher_tools = await research_client.get_tools()
    wiki_tools = researcher_tools

    print(f"Research tools: {[tool.name for tool in researcher_tools]}")

    assistant_agent = create_agent(
        llm,
        tools=researcher_tools,
        system_prompt=assistant_prompt
    )

    # Build graph
    builder = StateGraph(State)
    builder.add_node("assistant", assistant_node)
    builder.add_edge(START, "assistant")
    graph = builder.compile()

    return graph

# CLI loop    
async def main():
    """Run the chatbot in CLI mode."""
    global graph

    load_dotenv()
    graph = await initialize_chatbot()

    print("\n" + "="*50)
    print("Starting Hybrid RAG Poultry Chatbot")
    print("="*50 + "\n")

    conversation_state = {
        "messages": []
    }

    while True:
        user_input = input("\nAsk your backyard poultry question (or type 'exit'): ")

        lower_input = user_input.lower().strip()

        if not lower_input:
            print("\nPlease enter a poultry question or type 'exit'.")
            continue

        terminal_commands = [
            "git ", "python ", "pip ", "cd ", "dir", "ls", "mkdir ", "rm ", "del ",
            "copy ", "move ", "code ", "venv", ".venv", "powershell", "cmd"
        ]

        if any(lower_input.startswith(cmd) for cmd in terminal_commands):
            print("\nThat looks like a terminal command, not a poultry question.")
            print("Run terminal commands in PowerShell or the VS Code terminal.")
            continue
        
        # Exit chatbot even if the user adds extra spaces
        if lower_input == "exit":
            print("\nGoodbye 👋")
            break

        conversation_state["messages"].append(HumanMessage(content=user_input))

        async for chunk in graph.astream(
            conversation_state,
            stream_mode="updates"
        ):
            for node_name, node_update in chunk.items():
                if isinstance(node_update, dict):
                    conversation_state.update(node_update)

        if conversation_state.get("messages"):
            last_message = conversation_state["messages"][-1]
            print("\nAssistant:")
            print(getattr(last_message, "content", "No response available"))
        
  # Run app  
if __name__ == "__main__":
    asyncio.run(main())