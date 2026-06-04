from mcp.server.fastmcp import FastMCP
from transformers import pipeline

mcp = FastMCP("sentiment-analysis")

# Lazy load model
pipe = None

def get_pipe():
    global pipe
    if not pipe:
        pipe = pipeline("text-classification", model="ProsusAI/finbert")
    return pipe

@mcp.tool()
def analyze_sentiment(text: str) -> str:
    """Analyze sentiment of financial text"""
    try:
        p = get_pipe()
        # Truncate to 512 chars for simplicity
        result = p(text[:512])[0]
        return f"Label: {result['label']}, Score: {result['score']:.4f}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run()
