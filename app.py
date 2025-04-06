import streamlit as st
from cerebras.cloud.sdk import Cerebras
import openai
# prompt.py が存在し、RECIPE_BASE_PROMPTが定義されていると仮定
# もし存在しない場合は、適切に定義してください
try:
    from prompt import RECIPE_BASE_PROMPT
except ImportError:
    # テスト用にダミーのプロンプトを設定
    RECIPE_BASE_PROMPT = "You are a helpful recipe assistant."
    print("Warning: 'prompt.py' not found or 'RECIPE_BASE_PROMPT' not defined. Using a default system prompt.")

import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# Set page configuration
st.set_page_config(page_icon="🤖", layout="wide", page_title="Recipe Infographic Prompt Generator")


def icon(emoji: str):
    """Shows an emoji as a Notion-style page icon."""
    st.write(
        f'<span style="font-size: 78px; line-height: 1">{emoji}</span>',
        unsafe_allow_html=True,
    )


# Display header
icon("🧠🧑‍🍳")
st.title("ChatBot with Cerebras API")
st.subheader("Deploying Cerebras on Streamlit", divider="orange", anchor=False)

# Define model details
models = {
    "llama3.1-8b": {"name": "Llama3.1-8b", "tokens": 8192, "developer": "Meta"},
    "llama-3.3-70b": {"name": "Llama-3.3-70b", "tokens": 8192, "developer": "Meta"}
}

BASE_URL = "http://localhost:8000/v1" # Optillmが使用する場合のベースURL

# --- APIキーの処理 ---
# 環境変数からAPIキーを取得試行
api_key_from_env = os.getenv("CEREBRAS_API_KEY")
# APIキー入力フィールドを表示する必要があるかどうかのフラグ
show_api_key_input = not bool(api_key_from_env)
# アプリケーションで使用する最終的なAPIキー変数
api_key = None

# --- サイドバーの設定 ---
with st.sidebar:
    st.title("Settings")

    if show_api_key_input:
        # 環境変数にキーがない場合、入力フィールドを表示
        st.markdown("### :red[Enter your Cerebras API Key below]")
        api_key_input = st.text_input("Cerebras API Key:", type="password", key="api_key_input_field")
        if api_key_input:
            api_key = api_key_input # 入力されたキーを使用
    else:
        # 環境変数にキーがある場合、それを使用
        api_key = api_key_from_env
        st.success("✓ API Key loaded from environment") # 任意：ロードされたことを通知

    # Model selection
    model_option = st.selectbox(
        "Choose a model:",
        options=list(models.keys()),
        format_func=lambda x: models[x]["name"],
        key="model_select"
    )

    # Max tokens slider
    max_tokens_range = models[model_option]["tokens"]
    # デフォルト値を最大値ではなく、より一般的な値に設定（例：2048）
    default_tokens = min(2048, max_tokens_range)
    max_tokens = st.slider(
        "Max Tokens:",
        min_value=512,
        max_value=max_tokens_range,
        value=default_tokens, # 修正：デフォルト値を設定
        step=512,
        help="Select the maximum number of tokens (words) for the model's response."
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
    st.markdown("2. Chat away, powered by Cerebras.")
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
    avatar = '🤖' if message["role"] == "assistant" else '🦔'
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- チャット入力と処理 ---
if prompt := st.chat_input("Enter your prompt here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar='🦔'):
        st.markdown(prompt)

    try:
        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            full_response = ""

            # APIに送信するメッセージリストを作成 (システムプロンプト + ユーザープロンプト)
            # 必要に応じて過去の会話履歴も加えることができます
            # 例: messages_for_api = [{"role": "system", "content": RECIPE_BASE_PROMPT}] + st.session_state.messages[-N:] + [{"role": "user", "content": prompt}]
            messages_for_api=[
                {"role": "system", "content": RECIPE_BASE_PROMPT},
                {"role": "user", "content": prompt} # 最新のプロンプトのみ送信する場合
                # 全履歴を送信する場合:
                # *st.session_state.messages
            ]


            # ストリーミングで応答を取得
            # Cerebras SDK と OpenAI SDK で引数名や構造が同じか確認
            stream_kwargs = {
               "model": model_option,
               "messages": messages_for_api,
               "max_tokens": max_tokens,
               "stream": True,
            }
            # Optillm (OpenAI互換) と Cerebras SDK のcreateメソッドの互換性を確認
            response_stream = client.chat.completions.create(**stream_kwargs)

            for chunk in response_stream:
                # chunkの構造がSDKによって異なる可能性を考慮
                chunk_content = ""
                # OpenAI SDK / Cerebras SDK (OpenAI互換の場合) の一般的な構造
                if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content'):
                    # contentがNoneの場合も考慮
                    chunk_content = chunk.choices[0].delta.content or ""

                if chunk_content:
                    full_response += chunk_content
                    response_placeholder.markdown(full_response + "▌") # カーソル表示

            # 最終的な応答を表示（カーソルなし）
            response_placeholder.markdown(full_response)
            # アシスタントの応答を履歴に追加
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"Error generating response: {str(e)}", icon="🚨")
