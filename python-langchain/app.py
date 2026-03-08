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


# Shared state for the workflow graph.
# This defines the structure of the data that all nodes (agents/tools)
# will read from and write to.
#
# messages:
#   - Stores the full conversation history (user messages, AI responses,
#     and tool outputs).
#   - Annotated with add_messages so that when multiple nodes update the
#     state, new messages are appended instead of overwriting existing ones.
#
# This allows all agents in the workflow to share memory and build
# on each other's outputs safely.

class State(TypedDict):
    messages: Annotated[list, add_messages]

load_dotenv()


async def main():
    """Run the multi-agent content creation workflow."""
    
    # Check for required API keys
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
    
    # We'll add more here in the next steps
    
    print("\nOrchestration setup complete!")


if __name__ == "__main__":
    asyncio.run(main())