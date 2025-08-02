# image_generator.py

import os
import sys
import requests
import json # For debugging error responses
from openai import OpenAI
from datetime import datetime

# --- Debugging setup ---
DEBUG_IMG_GEN_MODE = True

def debug_img_gen_print(message):
    if DEBUG_IMG_GEN_MODE:
        print(f"[DEBUG - Generator - Image]: {message}")

def generate_image(prompt, output_dir, provider, model):
    """
    Generates an image using the specified AI provider and model.

    Args:
        prompt (str): The text prompt for image generation.
        output_dir (str): Base directory to save the generated image.
                          The image will be saved in a 'generated_images' subdirectory.
        provider (str): 'OpenAI (DALL-E)' or 'Google (Imagen)'.
        model (str): The specific model name (e.g., 'dall-e-3').

    Returns:
        str: The filename (e.g., "image_timestamp.png") of the saved image file,
             or None if generation failed.
    """
    debug_img_gen_print(f"Generating image with {provider} model {model}...")

    # Images should be saved in a 'generated_images' subdirectory
    image_save_dir = os.path.join(output_dir, "generated_images")
    os.makedirs(image_save_dir, exist_ok=True)

    filename = f"image_{int(datetime.now().timestamp())}.png"
    filepath = os.path.join(image_save_dir, filename) # Use image_save_dir for filepath

    if provider == "OpenAI (DALL-E)":
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            debug_img_gen_print("ERROR: OPENAI_API_KEY environment variable not set for DALL-E.")
            return None
        
        try:
            client = OpenAI(api_key=openai_api_key)
            
            response = client.images.generate(
                model=model,
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            debug_img_gen_print(f"DALL-E image URL: {image_url}")

            # Download the image
            img_data_response = requests.get(image_url)
            img_data_response.raise_for_status() # Raise an exception for bad status codes
            
            with open(filepath, 'wb') as handler:
                handler.write(img_data_response.content)
            debug_img_gen_print(f"DALL-E image saved to {filepath}")
            return filename # Return filename only, as expected by caller

        except requests.exceptions.RequestException as e:
            error_details = "N/A"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                except json.JSONDecodeError:
                    error_details = e.response.text
            debug_img_gen_print(f"Error during DALL-E image generation (Request Error): {e}. Details: {error_details}")
            return None
        except Exception as e:
            debug_img_gen_print(f"Error during DALL-E image generation (General Error): {e}")
            return None

    elif provider == "Google (Imagen)":
        debug_img_gen_print("Google Imagen integration is a placeholder and requires full GCP setup.")
        # Full Imagen integration would go here. For now, it will always return None.
        return None 

    else:
        debug_img_gen_print(f"Unknown image generation provider: {provider}")
        return None

if __name__ == '__main__':
    import sys
    # Simple test for image_generator.py (run with 'python image_generator.py test')
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("\n--- Testing DALL-E (requires OPENAI_API_KEY env var) ---")
        # Set a dummy API key for testing purposes (replace with a real one for actual generation)
        os.environ['OPENAI_API_KEY'] = 'YOUR_TEST_OPENAI_KEY' 
        
        test_output_dir = "test_generated_images"
        os.makedirs(test_output_dir, exist_ok=True)
        
        test_prompt = "A majestic lion standing on a rock in the savanna at sunrise, cinematic, highly detailed"
        image_filename = generate_image(test_prompt, test_output_dir, "OpenAI (DALL-E)", "dall-e-3")
        if image_filename:
            print(f"Successfully generated image: {os.path.join(test_output_dir, 'generated_images', image_filename)}")
        else:
            print("Failed to generate image via DALL-E. Check API key and console for errors.")

        print("\n--- Testing Google (Imagen) Placeholder ---")
        image_filename_imagen = generate_image("A cute robot playing chess", test_output_dir, "Google (Imagen)", "imagen-005")
        if image_filename_imagen:
            print(f"Successfully generated Imagen image: {os.path.join(test_output_dir, 'generated_images', image_filename_imagen)}")
        else:
            print("Failed to generate image via Imagen placeholder. This functionality is not fully implemented here.")
        
        # Clean up dummy API key if set for testing
        del os.environ['OPENAI_API_KEY']