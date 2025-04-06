import streamlit as st
from cerebras.cloud.sdk import Cerebras
import openai
from prompt import RECIPE_BASE_PROMPT

# Set page configuration
st.set_page_config(page_icon="🤖", layout="wide", page_title="Recipe Infographic Prompt Generator")


def icon(emoji: str):
    """Shows an emoji as a Notion-style page icon."""
    st.write(
        f'<span style="font-size: 78px; line-height: 1">{emoji}</span>',
        unsafe_allow_html=True,
    )


# Display header
icon("🧠")
st.title("ChatBot with Cerebras API")
st.subheader("Deploying Cerebras on Streamlit", divider="orange", anchor=False)

# Define model details
models = {
    "llama3.1-8b": {"name": "Llama3.1-8b", "tokens": 8192, "developer": "Meta"},
    "llama-3.3-70b": {"name": "Llama-3.3-70b", "tokens": 8192, "developer": "Meta"}
}

BASE_URL = "http://localhost:8000/v1"

# Sidebar configuration
with st.sidebar:
    st.title("Settings")
    st.markdown("### :red[Enter your Cerebras API Key below]")
    api_key = st.text_input("Cerebras API Key:", type="password")

    # Model selection
    model_option = st.selectbox(
        "Choose a model:",
        options=list(models.keys()),
        format_func=lambda x: models[x]["name"],
        key="model_select"
    )

    # Max tokens slider
    max_tokens_range = models[model_option]["tokens"]
    max_tokens = st.slider(
        "Max Tokens:",
        min_value=512,
        max_value=max_tokens_range,
        value=max_tokens_range,
        step=512,
        help="Select the maximum number of tokens (words) for the model's response."
    )

    use_optillm = st.toggle("Use Optillm", value=False)

# Check for API key before proceeding
if not api_key:
    st.markdown("""
    ## Cerebras API x Streamlit Demo!

    This simple chatbot app demonstrates how to use Cerebras with Streamlit.

    To get started:
    1. :red[Enter your Cerebras API Key in the sidebar.]
    2. Chat away, powered by Cerebras.
    """)
    st.stop()

# Initialize Cerebras client
# client = Cerebras(api_key=api_key)

if use_optillm:
    client = openai.OpenAI(
        base_url="http://localhost:8000/v1",
        api_key=api_key
    )
else:
    client = Cerebras(api_key=api_key)


# Chat history management
if "messages" not in st.session_state:
    st.session_state.messages = []

if "selected_model" not in st.session_state:
    st.session_state.selected_model = None

# Clear history if model changes
if st.session_state.selected_model != model_option:
    st.session_state.messages = []
    st.session_state.selected_model = model_option

# Display chat messages
for message in st.session_state.messages:
    avatar = '🤖' if message["role"] == "assistant" else '🦔'
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Chat input and processing
if prompt := st.chat_input("Enter your prompt here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar='🦔'):
        st.markdown(prompt)

    try:
        # Create empty container for streaming response
        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            full_response = ""

            # Stream the response
            for chunk in client.chat.completions.create(
                model=model_option,
                messages=[
                  {"role": "system", "content": RECIPE_BASE_PROMPT},
                  {"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                stream=True,  # Ensure Cerebras API supports streaming
                # base_url=BASE_URL
            ):
                if chunk.choices[0].delta.content:
                    chunk_content = chunk.choices[0].delta.content
                    full_response += chunk_content
                    response_placeholder.markdown(full_response + "▌")

            # Update the final response without cursor
            response_placeholder.markdown(full_response)
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"Error generating response: {str(e)}", icon="🚨")
