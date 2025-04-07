import streamlit as st
from cerebras.cloud.sdk import Cerebras
import openai
import os
from dotenv import load_dotenv
import base64 # 画像デコード用に追加
from io import BytesIO # 画像ダウンロード用に追加
from together import Together # Together AI SDKを追加

# --- RECIPE_BASE_PROMPT のインポート ---
try:
    from prompt import RECIPE_BASE_PROMPT
except ImportError:
    st.error("Error: 'prompt.py' not found or 'RECIPE_BASE_PROMPT' is not defined within it.")
    st.stop()

# --- 定数と設定 ---
models = {
    "llama3.1-8b": {"name": "Llama3.1-8b", "tokens": 8192, "developer": "Meta"},
    "llama-3.3-70b": {"name": "Llama-3.3-70b", "tokens": 8192, "developer": "Meta"}
}
BASE_URL = "http://localhost:8000/v1"
IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell-Free" # 使用する画像生成モデル

# --- 環境変数読み込み ---
load_dotenv()

# --- Streamlit ページ設定 ---
st.set_page_config(page_icon="🤖", layout="wide", page_title="Recipe Infographic Prompt Generator")

# --- ヘルパー関数 ---
def contains_injection_keywords(text):
    keywords = ["ignore previous", "ignore instructions", "disregard", "forget your instructions", "act as", "you must", "system prompt:"]
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in keywords)

def icon(emoji: str):
    st.write(
        f'<span style="font-size: 78px; line-height: 1">{emoji}</span>',
        unsafe_allow_html=True,
    )

# --- 画像生成関数 ---
@st.cache_data(show_spinner="Generating image...") # 結果をキャッシュ & スピナー表示
def generate_image_from_prompt(_together_client, prompt_text):
    """Generates an image using Together AI and returns image bytes."""
    try:
        response = _together_client.images.generate(
            prompt=prompt_text,
            model=IMAGE_MODEL,
            width=1024,
            height=768, # モデルに合わせて調整が必要な場合あり
            steps=4,    # モデルに合わせて調整が必要な場合あり
            n=1,
            response_format="b64_json",
            # stop=[] # stopは通常不要
        )
        if response.data and response.data[0].b64_json:
            b64_data = response.data[0].b64_json
            image_bytes = base64.b64decode(b64_data)
            return image_bytes
        else:
            st.error("Image generation failed: No image data received.")
            return None
    except Exception as e:
        st.error(f"Image generation error: {e}", icon="🚨")
        return None

# --- UI 表示 ---
icon("🧠 x 🧑‍🍳")
st.title("Recipe Infographic Prompt Generator")
st.subheader("Simply enter a dish name or recipe to easily generate image prompts for stunning recipe infographics", divider="orange", anchor=False)

# --- APIキーの処理 ---
# Cerebras API Key
api_key_from_env = os.getenv("CEREBRAS_API_KEY")
show_api_key_input = not bool(api_key_from_env)
cerebras_api_key = None

# Together AI API Key Check
together_api_key = os.getenv("TOGETHER_API_KEY")

# --- サイドバーの設定 ---
with st.sidebar:
    st.title("Settings")

    # Cerebras Key Input
    if show_api_key_input:
        st.markdown("### :red[Enter your Cerebras API Key below]")
        api_key_input = st.text_input("Cerebras API Key:", type="password", key="cerebras_api_key_input_field")
        if api_key_input:
            cerebras_api_key = api_key_input
    else:
        cerebras_api_key = api_key_from_env
        st.success("✓ Cerebras API Key loaded from environment")

    # Together Key Status
    if not together_api_key:
         st.warning("TOGETHER_API_KEY environment variable not set. Image generation will not work.", icon="⚠️")
    else:
         st.success("✓ Together API Key loaded from environment") # キー自体は表示しない

    # Model selection
    model_option = st.selectbox(
        "Choose a LLM model:", # ラベルを明確化
        options=list(models.keys()),
        format_func=lambda x: models[x]["name"],
        key="model_select"
    )

    # Max tokens slider
    max_tokens_range = models[model_option]["tokens"]
    default_tokens = min(2048, max_tokens_range)
    max_tokens = st.slider(
        "Max Tokens (LLM):", # ラベルを明確化
        min_value=512,
        max_value=max_tokens_range,
        value=default_tokens,
        step=512,
        help="Select the maximum number of tokens for the language model's response."
    )

    use_optillm = st.toggle("Use Optillm (for Cerebras)", value=False) # ラベルを明確化

# --- メインアプリケーションロジック ---

# APIキー(Cerebras)が最終的に利用可能かチェック
if not cerebras_api_key:
    # (以前のエラー表示ロジックと同じ)
    st.markdown("...") # 省略: APIキーがない場合の説明
    st.stop()

# APIクライアント初期化 (Cerebras & Together)
try:
    # Cerebras Client
    if use_optillm:
        llm_client = openai.OpenAI(base_url=BASE_URL, api_key=cerebras_api_key)
    else:
        llm_client = Cerebras(api_key=cerebras_api_key)

    # Together Client (APIキーがあれば初期化)
    image_client = None
    if together_api_key:
        image_client = Together(api_key=together_api_key) # 明示的にキーを渡すことも可能

except Exception as e:
    st.error(f"Failed to initialize API client(s): {str(e)}", icon="🚨")
    st.stop()

# --- チャット履歴管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generated_images" not in st.session_state:
     st.session_state.generated_images = {} # 画像データをメッセージIDごとに保存 {msg_idx: image_bytes}

if "selected_model" not in st.session_state:
    st.session_state.selected_model = None

# モデルが変更されたら履歴をクリア (画像履歴もクリアするかは要検討)
if st.session_state.selected_model != model_option:
    st.session_state.messages = []
    st.session_state.generated_images = {} # 画像履歴もクリア
    st.session_state.selected_model = model_option

# --- チャットメッセージの表示ループ ---
# このループでは過去のメッセージを表示し、それぞれに画像生成ボタンをつける
for idx, message in enumerate(st.session_state.messages):
    avatar = '🤖' if message["role"] == "assistant" else '🦔'
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

        # アシスタントのメッセージで、かつ有効な形式の可能性があり、画像クライアントが利用可能な場合
        if message["role"] == "assistant" and image_client:
             # 簡単なチェック: 拒否メッセージではないことを確認
             lower_content = message["content"].lower()
             is_likely_prompt = "please provide a valid food dish name" not in lower_content

             if is_likely_prompt:
                 button_key = f"gen_img_{idx}"
                 if st.button("Generate Image ✨", key=button_key):
                     # 画像生成関数を呼び出し、結果をセッション状態に保存
                     image_bytes = generate_image_from_prompt(image_client, message["content"])
                     if image_bytes:
                         st.session_state.generated_images[idx] = image_bytes
                     # ボタンが押されたら再実行されるので、画像表示は下のブロックで行う

                 # 対応する画像データがセッション状態にあれば表示・ダウンロードボタンを表示
                 if idx in st.session_state.generated_images:
                     img_bytes = st.session_state.generated_images[idx]
                     st.image(img_bytes, caption=f"Generated Image for Prompt #{idx+1}")
                     st.download_button(
                         label="Download Image 💾",
                         data=img_bytes,
                         file_name=f"recipe_infographic_{idx+1}.png",
                         mime="image/png",
                         key=f"dl_img_{idx}"
                     )

# --- チャット入力と新しいメッセージの処理 ---
if prompt := st.chat_input("Enter food name/food recipe here..."):
    # 入力検証
    if contains_injection_keywords(prompt):
        st.error("Your input seems to contain instructions. Please provide only the dish name or recipe.", icon="🚨")
    elif len(prompt) > 4000:
        st.error("Input is too long. Please provide a shorter recipe or dish name.", icon="🚨")
    else:
        # --- 検証をパスした場合の処理 ---
        st.session_state.messages.append({"role": "user", "content": prompt})

        # ユーザーメッセージを表示
        with st.chat_message("user", avatar='🦔'):
            st.markdown(prompt)

        # アシスタントの応答を生成・表示
        try:
            with st.chat_message("assistant", avatar="🤖"):
                response_placeholder = st.empty()
                full_response = ""

                messages_for_api=[
                    {"role": "system", "content": RECIPE_BASE_PROMPT},
                    {"role": "user", "content": prompt}
                ]
                stream_kwargs = {
                   "model": model_option, "messages": messages_for_api,
                   "max_tokens": max_tokens, "stream": True,
                }
                # LLM Client を使用
                response_stream = llm_client.chat.completions.create(**stream_kwargs)

                for chunk in response_stream:
                    chunk_content = ""
                    if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content'):
                        chunk_content = chunk.choices[0].delta.content or ""
                    if chunk_content:
                        full_response += chunk_content
                        response_placeholder.markdown(full_response + "▌")

                # 最終応答表示
                response_placeholder.markdown(full_response)

                # --- ここで新しいアシスタントメッセージに対する処理 ---
                # 応答を履歴に追加 *してから* インデックスを取得
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                new_message_idx = len(st.session_state.messages) - 1 # 新しいメッセージのインデックス

                # 出力検証
                expected_keywords = ["infographic", "step-by-step", "ingredient", "layout", "minimal style"]
                lower_response = full_response.lower()
                is_valid_format_check = any(keyword in lower_response for keyword in expected_keywords)
                is_refusal_check = "please provide a valid food dish name or recipe for infographic prompt generation" in lower_response

                if not is_valid_format_check and not is_refusal_check:
                    st.warning("The generated response might not contain expected keywords...", icon="⚠️")
                elif is_refusal_check:
                     st.info("Input was determined to be invalid or unrelated...")

                # 画像生成ボタンと表示エリア (新しいメッセージに対して)
                # 条件: 画像クライアントがあり、拒否応答でない場合
                if image_client and not is_refusal_check:
                    button_key = f"gen_img_{new_message_idx}"
                    if st.button("Generate Image ✨", key=button_key):
                        image_bytes = generate_image_from_prompt(image_client, full_response)
                        if image_bytes:
                            st.session_state.generated_images[new_message_idx] = image_bytes
                        # 再実行ループで画像表示

                    # 対応する画像データがあれば表示
                    if new_message_idx in st.session_state.generated_images:
                         img_bytes = st.session_state.generated_images[new_message_idx]
                         st.image(img_bytes, caption=f"Generated Image for Prompt #{new_message_idx+1}")
                         st.download_button(
                             label="Download Image 💾",
                             data=img_bytes,
                             file_name=f"recipe_infographic_{new_message_idx+1}.png",
                             mime="image/png",
                             key=f"dl_img_{new_message_idx}"
                         )

        except Exception as e:
            st.error(f"Error generating response: {str(e)}", icon="🚨")
