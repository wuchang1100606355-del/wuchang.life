#!/usr/bin/env python3
import sys, json, os
from google.cloud import aiplatform
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel, GenerationConfig

PROJECT_ID = "my-j-483304"
LOCATION = "us-central1"
KEY_PATH = "secrets/gcp-sa-key.json"
PROFILE_PATH = "config/openwebui_model_profile.json"

def main():
    if not os.path.exists(KEY_PATH):
        print('{"patch_type": "ERROR", "file_ref": "", "content_delta": "HOLD_GATEWAY_MISSING_KEY"}')
        sys.exit(1)
    try:
        request_data = json.loads(sys.stdin.read().strip())
    except Exception:
        print('{"patch_type": "ERROR", "file_ref": "", "content_delta": "HOLD_GATEWAY_INVALID_JSON"}')
        sys.exit(1)
    task_intent = request_data.get("task_intent", "")
    if not task_intent:
        print('{"patch_type": "ERROR", "file_ref": "", "content_delta": "HOLD_GATEWAY_EMPTY_INTENT"}')
        sys.exit(1)
    try:
        with open(PROFILE_PATH, 'r') as f:
            system_instruction = json.load(f)["params"]["system"]
    except Exception:
        system_instruction = "You are a strict JSON patch generator. Output only JSON."

    credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
    aiplatform.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
    
    model = GenerativeModel("gemini-1.5-pro-001", system_instruction=[system_instruction])
    prompt = f"[8D_GENERATIVE_TRANSFER_REQUEST]\nTASK INTENT: {task_intent}\nFILES PROVIDED: {request_data.get('manifest_index_refs', [])}\nProvide the exact JSON Delta output:"

    try:
        resp = model.generate_content(
            prompt, 
            generation_config=GenerationConfig(temperature=0.0, response_mime_type="application/json")
        )
        raw = resp.text.strip()
        if raw.startswith("```json"): raw = raw[7:]
        if raw.endswith("```"): raw = raw[:-3]
        print(raw.strip())
    except Exception as e:
        print('{"patch_type": "ERROR", "file_ref": "", "content_delta": "GATEWAY_API_FAILURE"}')
        sys.exit(1)

if __name__ == "__main__":
    main()
