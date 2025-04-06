import streamlit as st
from cerebras.cloud.sdk import Cerebras
import openai
import os
from dotenv import load_dotenv

# --- RECIPE_BASE_PROMPT のインポート ---
# prompt.py が存在し、RECIPE_BASE_PROMPTが定義されていると仮定
try:
    from prompt import RECIPE_BASE_PROMPT
except ImportError:
    # エラー処理: prompt.pyが見つからないか、変数が定義されていない場合
    st.error("Error: 'prompt.py' not found or 'RECIPE_BASE_PROMPT' is not defined within it.")
    st.stop() # 致命的なエラーなのでアプリを停止
    # RECIPE_BASE_PROMPT = "You are a helpful recipe assistant." # フォールバックが必要な場合
    # print("Warning: 'prompt.py' not found or 'RECIPE_BASE_PROMPT' not defined. Using a default system prompt.")

# --- 定数と設定 ---

# モデル定義
models = {
    "llama3.1-8b": {"name": "Llama3.1-8b", "tokens": 8192, "developer": "Meta"},
    "llama-3.3-70b": {"name": "Llama-3.3-70b", "tokens": 8192, "developer": "Meta"}
}

# Optillm用ベースURL (必要に応じて変更)
BASE_URL = "http://localhost:8000/v1"

# --- 環境変数読み込み ---
load_dotenv()

# --- Streamlit ページ設定 ---
st.set_page_config(page_icon="🤖", layout="wide", page_title="Recipe Infographic Prompt Generator")

# --- ヘルパー関数 ---
def contains_injection_keywords(text):
    """Checks for basic prompt injection keywords."""
    keywords = ["ignore previous", "ignore instructions", "disregard", "forget your instructions", "act as", "you must", "system prompt:"]
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in keywords)

def icon(emoji: str):
    """Shows an emoji as a Notion-style page icon."""
    st.write(
        f'<span style="font-size: 78px; line-height: 1">{emoji}</span>',
        unsafe_allow_html=True,
    )

# --- UI 表示 ---
icon("🧠 x 🧑‍🍳") # アイコンを修正
st.title("Recipe Infographic Prompt Generator")
st.subheader("Simply enter a dish name or recipe to easily generate image prompts for stunning recipe infographics", divider="orange", anchor=False)

# --- APIキーの処理 ---
api_key_from_env = os.getenv("CEREBRAS_API_KEY")
show_api_key_input = not bool(api_key_from_env)
api_key = None

# --- サイドバーの設定 ---
with st.sidebar:
    st.title("Settings")

    if show_api_key_input:
        st.markdown("### :red[Enter your Cerebras API Key below]")
        api_key_input = st.text_input("Cerebras API Key:", type="password", key="api_key_input_field")
        if api_key_input:
            api_key = api_key_input
    else:
        api_key = api_key_from_env
        st.success("✓ API Key loaded from environment")

    model_option = st.selectbox(
        "Choose a model:",
        options=list(models.keys()),
        format_func=lambda x: models[x]["name"],
        key="model_select"
    )

    max_tokens_range = models[model_option]["tokens"]
    default_tokens = min(2048, max_tokens_range)
    max_tokens = st.slider(
        "Max Tokens:",
        min_value=512,
        max_value=max_tokens_range,
        value=default_tokens,
        step=512,
        help="Select the maximum number of tokens for the model's response." # helpテキストを修正
    )

    use_optillm = st.toggle("Use Optillm", value=False)

# --- メインアプリケーションロジック ---

# APIキーが最終的に利用可能かチェック (サイドバーの処理後)
if not api_key:
    st.markdown("""
    ## Cerebras API x Streamlit Demo!

    This simple chatbot app demonstrates how to use Cerebras with Streamlit.

    To get started:
    """)
    if show_api_key_input:
         # サイドバー入力が表示されている場合
        st.warning("1. :red[Enter your Cerebras API Key in the sidebar.]")
    else:
         # 環境変数から読み込むべきだったが、見つからなかった/空だった場合
        st.error("1. :red[CEREBRAS_API_KEY environment variable not found or empty.] Please set it in your environment (e.g., in a .env file).")
    st.markdown("2. Configure your settings and start chatting.") # メッセージを少し変更
    st.stop() # APIキーがない場合はここで停止

# APIキーが利用可能な場合のみクライアントを初期化
try:
    if use_optillm:
        client = openai.OpenAI(
            base_url=BASE_URL, # Optillmがlocalhostを使用する場合
            api_key=api_key
        )
    else:
        # Cerebras SDKがapi_keyだけで初期化可能か確認
        # SDKのバージョンや使い方によってはendpoint等の追加設定が必要な場合あり
        client = Cerebras(api_key=api_key)
    # st.success("API Client Initialized.") # 任意：初期化成功メッセージ
except Exception as e:
    st.error(f"Failed to initialize API client: {str(e)}", icon="🚨")
    st.stop() # クライアント初期化失敗時も停止

# --- チャット履歴管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "selected_model" not in st.session_state:
    st.session_state.selected_model = None

# モデルが変更されたら履歴をクリア
if st.session_state.selected_model != model_option:
    st.session_state.messages = []
    st.session_state.selected_model = model_option

# チャットメッセージを表示
for message in st.session_state.messages:
    avatar = '🤖' if message["role"] == "assistant" else '🦔' # アバターを調整 (ユーザーはハリネズミ?)
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- チャット入力と処理 (インデント修正済み) ---
if prompt := st.chat_input("Enter food name/food recipe here..."):
    # ☆★☆ 入力検証 ☆★☆
    if contains_injection_keywords(prompt):
        st.error("Your input seems to contain instructions. Please provide only the dish name or recipe.", icon="🚨")
    elif len(prompt) > 4000: # 文字数制限は適切に調整してください
        st.error("Input is too long. Please provide a shorter recipe or dish name.", icon="🚨")
    else:
        # ↓↓↓ --- 検証をパスした場合の処理 (ここからインデント) --- ↓↓↓
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar='🦔'): # ユーザーアバター
            st.markdown(prompt)

        try:
            with st.chat_message("assistant", avatar="🤖"): # アシスタントアバター
                response_placeholder = st.empty()
                full_response = ""

                # APIに送信するメッセージリストを作成
                messages_for_api=[
                    {"role": "system", "content": RECIPE_BASE_PROMPT},
                    {"role": "user", "content": prompt} # 最新のユーザープロンプトのみ
                ]

                # ストリーミングで応答を取得
                stream_kwargs = {
                   "model": model_option,
                   "messages": messages_for_api,
                   "max_tokens": max_tokens,
                   "stream": True,
                }
                response_stream = client.chat.completions.create(**stream_kwargs)

                for chunk in response_stream:
                    chunk_content = ""
                    # API応答の構造に合わせて調整が必要な場合あり
                    if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content'):
                        chunk_content = chunk.choices[0].delta.content or ""

                    if chunk_content:
                        full_response += chunk_content
                        response_placeholder.markdown(full_response + "▌") # カーソル表示

                # 最終的な応答を表示（カーソルなし）
                response_placeholder.markdown(full_response)

                # ☆★☆ 出力検証 ☆★☆
                expected_keywords = ["infographic", "step-by-step", "ingredient", "layout", "minimal style"]
                lower_response = full_response.lower()
                is_valid_format = any(keyword in lower_response for keyword in expected_keywords)
                # システムプロンプトで定義した拒否応答の文字列と一致させる
                is_refusal = "please provide a valid food dish name or recipe for infographic prompt generation" in lower_response

                if not is_valid_format and not is_refusal:
                    # 期待される形式でもなく、意図した拒否応答でもない場合
                    st.warning("The generated response might not contain expected keywords or could indicate an issue.", icon="⚠️")
                elif is_refusal:
                    # 意図した拒否応答の場合 (infoレベルで表示)
                     st.info("Input was determined to be invalid or unrelated. Please provide a valid food dish/recipe.") # メッセージを少し調整

                # アシスタントの応答を履歴に追加
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"Error generating response: {str(e)}", icon="🚨")
        # ↑↑↑ --- ここまでが else 節のインデント内 --- ↑↑↑
