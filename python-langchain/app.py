import os
import asyncio
import json
from typing import Annotated, Literal
from typing_extensions import TypedDict
#from typing import TypedDict, Annotated, Literal
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



class State(TypedDict):
    messages: Annotated[list, add_messages]


load_dotenv()


assistant_agent = None
retriever = None
vectorstore = None
wiki_tools = None
llm = None

def build_retriever():
    loader = TextLoader("data/chicken_guide.md", encoding="utf-8")
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n## ", "\n### ", "\n- ", "\n\n", "\n", " "],
        chunk_size=400,
        chunk_overlap=60
    )

    splits = text_splitter.split_documents(documents)
    splits = splits[:12]  # keep for testing
    print(f"Built {len(splits)} chunks")

    for i, doc in enumerate(splits[:5], 1):
        print(f"\n--- Chunk {i} ---")
        print(doc.page_content[:300])

    # ✅ ADD THIS PART (new)
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        base_url="https://models.github.ai/inference",
        api_key=os.getenv("GITHUB_TOKEN")
    )

    vectorstore = FAISS.from_documents(splits, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    # ✅ RETURN BOTH
    return vectorstore, retriever

async def wikipedia_search(query: str):
    """Search Wikipedia and return text result."""
    global wiki_tools

    search_tool = next(
        (t for t in wiki_tools if t.name == "search_wikipedia"),
        None
    )

    if not search_tool:
        return "No Wikipedia tool available."

    # simple topic cleanup for better Wikipedia matching
    cleaned_query = query.lower()

    if "marek" in cleaned_query:
        wiki_query = "Marek's disease"
    elif "mite" in cleaned_query or "mites" in cleaned_query:
        wiki_query = "Poultry red mite"
    elif "coccidiosis" in cleaned_query:
        wiki_query = "Coccidiosis"
    else:
        wiki_query = (
            query.replace("What are symptoms of", "")
                 .replace("What is", "")
                 .replace("in chickens", "")
                 .strip()
        )

    print(f"\nWikipedia query: {wiki_query}")

    results = await search_tool.ainvoke({"query": wiki_query})
    return str(results)[:1500]

async def assistant_node(state: State) -> Command[Literal["__end__"]]:
    """Single backyard poultry assistant node with hybrid local RAG + Wikipedia fallback."""
    global retriever, vectorstore, llm

    print("\n" + "=" * 50)
    print("POULTRY ASSISTANT NODE")
    print("=" * 50)

    user_question = state["messages"][-1].content

    # Search local knowledge base first, with scores
    scored_docs = vectorstore.similarity_search_with_score(user_question, k=2)

    docs = [doc for doc, score in scored_docs]
    scores = [score for doc, score in scored_docs]

    print(f"\nLocal search scores: {scores}")

    # Lower score = better match
    use_local_rag = len(scores) > 0 and scores[0] < 1.0

    if use_local_rag:
        retrieved_context = "\n\n".join(doc.page_content for doc in docs)

        print("\nUsing LOCAL knowledge base")
        print("\nRetrieved Context:")
        print(retrieved_context)

        rag_message = HumanMessage(
            content=f"""
Answer only from the poultry knowledge base below.
If the answer is not clearly contained in the knowledge base, say you do not have enough local information.
Do not guess.
Keep the answer beginner-friendly and structured.

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

        response = await assistant_agent.ainvoke({"messages": [rag_message]})
        final_message = response["messages"][-1]

    else:
        print("\nLocal match weak. Falling back to Wikipedia.")

        wiki_result = await wikipedia_search(user_question)

        print("\nWikipedia Result Preview:")
        print(wiki_result[:500])

        fallback_message = HumanMessage(
            content=f"""
The local poultry knowledge base did not contain a strong match.

Use the Wikipedia information below to answer the user's poultry question.

WIKIPEDIA DATA:
{wiki_result}

Instructions:
- Use the Wikipedia data as your primary source
- Keep the answer beginner-friendly
- Do not add unrelated information

Format:
Direct Answer:
Important Details:
Safety Notes:
Simple Next Step:

USER QUESTION:
{user_question}
"""
        )

        response = await llm.ainvoke([fallback_message])
        final_message = response

    print("\nAssistant Output:")
    print(final_message.content)
    print("\n" + "=" * 50 + "\n")

    return Command(
        update={"messages": state["messages"] + [final_message]},
        goto="__end__"
    )
    
async def main():
    """Run the multi-agent content creation workflow."""
    global assistant_agent, retriever, vectorstore, wiki_tools, llm
    
    # Check for required API keys to see if they are loaded properly
    #print("GITHUB_TOKEN:", os.getenv("GITHUB_TOKEN"))
    #print("TAVILY_API_KEY:", os.getenv("TAVILY_API_KEY"))
    
    if not os.getenv("GITHUB_TOKEN"):
        print("Error: GITHUB_TOKEN not found.")
        print("Add GITHUB_TOKEN=your-token to a .env file")
        return
    
    if not os.getenv("TAVILY_API_KEY"):
        print("Error: TAVILY_API_KEY not found.")
        print("Add TAVILY_API_KEY=your-key to a .env file")
        print("Get your API key from: https://app.tavily.com/")
        return
    # Initialize LLM
    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0.7,
        base_url="https://models.github.ai/inference",
        api_key=os.getenv("GITHUB_TOKEN")
    )
    vectorstore, retriever = build_retriever()
    print("Retriever loaded from data/chicken_guide.md")

    # Load prompts from your local filesystem
    with open("templates/assistant.json", "r") as f:
        assistant_data = json.load(f)
        assistant_prompt = assistant_data.get(
            "template",
            "You are a helpful backyard poultry assistant."
        )

    # Get Tavily API key from environment
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    # Create MCP client for Tavily
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
    
    # Get tools from the client
    researcher_tools = await research_client.get_tools()
    global wiki_tools
    wiki_tools = researcher_tools
    
    print(f"Research tools: {[tool.name for tool in researcher_tools]}")
    
    assistant_agent = create_agent(
        llm,
        tools=researcher_tools,
        system_prompt=assistant_prompt
    )
    
    # Build the Graph without manual edges (Edgeless Handoff)
    builder = StateGraph(State)
    builder.add_node("assistant", assistant_node)
    builder.add_edge(START, "assistant")
    graph = builder.compile()
        
    # Run the workflow
        
    print("\n" + "="*50)
    print("Starting Multi-Agent Content Creation Workflow")
    print("="*50 + "\n")

    user_input = input("Ask your backyard poultry question: ")
    initial_message = HumanMessage(content=user_input)
    
    final_state = {
        "messages": [initial_message]
    }

    async for chunk in graph.astream(
        final_state,
        stream_mode="updates"
    ):
        print("\n--- STREAM UPDATE ---")
        
        for node_name, node_update in chunk.items():
            print(f"✓ Agent completed: {node_name}")
            #print(f"Updated keys: {list(node_update.keys())}")
            
            # Merge node updates into final_state
            if isinstance(node_update, dict):
                final_state.update(node_update)
    
    print("\n" + "=" * 50)
    print("Workflow Complete")
    print("=" * 50 + "\n")
    
    if final_state.get("messages"):
        last_message = final_state["messages"][-1]
        print("Final Output:")
        print(getattr(last_message, "content", "No response available"))
if __name__ == "__main__":
    asyncio.run(main())