IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell-Free"  # model from together ai
BASE_URL = "http://localhost:8000/v1"


MODELS = {
    "llama3.1-8b": {"name": "Llama3.1-8b", "tokens": 8192, "developer": "Meta"},
    "llama-3.3-70b": {"name": "Llama-3.3-70b", "tokens": 8192, "developer": "Meta"},
    "llama-4-scout-17b-16e-instruct": {"name": "Llama4 Scout", "tokens": 8192, "developer": "Meta"},
    "qwen-3-32b":{"name": "Qwen 3 32B", "tokens": 8192, "developer": "Qwen"},
}


# config for image generation
IMAGE_WIDTH = 768
IMAGE_HEIGHT = 1024
IMAGE_STEPS = 4
IMAGE_N = 1
IMAGE_RESPONSE_FORMAT = "b64_json"
