# utils.py
import streamlit as st
import base64
import config

# for prompt injection detection
def contains_injection_keywords(text):
    keywords = ["ignore previous", "ignore instructions", "disregard", "forget your instructions", "act as", "you must", "system prompt:"]
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in keywords)


# --- 画像生成関数 ---
@st.cache_data(show_spinner="Generating image...") # 結果をキャッシュ & スピナー表示
def generate_image_from_prompt(_together_client, prompt_text):
    """Generates an image using Together AI and returns image bytes."""
    try:
        response = _together_client.images.generate(
            prompt=prompt_text,
            model=config.IMAGE_MODEL,
            width=config.IMAGE_WIDTH, 
            height=config.IMAGE_HEIGHT,
            steps=config.IMAGE_STEPS,    
            n=1,
            response_format=config.IMAGE_RESPONSE_FORMAT,
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
