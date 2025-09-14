from dotenv import load_dotenv
import os
import json
import re
from crewai import Agent, LLM
from crewai.tools import BaseTool
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Load and split PDF
pdf_path = r"C:\Nithin\Hackathon\Gradient Accent\crewproject\skupolicy.pdf"
loader = PyPDFLoader(pdf_path)
documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
docs = text_splitter.split_documents(documents)

# Embeddings and vector store
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GEMINI_API_KEY
)
db = Chroma.from_documents(docs, embeddings, persist_directory="./chroma_db")
retriever = db.as_retriever()

# LLM setup
llm = LLM(
    model="gemini/gemini-1.5-flash",
    api_key=GEMINI_API_KEY
)

# Return policy logic
def check_return_policy(sku_id: str, days_since_purchase: int) -> str:
    print(f"\n Checking return policy for SKU: {sku_id}")
    print(f" Days since purchase: {days_since_purchase}")

    query = f"Return policy for {sku_id}"
    retrieved_docs = retriever.invoke(query, config={"n_results": min(6, len(docs))})

    # Filter chunks that explicitly mention the SKU
    filtered_docs = [doc for doc in retrieved_docs if sku_id in doc.page_content]

    if not filtered_docs:
        print(" No chunks explicitly mention the SKU. Falling back to keyword search.")
        filtered_docs = [doc for doc in docs if sku_id in doc.page_content]

    if not filtered_docs:
        print(" No matching chunks found. Returning ineligible.")
        return json.dumps({
            "eligible": False,
            "reason": f"Return policy for SKU={sku_id} not found in PDF."
        })

    # Use only the first matching chunk for this SKU
    sku_chunk = filtered_docs[0].page_content
    print(f"\n Selected Chunk for SKU:\n{sku_chunk[:500]}...")

    # Extract return window from the SKU-specific chunk
    match = re.search(rf"{sku_id}.*?(\d+)\s+day[s]?", sku_chunk, re.IGNORECASE | re.DOTALL)
    if not match:
        match = re.search(r"(\d+)\s+day[s]?", sku_chunk, re.IGNORECASE)

    if match:
        allowed_days = int(match.group(1))
        print(f" Extracted return window for {sku_id}: {allowed_days} days")
        if days_since_purchase <= allowed_days:
            print(" Product is eligible for return.")
            return json.dumps({
                "eligible": True,
                "reason": f" Product is within the {allowed_days}-day return window."
            })
        else:
            print(" Product exceeds return window.")
            return json.dumps({
                "eligible": False,
                "reason": f" Product exceeds the {allowed_days}-day return window."
            })
    else:
        print(" No return window found in chunk. Using LLM for fallback.")
        prompt = f"""
You are a policy expert. Given the company's return policy context below, answer if the product with the given SKU can be returned based on the days since purchase.

POLICY CONTEXT:
{sku_chunk}

Request:
SKU ID: {sku_id}
Days Since Purchase: {days_since_purchase}

Answer STRICTLY in this JSON format only:
{{
  "eligible": true/false,
  "reason": "<clear explanation>"
}}
"""
        response = llm.run(prompt)
        print("\n LLM Response:")
        print(response)
        return response

# CrewAI-compatible tool
class CheckReturnPolicyTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="check_return_policy",
            description="Checks if a product is eligible for return based on SKU and days since purchase."
        )

    def _run(self, sku_id: str, days_since_purchase: int) -> str:
        return check_return_policy(sku_id, days_since_purchase)

check_return_policy_tool = CheckReturnPolicyTool()

# Agent setup
policy_agent = Agent(
    role="Policy Agent",
    goal="Decide return eligibility from company's policy PDF.",
    backstory="Reads company's return policies and makes eligibility decisions.",
    tools=[check_return_policy_tool],
    llm=llm,
    verbose=True
)

# Debug test
if __name__ == "__main__":
    result = check_return_policy_tool.run(
        sku_id="SKU005",
        days_since_purchase=15
    )
    print("\n Final Decision from Policy Agent:")
    print(result)