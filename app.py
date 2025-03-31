import asyncio
import perplexity_async
import time
from flask import Flask, request, jsonify, Response
import json
import os
from flask_cors import CORS
import argparse
import ast
import base64
import re
from functools import wraps

PERPLEXITY_MODES_MODELS = {
    'pro': ['', 'sonar', 'gpt-4.5', 'gpt-4o', 'claude 3.7 sonnet', 'gemini 2.0 flash', 'grok-2'],
    'reasoning': ['', 'r1', 'o3-mini', 'claude 3.7 sonnet'],
    'auto': [''],
    'deep research': ['']
}

ALL_MODELS_WITH_PREFIX = []
MODEL_ID_TO_API_PARAMS_MAP = {}
DEFAULT_MODEL_ID = None
DEFAULT_PREFIX = "perplexity-chat/"
DEFAULT_MODE_FOR_FALLBACK = None
DEFAULT_MODEL_FOR_FALLBACK = None

EXPECTED_API_KEY = os.environ.get("PPLX_OPENAI_KEY", "your-secret-api-key")

app = Flask(__name__)
CORS(app)

def require_api_key(f):
    """Decorator to ensure an API key is present and valid."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            api_key = auth_header.split('Bearer ')[1]

        if not api_key or api_key != EXPECTED_API_KEY:
            return jsonify({
                "error": {
                    "message": "Invalid or missing API key.",
                    "type": "authentication_error",
                    "code": 401
                }
            }), 401
        return f(*args, **kwargs)
    return decorated_function


async def get_perplexity_response(prompt, model_id_with_prefix=DEFAULT_MODEL_ID, files_dict=None):
    """
    Sends a request to the Perplexity API and returns an OpenAI-compatible response.

    Args:
        prompt: The user's prompt string.
        model_id_with_prefix: The model ID string (e.g., 'perplexity-chat/pro-default').
        files_dict: An optional dictionary of filenames to file content (bytes or str).

    Returns:
        A dictionary representing the OpenAI-compatible chat completion response,
        or a tuple (dict, status_code) in case of an error.
    """
    mode_for_api, model_for_api = MODEL_ID_TO_API_PARAMS_MAP.get(
        model_id_with_prefix,
        (DEFAULT_MODE_FOR_FALLBACK, DEFAULT_MODEL_FOR_FALLBACK)
    )

    try:

        print("-" * 20)
        print(f"Calling get_perplexity_response with:")
        print(f"  Prompt: {prompt[:100]}...")
        print(f"  Model ID: {model_id_with_prefix}")
        print(f"  Mode for API: {mode_for_api}")
        print(f"  Model for API: {model_for_api}")
        if files_dict:
            print(f"  Files Dict ({len(files_dict)} files):")
            for filename, filedata in files_dict.items():

                print(f"    - {filename}: type={type(filedata)}, size={len(filedata) if isinstance(filedata, bytes) else 'N/A'}")
        else:
            print("  Files Dict: None")
        print("-" * 20)

        perplexity_cli = await perplexity_async.Client(perplexity_cookies if perplexity_cookies else None)
        resp = await perplexity_cli.search(
            prompt,
            mode=mode_for_api,
            model=model_for_api,
            sources=[],
            files=files_dict if files_dict else {},
            stream=False,
            language='en-US',
            follow_up=None,
            incognito=False
        )

        if resp and resp.get('text') and isinstance(resp['text'], list) and len(resp['text']) > 0:
            final_step = resp['text'][-1]
            if final_step.get('step_type') == 'FINAL' and final_step.get('content'):
                answer_content_raw = final_step['content'].get('answer')

                plain_text_answer = "no response."
                if answer_content_raw:
                    try:
                        parsed_answer = json.loads(answer_content_raw)
                        if isinstance(parsed_answer, dict) and 'answer' in parsed_answer:
                            plain_text_answer = parsed_answer['answer']
                        else:
                            plain_text_answer = str(answer_content_raw)
                    except json.JSONDecodeError:
                        plain_text_answer = str(answer_content_raw)

                openai_compatible_response = {
                    "id": resp.get('uuid', f"pplx-{int(time.time())}"),
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model_id_with_prefix,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": plain_text_answer
                            },
                            "finish_reason": "stop" if resp.get('status') == 'completed' else "length"
                        }
                    ],
                    "usage": { "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 }
                }
                return openai_compatible_response
            else:

                full_text_raw = " ".join([step.get('content', {}).get('answer', '')
                                          for step in resp.get('text', [])
                                          if step.get('content', {}).get('answer')])
                plain_text_fallback = "Could not extract the answer."
                if full_text_raw:
                     try:
                         parsed_fallback = json.loads(full_text_raw)
                         if isinstance(parsed_fallback, dict) and 'answer' in parsed_fallback:
                              plain_text_fallback = parsed_fallback['answer']
                         else:
                              plain_text_fallback = str(full_text_raw)
                     except json.JSONDecodeError:
                          plain_text_fallback = str(full_text_raw)

                if plain_text_fallback != "Could not extract the answer.":
                     openai_compatible_response = {
                        "id": resp.get('uuid', f"pplx-fallback-{int(time.time())}"),
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model_id_with_prefix + "-fallback",
                        "choices": [
                            {
                                "index": 0,
                                "message": { "role": "assistant", "content": plain_text_fallback },
                                "finish_reason": "stop" if resp.get('status') == 'completed' else "length"
                            }
                        ],
                        "usage": { "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 }
                    }
                     return openai_compatible_response
                else:
                    error_msg = "Error: Final step or content not found in Perplexity response (Fallback)."
                    print(error_msg)
                    return {"error": {"message": error_msg, "type": "api_error", "code": 500}}, 500
        else:
             error_msg = "Error: Invalid or empty response from Perplexity API."
             print(error_msg)
             return {"error": {"message": error_msg, "type": "api_error", "code": 502}}, 502

    except perplexity_async.PerplexityError as e:
        error_msg = f"Perplexity API Error: {e}"
        print(error_msg)
        return {"error": {"message": error_msg, "type": "perplexity_api_error", "code": 503}}, 503
    except json.JSONDecodeError as e:

         raw_resp_info = "N/A"
         try:
              raw_resp_info = str(resp)
         except NameError:
              pass
         error_msg = f"Failed to decode JSON response from Perplexity API: {e}. Raw Response: {raw_resp_info}"
         print(error_msg)
         return {"error": {"message": "Received invalid JSON from Perplexity API.", "type": "perplexity_api_error", "code": 502}}, 502
    except Exception as e:
        error_msg = f"Internal Server Error during Perplexity request: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {"error": {"message": error_msg, "type": "internal_server_error", "code": 500}}, 500


@app.route('/v1/models', methods=['GET'])
@require_api_key
def list_models():
    """Returns a list of available models in OpenAI format."""
    models_data = []
    created_time = int(time.time())
    for model_id in ALL_MODELS_WITH_PREFIX:
        models_data.append({
            "id": model_id,
            "object": "model",
            "created": created_time,
            "owned_by": "openai"
        })

    return jsonify({"object": "list", "data": models_data})


@app.route('/v1/chat/completions', methods=['POST'])
@require_api_key
def chat_completions():
    """
    Endpoint compatible with OpenAI Chat Completion API.

    Supports file uploads via multipart/form-data or image URLs in messages.
    """
    try:
        prompt_text = ""
        files_to_pass = {}
        data = None

        content_type = request.content_type
        is_multipart = 'multipart/form-data' in content_type

        if is_multipart:
            json_payload_str = request.form.get('json_payload')
            if not json_payload_str:
                return jsonify({
                    "error": ("Missing 'json_payload' field in "
                              "multipart/form-data request")
                }), 400
            try:
                data = json.loads(json_payload_str)
            except json.JSONDecodeError:
                return jsonify({
                    "error": "Invalid JSON in 'json_payload' field"
                }), 400


            if request.files:
                for field_name, file_storage in request.files.items():
                    if file_storage and file_storage.filename:
                        filename = file_storage.filename
                        mimetype = file_storage.mimetype
                        print(f"Processing uploaded file: {filename}, mimetype: {mimetype}")

                        text_extensions = ('.txt', '.md', '.py', '.json', '.csv',
                                           '.html', '.css', '.js', '.xml', '.log',
                                           '.srt')
                        is_text_file = (
                            filename.lower().endswith(text_extensions) or
                            (mimetype and mimetype.startswith('text/'))
                        )

                        try:
                            if is_text_file:
                                file_content = file_storage.stream.read().decode('utf-8', errors='replace')
                                files_to_pass[filename] = file_content
                                print(f"  Read {filename} as text (str), size: {len(file_content)}")
                            else:
                                file_content = file_storage.read()
                                files_to_pass[filename] = file_content
                                print(f"  Read {filename} as bytes, size: {len(file_content)}")
                        except Exception as read_err:
                             print(f"Error reading file {filename}: {read_err}")
                             continue
                    else:
                         print(f"Warning: Received empty file field '{field_name}'")
            if not files_to_pass:
                files_to_pass = None

        else:
            try:
                 data = request.get_json()

                 if not data:
                     raise ValueError("Empty JSON data")
            except Exception as json_err:
                 raw_body = request.get_data(as_text=True)
                 print(f"Failed to parse JSON. Raw body: {raw_body}")
                 return jsonify({"error": f"Invalid JSON request. Error: {json_err}. Raw Body: {raw_body[:500]}..."}), 400


        if not data or 'messages' not in data:
             print("Error: Missing 'messages' in payload.")
             return jsonify({"error": "Missing 'messages' field in the request payload"}), 400

        image_count = 0
        all_text_parts = []
        for msg in data['messages']:
            content = msg.get('content')
            if isinstance(content, str):
                all_text_parts.append(content)
            elif isinstance(content, list):
                 for part in content:
                     if part.get('type') == 'text':
                         all_text_parts.append(part.get('text', ''))
                     elif not is_multipart and part.get('type') == 'image_url':
                         image_url_data = part.get('image_url', {}).get('url')
                         if image_url_data and image_url_data.startswith('data:image'):
                              try:
                                  header, encoded_data = image_url_data.split(',', 1)
                                  mime_match = re.search(r'data:(image/[a-zA-Z+]+);base64', header)
                                  mime_type = mime_match.group(1) if mime_match else 'image/png'
                                  extension = mime_type.split('/')[-1]
                                  decoded_bytes = base64.b64decode(encoded_data)
                                  image_count += 1
                                  filename = f"image_{image_count}.{extension}"
                                  if files_to_pass is None: files_to_pass = {}
                                  files_to_pass[filename] = decoded_bytes
                                  print(f"Decoded and added image from data URL: "
                                        f"{filename}, size: {len(decoded_bytes)}")
                              except Exception as e:
                                  print(f"Error decoding base64 image URL: {e}")

        prompt_text = "\n".join(all_text_parts).strip()


        print(f"Extracted prompt_text to send to Perplexity: '{prompt_text}'")
        if not files_to_pass:
            print("No files extracted from this request to pass directly.")
        else:
            print(f"Files extracted to pass: {list(files_to_pass.keys())}")
        print("-" * 20)


        if not prompt_text:
             if files_to_pass:
                  prompt_text = "Describe the attached file(s)."
             else:
                  prompt_text = "Hello."
             print(f"Prompt text was empty, using default: '{prompt_text}'")

        model_id_with_prefix = data.get("model", DEFAULT_MODEL_ID)

        response_data = asyncio.run(get_perplexity_response(prompt_text, model_id_with_prefix, files_dict=files_to_pass))

        if isinstance(response_data, tuple):
             return jsonify(response_data[0]), response_data[1]
        else:
             if isinstance(response_data, dict) and "model" not in response_data:
                 response_data["model"] = model_id_with_prefix
             return jsonify(response_data)

    except Exception as e:
        print(f"Error in /v1/chat/completions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": {"message": "Internal Server Error",
                      "type": "internal_server_error"}
        }), 500

def parse_cookies_from_file(filepath):
    """Reads a file and extracts the cookies dictionary."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        start_index = content.find('cookies = {')
        if start_index == -1:
            print(f"Error: Could not find 'cookies = {{' string in file "
                  f"{filepath}")
            return None

        dict_str = content[start_index + len('cookies = '):]

        cookies_dict = ast.literal_eval(dict_str)
        if isinstance(cookies_dict, dict):
            return cookies_dict
        else:
            print(f"Error: Failed to parse dictionary from file {filepath}")
            return None
    except FileNotFoundError:
        print(f"Error: Cookie file not found at {filepath}")
        return None
    except Exception as e:
        print(f"Error reading or parsing cookie file {filepath}: {e}")
        return None

def setup_models(prefix):
    """Generates lists of models and API parameters based on the given prefix."""
    global ALL_MODELS_WITH_PREFIX, MODEL_ID_TO_API_PARAMS_MAP, DEFAULT_MODEL_ID
    global DEFAULT_PREFIX, DEFAULT_MODE_FOR_FALLBACK, DEFAULT_MODEL_FOR_FALLBACK

    ALL_MODELS_WITH_PREFIX.clear()
    MODEL_ID_TO_API_PARAMS_MAP.clear()
    DEFAULT_PREFIX = prefix

    for mode, model_list in PERPLEXITY_MODES_MODELS.items():
        mode_sanitized = mode.replace(" ", "-")
        for model_name in model_list:
            final_id = ""
            api_model_param = None

            if model_name is None:
                if mode in ['auto', 'deep research']:
                    final_id = f"{DEFAULT_PREFIX}/{mode_sanitized}"
                else:
                    final_id = f"{DEFAULT_PREFIX}/{mode_sanitized}-default"
                api_model_param = None
            else:
                model_name_sanitized = model_name.replace(" ", "-")
                final_id = f"{DEFAULT_PREFIX}/{mode_sanitized}-{model_name_sanitized}"
                api_model_param = model_name

            if final_id:
                ALL_MODELS_WITH_PREFIX.append(final_id)
                MODEL_ID_TO_API_PARAMS_MAP[final_id] = (mode, api_model_param)

    DEFAULT_MODEL_ID = f"{DEFAULT_PREFIX}/auto"
    if DEFAULT_MODEL_ID not in MODEL_ID_TO_API_PARAMS_MAP:
        DEFAULT_MODEL_ID = next((k for k in MODEL_ID_TO_API_PARAMS_MAP if k.startswith(f"{DEFAULT_PREFIX}/pro-")),
                                ALL_MODELS_WITH_PREFIX[0] if ALL_MODELS_WITH_PREFIX else None)

    if DEFAULT_MODEL_ID:
        DEFAULT_MODE_FOR_FALLBACK, DEFAULT_MODEL_FOR_FALLBACK = MODEL_ID_TO_API_PARAMS_MAP.get(DEFAULT_MODEL_ID, ('auto', None))
    else:
        DEFAULT_MODE_FOR_FALLBACK, DEFAULT_MODEL_FOR_FALLBACK = ('auto', None)
        print("Warning: No models could be generated. Check PERPLEXITY_MODES_MODELS.")

    print(f"Models setup complete. Default prefix: '{DEFAULT_PREFIX}'. Default model ID: '{DEFAULT_MODEL_ID}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Perplexity API server.")

    parser.add_argument(
        '--sources',
        nargs='*',
        choices=['web', 'scholar', 'social'],
        default=[],
        help="Sources for search (specify multiple: web, scholar, social)."
    )

    parser.add_argument(
        '--prefix',
        type=str,
        help="Prefix for API model IDs (e.g., 'pplx')."
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5010,
        help="Port to run the server on."
    )

    parser.add_argument(
        '--language',
        type=str,
        default='en-US',
        help="Language for Perplexity API."
    )

    parser.add_argument(
        '--incognito',
        action='store_true',
        default=False,
        help="Enable incognito mode."
    )

    parser.add_argument(
        '--api-key',
        type=str,
        default="your-secret-api-key",
        help="Perplexity API key (overrides PPLX_OPENAI_KEY environment variable)."
    )

    parser.add_argument(
        '--cookies-file',
        type=str,
        default='cookies.txt',
        help=("Path to the file containing cookies "
              "(format 'cookies = {...}'). Defaults to 'cookies.txt'.")
    )

    args = parser.parse_args()

    effective_prefix = args.prefix if args.prefix else "perplexity-chat"

    setup_models(effective_prefix)

    print("\n--- Startup Parameters ---")
    print(f"Port: {args.port}")
    print(f"API Prefix: {DEFAULT_PREFIX}")
    print(f"Sources: {args.sources}")
    print(f"Language: {args.language}")
    print(f"Incognito Mode: {args.incognito}")
    api_key_status = ('Yes' if EXPECTED_API_KEY != 'your-secret-api-key'
                      else 'No (default placeholder)')
    print(f"API Key Used: {api_key_status}")
    print(f"Cookie File Path: {args.cookies_file}")
    if DEFAULT_MODE_FOR_FALLBACK != 'auto':
        print(f"Loaded {len(MODEL_ID_TO_API_PARAMS_MAP) - 1} cookies.")
    else:
        print("Cookies not loaded from file.")
    print("--------------------------\n")

    EXPECTED_API_KEY = args.api_key or os.environ.get("PPLX_OPENAI_KEY", "your-secret-api-key")
    if EXPECTED_API_KEY == "your-secret-api-key" and not args.api_key:
        print("Warning: PPLX_OPENAI_KEY is not set in environment and "
              "--api-key was not provided. Using default placeholder key.")

    perplexity_cookies = None
    print(f"Attempting to load cookies from: {args.cookies_file}")
    perplexity_cookies = parse_cookies_from_file(args.cookies_file)

    if perplexity_cookies:
         print("Cookies loaded successfully.")
    else:
         if args.cookies_file == 'cookies.txt':
             print(f"Could not load cookies from the default file "
                   f"'{args.cookies_file}'.")
             print("Ensure the file exists in the same directory as the script "
                   "and has the correct format ('cookies = {...}').")
             print("Or specify a different path using --cookies-file.")
         else:

             print(f"Could not load cookies from the specified file "
                   f"'{args.cookies_file}'.")
         print("Running without cookies loaded from file.")

    app.run(host='0.0.0.0', port=args.port, debug=False)
