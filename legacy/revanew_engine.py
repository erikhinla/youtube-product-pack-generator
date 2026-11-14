import re
import json
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Setup Streamlit Config
st.set_page_config(page_title="RevAnew Engine", page_icon="⚡", layout="wide")

st.title("⚡ RevAnew Extraction Engine")
st.subtitle("Turn YouTube Videos into 8–12 Asset Digital Product Ecosystems")

# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def extract_youtube_id(url: str) -> str:
    """Extract YouTube Video ID from standard or short URLs."""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_video_transcript(video_id: str) -> str:
    """Fetch video transcript text using YouTube Transcript API."""
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join([item['text'] for item in transcript_list])

def generate_revanew_concept_board(transcript: str, api_key: str) -> dict:
    """Run extraction pipeline via LLM to construct digital artifacts and pricing strategy."""
    llm = ChatOpenAI(temperature=0.3, model_name="gpt-4", openai_api_key=api_key)
    
    system_prompt = """
    You are the RevAnew Engine, an automated product development system for creators.
    Your task is to take a YouTube video transcript, extract its core intellectual frameworks, 
    and transform them into a complete digital product ecosystem (8-12 digital assets).

    Return ONLY a valid JSON object matching this schema:
    {
        "video_summary": "Brief summary of the video's core lesson",
        "core_frameworks": ["Framework 1", "Framework 2", ...],
        "suggested_price": "$27",
        "price_justification": "Why this price point optimizes the Self-Liquidating Offer (SLO) model.",
        "artifacts": [
            {
                "asset_name": "Market Avatar Worksheet",
                "category": "Implementation Pack",
                "description": "Short description of what is included in this digital file."
            },
            ...
        ]
    }
    """

    user_prompt = f"Extract and generate the RevAnew concept board for this transcript:\n\n{transcript[:6000]}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    response = llm(messages)
    return json.loads(response.content)

# ------------------------------------------------------------------------------
# User Interface Form
# ------------------------------------------------------------------------------
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
youtube_url = st.text_input("Drop YouTube Video URL Here:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Generate RevAnew Concept Board") and youtube_url:
    if not openai_api_key:
        st.error("Please provide an OpenAI API key in the sidebar.")
    else:
        video_id = extract_youtube_id(youtube_url)
        if not video_id:
            st.error("Invalid YouTube URL. Please check the link and try again.")
        else:
            with st.spinner("Extracting transcript & compiling digital artifacts..."):
                try:
                    # 1. Fetch transcript
                    transcript = get_video_transcript(video_id)
                    
                    # 2. Run engine extraction logic
                    concept_board = generate_revanew_concept_board(transcript, openai_api_key)
                    
                    # 3. Render Output Board
                    st.success("RevAnew Extraction Complete!")
                    st.divider()

                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.header("📋 Proposed Digital Artifacts Package")
                        for idx, artifact in enumerate(concept_board.get("artifacts", []), 1):
                            with st.expander(f"{idx}. {artifact['asset_name']} ({artifact['category']})"):
                                st.write(artifact['description'])

                    with col2:
                        st.header("💰 Pricing Strategy")
                        st.metric(label="Recommended Bundle Price", value=concept_board.get("suggested_price", "$27"))
                        st.caption(concept_board.get("price_justification", ""))

                        st.subheader("Core Frameworks Extracted")
                        for fw in concept_board.get("core_frameworks", []):
                            st.markdown(f"- {fw}")

                except Exception as e:
                    st.error(f"Error processing video: {str(e)}")
