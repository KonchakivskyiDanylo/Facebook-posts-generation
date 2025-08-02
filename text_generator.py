# text_generator.py

import os
import sys
import requests # For local LLM API calls
import json # For local LLM API calls

# Conditional imports for Google Gemini and OpenAI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("WARNING: google-generativeai not found. Gemini features will be disabled.", file=sys.stderr)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("WARNING: openai library not found. OpenAI features will be disabled.", file=sys.stderr)

# --- Debugging setup ---
DEBUG_GEN_MODE = True

def debug_gen_print(message):
    if DEBUG_GEN_MODE:
        print(f"[DEBUG - Generator - Text]: {message}")

def configure_apis():
    # Configure Gemini API
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if GEMINI_AVAILABLE and gemini_api_key: # Added GEMINI_AVAILABLE check here
        genai.configure(api_key=gemini_api_key)
        debug_gen_print("Gemini API configured.")
    else:
        debug_gen_print("WARNING: GEMINI_API_KEY environment variable not set or google-generativeai not available. Gemini generation will not work.")
        debug_gen_print("WARNING: GEMINI_API_KEY environment variable not set. Gemini generation will not work.") # This line is redundant after adding the GEMINI_AVAILABLE check above.

    # Configure OpenAI API
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        # OpenAI client initialization moved to generate_text for specific model selection flexibility
        debug_gen_print("OpenAI API key detected.")
    else:
        debug_gen_print("WARNING: OPENAI_API_KEY environment variable not set. OpenAI generation will not work.")

    # Local LLM (DeepSeek/Mistral example) - No direct API key, just endpoint check
    deepseek_local_url = "http://localhost:11434/api/generate"
    try:
        # A quick check to see if the local server is running
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            debug_gen_print(f"Local LLM (Ollama) server detected at {deepseek_local_url}.")
        else:
            debug_gen_print(f"WARNING: Local LLM (Ollama) server not reachable at {deepseek_local_url} (status: {response.status_code}).")
    except requests.exceptions.RequestException as e:
        debug_gen_print(f"WARNING: Local LLM (Ollama) server not reachable at {deepseek_local_url} ({e}). DeepSeek/Mistral generation may not work.")


# Call configure_apis once when module is imported
configure_apis()

def generate_text(prompt_en, prompt_ar, target_language, provider, model, temperature=0.7, contact_info_en="", contact_info_ar=""):
    """
    Generates text content using the specified AI provider and model.

    Args:
        prompt_en (str): English prompt for content generation.
        prompt_ar (str): Arabic prompt for content generation.
        target_language (str): 'English', 'Arabic', or 'Both'.
        provider (str): 'Gemini', 'OpenAI', 'DeepSeek', or 'Mistral'.
        model (str): The specific model name.
        temperature (float): Controls the randomness of the output.
        contact_info_en (str): English contact information to include.
        contact_info_ar (str): Arabic contact information to include.

    Returns:
        tuple: (generated_content_en, generated_content_ar, actual_prompt_en_used, actual_prompt_ar_used)
                where actual_prompt_en/ar are the full prompts sent to the LLM.
    """
    debug_gen_print(f"Generating text with {provider} model {model} for language {target_language}...")

    generated_content_en = ""
    generated_content_ar = ""
    actual_prompt_en_used = ""
    actual_prompt_ar_used = ""

    # Construct prompts with contact info, guiding the LLM to integrate naturally
    full_english_post_prompt = f"{prompt_en}\n\nEnsure this post concludes with the following contact information, integrated naturally: {contact_info_en}" if contact_info_en else prompt_en
    full_arabic_post_prompt = f"{prompt_ar}\n\nتأكد من أن هذا المنشور ينتهي بمعلومات الاتصال التالية، مدمجة بشكل طبيعي: {contact_info_ar}" if contact_info_ar else prompt_ar


    if provider == "Gemini":
        if GEMINI_AVAILABLE:
            try:
                client = genai.GenerativeModel(model_name=model)
                if (target_language == "English" or target_language == "Both") and full_english_post_prompt:
                    debug_gen_print(f"Gemini (EN) prompt: {full_english_post_prompt[:100]}...")
                    response_en = client.generate_content(
                        full_english_post_prompt,
                        generation_config=genai.types.GenerationConfig(temperature=temperature)
                    )
                    generated_content_en = response_en.text.strip()
                    actual_prompt_en_used = full_english_post_prompt
                    debug_gen_print(f"Gemini (EN) generated content (first 50 chars): {generated_content_en[:50]}...")
                if (target_language == "Arabic" or target_language == "Both") and full_arabic_post_prompt:
                    debug_gen_print(f"Gemini (AR) prompt: {full_arabic_post_prompt[:100]}...")
                    response_ar = client.generate_content(
                        full_arabic_post_prompt,
                        generation_config=genai.types.GenerationConfig(temperature=temperature)
                    )
                    generated_content_ar = response_ar.text.strip()
                    actual_prompt_ar_used = full_arabic_post_prompt
                    debug_gen_print(f"Gemini (AR) generated content (first 50 chars): {generated_content_ar[:50]}...")

            except Exception as e:
                debug_gen_print(f"Error during Gemini generation: {e}")
                return f"Generation failed (Gemini API Error): {e}", "", full_english_post_prompt, full_arabic_post_prompt
        else:
            generated_content_en = "Gemini API not available."
            generated_content_ar = "Gemini API not available."

    elif provider == "OpenAI":
        if OPENAI_AVAILABLE:
            try:
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                if (target_language == "English" or target_language == "Both") and full_english_post_prompt:
                    debug_gen_print(f"OpenAI (EN) prompt: {full_english_post_prompt[:100]}...")
                    response_en = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": full_english_post_prompt}],
                        temperature=temperature
                    )
                    generated_content_en = response_en.choices[0].message.content.strip()
                    actual_prompt_en_used = full_english_post_prompt
                    debug_gen_print(f"OpenAI (EN) generated content (first 50 chars): {generated_content_en[:50]}...")
                if (target_language == "Arabic" or target_language == "Both") and full_arabic_post_prompt:
                    debug_gen_print(f"OpenAI (AR) prompt: {full_arabic_post_prompt[:100]}...")
                    response_ar = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": full_arabic_post_prompt}],
                        temperature=temperature
                    )
                    generated_content_ar = response_ar.choices[0].message.content.strip()
                    actual_prompt_ar_used = full_arabic_post_prompt
                    debug_gen_print(f"OpenAI (AR) generated content (first 50 chars): {generated_content_ar[:50]}...")

            except Exception as e:
                debug_gen_print(f"Error during OpenAI generation: {e}")
                return f"Generation failed (OpenAI API Error): {e}", "", full_english_post_prompt, full_arabic_post_prompt
        else:
            generated_content_en = "OpenAI API not available."
            generated_content_ar = "OpenAI API not available."

    elif provider == "DeepSeek" or provider == "Mistral": # Group DeepSeek and Mistral as local LLMs
        local_llm_url = "http://localhost:11434/api/generate" # Assuming Ollama default
        local_llm_model = model # model parameter holds the ollama model tag
        headers = {'Content-Type': 'application/json'}

        # Increased timeout to 240000 seconds (4000 minutes or ~66 hours) as requested
        # Be aware this is an extremely long timeout.
        TIMEOUT_SECONDS = 240000

        # Common options for DeepSeek/Mistral models
        common_ollama_options = {
            "temperature": temperature,
            "num_predict": 1000, # Max tokens to predict
            "stop": ["</think>", "</s>"] # Add </s> as a common stop token for Mistral/Llama models
        }


        if (target_language == "English" or target_language == "Both") and full_english_post_prompt:
            payload_en = {
                "model": local_llm_model,
                "prompt": full_english_post_prompt,
                "stream": False,
                "options": common_ollama_options # Apply common options
            }
            try:
                debug_gen_print(f"{provider} (EN) API Payload SENT: {json.dumps(payload_en)}") # ADDED DEBUG PRINT
                debug_gen_print(f"{provider} (EN) prompt: {full_english_post_prompt[:100]}...")
                response_en = requests.post(local_llm_url, headers=headers, data=json.dumps(payload_en), timeout=TIMEOUT_SECONDS)
                response_en.raise_for_status()
                generated_content_en = response_en.json()['response'].strip()
                # Clean up any residual <think> tags if they were generated before stop took effect
                generated_content_en = generated_content_en.split('<think>')[0].strip() if '<think>' in generated_content_en else generated_content_en
                generated_content_en = generated_content_en.split('</think>')[0].strip() if '</think>' in generated_content_en else generated_content_en
                # Also strip </s> if present
                generated_content_en = generated_content_en.split('</s>')[0].strip() if '</s>' in generated_content_en else generated_content_en


                actual_prompt_en_used = full_english_post_prompt
                debug_gen_print(f"{provider} (EN) generated content (first 50 chars): {generated_content_en[:50]}...")
            except Exception as e:
                debug_gen_print(f"Error during {provider} (EN) generation: {e}")
                generated_content_en = f"Generation failed ({provider} EN API Error): {e}"

        if (target_language == "Arabic" or target_language == "Both") and full_arabic_post_prompt:
            payload_ar = {
                "model": local_llm_model,
                "prompt": full_arabic_post_prompt,
                "stream": False,
                "options": common_ollama_options # Apply common options
            }
            try:
                debug_gen_print(f"{provider} (AR) API Payload SENT: {json.dumps(payload_ar)}") # ADDED DEBUG PRINT
                debug_gen_print(f"{provider} (AR) prompt: {full_arabic_post_prompt[:100]}...")
                response_ar = requests.post(local_llm_url, headers=headers, data=json.dumps(payload_ar), timeout=TIMEOUT_SECONDS)
                response_ar.raise_for_status()
                generated_content_ar = response_ar.json()['response'].strip()
                # Clean up any residual <think> tags if they were generated before stop took effect
                generated_content_ar = generated_content_ar.split('<think>')[0].strip() if '<think>' in generated_content_ar else generated_content_ar
                generated_content_ar = generated_content_ar.split('</think>')[0].strip() if '</think>' in generated_content_ar else generated_content_ar
                # Also strip </s> if present
                generated_content_ar = generated_content_ar.split('</s>')[0].strip() if '</s>' in generated_content_ar else generated_content_ar


                actual_prompt_ar_used = full_arabic_post_prompt
                debug_gen_print(f"{provider} (AR) generated content (first 50 chars): {generated_content_ar[:50]}...")
            except Exception as e:
                debug_gen_print(f"Error during {provider} (AR) generation: {e}")
                generated_content_ar = f"Generation failed ({provider} AR API Error): {e}"

    else:
        debug_gen_print(f"Unknown text generation provider: {provider}")
        return "ERROR: Unknown text provider", "", "", ""

    return generated_content_en, generated_content_ar, actual_prompt_en_used, actual_prompt_ar_used

if __name__ == '__main__':
    import sys
    # Simple test for text_generator.py (run with 'python text_generator.py test')
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("\n--- Testing Gemini ---")
        # Ensure GEMINI_API_KEY is set in your environment for this test to work
        content_en, content_ar, prompt_en, prompt_ar = generate_text("a short fact about space", "", "English", "Gemini", "gemini-1.5-flash", 0.7)
        print(f"Gemini EN: {content_en}\nPrompt: {prompt_en}\n")

        print("\n--- Testing OpenAI ---")
        # Ensure OPENAI_API_KEY is set in your environment for this test to work
        # os.environ['OPENAI_API_KEY'] = 'YOUR_TEST_OPENAI_KEY' # Uncomment and replace for actual test
        content_en, content_ar, prompt_en, prompt_ar = generate_text("a short motivational quote", "", "English", "OpenAI", "gpt-3.5-turbo", 0.7)
        print(f"OpenAI EN: {content_en}\nPrompt: {prompt_en}\n")

        print("\n--- Testing DeepSeek (requires local Ollama server with deepseek-coder or deepseek-r1 pulled) ---")
        # To run DeepSeek locally, in your terminal:
        # 1. Install Ollama: https://ollama.com/download
        # 2. Pull the model: ollama pull deepseek-coder:latest (or deepseek-r1:latest if preferred)
        # 3. Ensure Ollama is running (it usually runs in the background automatically)
        content_en, content_ar, prompt_en, prompt_ar = generate_text("Write a very short, positive Facebook post for a business.", "", "English", "DeepSeek", "deepseek-coder", 0.7)
        print(f"DeepSeek EN: {content_en}\nPrompt: {prompt_en}\n")

        content_en, content_ar, prompt_en, prompt_ar = generate_text("", "اكتب منشورًا قصيرًا وإيجابيًا على فيسبوك لشركة.", "Arabic", "DeepSeek", "deepseek-coder", 0.7)
        print(f"DeepSeek AR: {content_ar}\nPrompt: {prompt_ar}\n")

        print("\n--- Testing Mistral (requires local Ollama server with mistral pulled) ---")
        # 1. Install Ollama: https://ollama.com/download
        # 2. Pull the model: ollama pull mistral
        # 3. Ensure Ollama is running
        content_en, content_ar, prompt_en, prompt_ar = generate_text("Write a very short, factual statement about AI.", "", "English", "Mistral", "mistral", 0.7)
        print(f"Mistral EN: {content_en}\nPrompt: {prompt_en}\n")

        # del os.environ['OPENAI_API_KEY'] # Clean up if you set it for testing