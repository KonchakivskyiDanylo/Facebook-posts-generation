# routes/topic_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os
import json
import threading
import sys
import re

# Import FACEBOOK_PAGES and ConfigLoader from the routes package's __init__
from .config_loader import ConfigLoader, FACEBOOK_PAGES

# Import text_generator for prompt generation
import text_generator

# Assume google.generativeai and os.getenv are available for checking API key status
try:
    import google.generativeai as genai

    GEMINI_AVAILABLE_FOR_GUI = True
except ImportError:
    GEMINI_AVAILABLE_FOR_GUI = False

topic_routes = Blueprint('topic_routes', __name__)

# Temporary log for displaying generation output in the template
manage_topics_log = []


def _log_to_manage_topics_log(message):
    manage_topics_log.append(message)
    # Keep the log from growing indefinitely
    if len(manage_topics_log) > 100:
        del manage_topics_log[0]


@topic_routes.route('/manage_topics', methods=['GET', 'POST'])
def manage_topics_page():
    page_names = [page["page_name"] for page in FACEBOOK_PAGES]
    selected_page = None
    selected_topic = None
    gemini_api_key_set = False  # Default to False

    if GEMINI_AVAILABLE_FOR_GUI and os.getenv("GEMINI_API_KEY"):
        gemini_api_key_set = True

    # Determine selected page for GET and initial load
    selected_page_name = request.args.get('selected_page')
    if not selected_page_name and FACEBOOK_PAGES:
        selected_page_name = FACEBOOK_PAGES[0]["page_name"]

    if selected_page_name:
        selected_page = next((p for p in FACEBOOK_PAGES if p["page_name"] == selected_page_name), None)

    # Get the current Flask app instance to pass to threads
    app_for_thread = current_app._get_current_object()

    if request.method == 'POST':
        action = request.form.get('action')
        original_selected_page_name = request.form.get('selected_page_name')

        if not selected_page and original_selected_page_name:
            selected_page = next((p for p in FACEBOOK_PAGES if p["page_name"] == original_selected_page_name), None)
            if not selected_page:
                flash(f"Error: Page '{original_selected_page_name}' not found.", "danger")
                return redirect(url_for('topic_routes.manage_topics_page'))
            selected_page_name = original_selected_page_name

        if not selected_page:
            flash("Please select a Facebook page first.", "danger")
            return redirect(url_for('topic_routes.manage_topics_page'))

        page_topics = selected_page.setdefault("topics", [])

        if action == 'add_topic':
            new_topic_name = request.form.get('new_topic_name', '').strip()
            if not new_topic_name:
                flash("Topic name cannot be empty.", "danger")
            elif any(t["name"].lower() == new_topic_name.lower() for t in page_topics):
                flash(f"Topic '{new_topic_name}' already exists for this page.", "warning")
            else:
                new_topic_data = {
                    "name": new_topic_name,
                    "english_post_prompt": "",
                    "english_image_prompt": "",
                    "arabic_post_prompt": "",
                    "arabic_image_prompt": ""
                }
                page_topics.append(new_topic_data)
                ConfigLoader.save_app_config(current_app)
                flash(f"Topic '{new_topic_name}' added.", "success")
            return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name))

        elif action == 'add_topics_from_list':
            topic_list_text = request.form.get('topic_list_text', '').strip()
            if not topic_list_text:
                flash("No topics entered in the list.", "danger")
            else:
                new_topics_raw = topic_list_text.split('\n')
                added_count = 0
                for topic_line in new_topics_raw:
                    new_topic_name = topic_line.strip()
                    if new_topic_name and not any(t["name"].lower() == new_topic_name.lower() for t in page_topics):
                        page_topics.append({
                            "name": new_topic_name,
                            "english_post_prompt": "",
                            "english_image_prompt": "",
                            "arabic_post_prompt": "",
                            "arabic_image_prompt": ""
                        })
                        added_count += 1
                if added_count > 0:
                    ConfigLoader.save_app_config(current_app)
                    flash(f"Added {added_count} new topics.", "success")
                else:
                    flash("No new topics were added (they might already exist).", "info")
            return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name))

        elif action == 'rename_topic':
            old_topic_name = request.form.get('selected_topic_name_old')
            new_topic_name = request.form.get('new_topic_name', '').strip()

            if not old_topic_name or not new_topic_name:
                flash("Old or new topic name missing for rename.", "danger")
            else:
                topic_obj = next((t for t in page_topics if t["name"] == old_topic_name), None)
                if topic_obj:
                    if new_topic_name.lower() != old_topic_name.lower() and \
                            any(t["name"].lower() == new_topic_name.lower() for t in page_topics if
                                t["name"] != old_topic_name):
                        flash(
                            f"A topic with the name '{new_topic_name}' already exists. Please choose a different name.",
                            "warning")
                    else:
                        topic_obj["name"] = new_topic_name
                        ConfigLoader.save_app_config(current_app)
                        flash(f"Topic '{old_topic_name}' renamed to '{new_topic_name}'.", "success")
                else:
                    flash(f"Topic '{old_topic_name}' not found.", "danger")
            return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name,
                                    selected_topic=new_topic_name))

        elif action == 'delete_topic':
            selected_topics_to_delete = request.form.getlist('selected_topics_to_delete')
            if not selected_topics_to_delete:
                flash("No topics selected for deletion.", "warning")
            else:
                original_count = len(page_topics)
                selected_page["topics"] = [t for t in page_topics if t["name"] not in selected_topics_to_delete]

                # Update the reference for the local page_topics variable
                page_topics = selected_page["topics"]

                deleted_count = original_count - len(page_topics)
                if deleted_count > 0:
                    ConfigLoader.save_app_config(current_app)
                    flash(f"Deleted {deleted_count} topic(s).", "success")
                else:
                    flash("No topics were deleted.", "info")
            return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name))

        elif action == 'update_topic_prompts':
            topic_name_to_update = request.form.get('topic_name_to_update')
            topic_obj = next((t for t in page_topics if t["name"] == topic_name_to_update), None)

            if topic_obj:
                topic_obj["english_post_prompt"] = request.form.get('english_post_prompt', '').strip()
                topic_obj["english_image_prompt"] = request.form.get('english_image_prompt', '').strip()
                topic_obj["arabic_post_prompt"] = request.form.get('arabic_post_prompt', '').strip()
                topic_obj["arabic_image_prompt"] = request.form.get('arabic_image_prompt', '').strip()

                ConfigLoader.save_app_config(current_app)
                flash(f"Prompts for '{topic_name_to_update}' updated and saved.", "success")
            else:
                flash(f"Topic '{topic_name_to_update}' not found for update.", "danger")
            return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name,
                                    selected_topic=topic_name_to_update))

        elif action == 'generate_prompts_gemini':
            topics_to_generate_names = request.form.getlist('selected_topics_to_generate')
            if not topics_to_generate_names:
                flash("No topics selected for Gemini prompt generation.", "warning")
                return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name))

            topics_to_process = [t for t in page_topics if t["name"] in topics_to_generate_names]

            if not topics_to_process:
                flash("Selected topics for generation were not found.", "danger")
                return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name))

            if not gemini_api_key_set:
                flash("Gemini API Key is not set. Cannot generate prompts.", "danger")
                return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name))

            manage_topics_log.clear()
            _log_to_manage_topics_log(f"Starting Gemini prompt generation for {len(topics_to_process)} topics...")

            # Run in a thread to avoid blocking the UI.
            threading.Thread(target=_run_gemini_generation_background,
                             args=(app_for_thread, topics_to_process, selected_page_name)).start()

            flash("Gemini prompt generation started in the background. Check Activity Log for progress.", "info")
            return redirect(url_for('topic_routes.manage_topics_page', selected_page=selected_page_name))

    # Re-evaluate selected_topic for GET or after POST redirect
    selected_topic_name = request.args.get('selected_topic')
    if selected_topic_name and selected_page:
        selected_topic = next((t for t in selected_page.get("topics", []) if t["name"] == selected_topic_name), None)

    return render_template('manage_topics.html',
                           page_names=page_names,
                           selected_page_name=selected_page_name,
                           topics=selected_page.get("topics", []) if selected_page else [],
                           selected_topic=selected_topic,
                           gemini_available=gemini_api_key_set,
                           manage_topics_log=manage_topics_log)


def _run_gemini_generation_background(app, topics_to_process, page_name_for_redirect):
    with app.app_context():  # Establish app context for the thread
        generated_count = 0
        total_topics = len(topics_to_process)
        errors_occurred = False

        try:
            model_name = app.config.get('DEFAULT_GEMINI_MODEL', 'gemini-1.5-flash')
            temperature = app.config.get('DEFAULT_GEMINI_TEMPERATURE', 0.7)

            if not text_generator.GEMINI_AVAILABLE or not os.getenv("GEMINI_API_KEY"):
                _log_to_manage_topics_log("ERROR: Gemini API not available or key missing in background thread.")
                flash("Gemini API not available or key missing. Cannot generate prompts.",
                      "danger")  # Flash on main context
                return

            client = genai.GenerativeModel(model_name=model_name, generation_config={"temperature": temperature})

            for i, topic_obj in enumerate(topics_to_process):
                topic_name = topic_obj["name"]
                _log_to_manage_topics_log(f"Generating prompts for '{topic_name}' ({i + 1}/{total_topics})...")

                try:
                    full_prompt_template = (
                        f"Generate three distinct pieces of content based on the topic: '{topic_name}'. "
                        f"The content should be related to automotive parts, maintenance, or fleet solutions. "
                        f"Provide them in the following structured JSON format. Ensure all strings are properly escaped. "
                        f"Return ONLY the JSON. Do not include any other text or markdown outside the JSON.\n\n"
                        f"{{\n"
                        f'  "english_image_prompt": "A detailed, descriptive image generation prompt in English for an automotive themed image related to {topic_name}. Be very specific about style, colors, and elements, e.g., '
                        f'\'realistic, close-up, high-resolution, engine bay, metallic components, blue wrench, soft studio lighting\'. Consider adding details like aspect ratio (e.g., \'aspect ratio 16:9\') or camera angles (e.g., \'cinematic shot\').",'
                        f'  "arabic_post_prompt": "اكتب منشور فيسبوك جذابًا باللغة العربية حول \'{topic_name}\'. يجب أن يتضمن المنشور وسومًا (hashtags) ذات صلة ويركز على قطع غيار السيارات أو صيانتها أو حلول الأساطيل. يجب أن يكون نصًا عربيًا فصيحًا ومباشرًا, ولا تزيد عن 200 كلمة.",'
                        f'  "arabic_image_prompt": "صورة وصفية تفصيلية باللغة العربية لإنشاء صورة ذات طابع سيارات تتعلق بـ \'{topic_name}\'. كن محددًا جدًا بشأن الأسلوب والألوان والعناصر، على سبيل المثال، '
                        f'\'واقعية، لقطة مقربة، عالية الدقة، محرك السيارة، مكونات معدنية، مفتاح ربط أزرق، إضاءة استوديع ناعمة\'. يمكن إضافة تفاصيل مثل نسبة العرض إلى العرض إلى الارتفاع (مثال: \'نسبة عرض إلى ارتفاع 16:9\') أو زوايا الكاميرا (مثال: \'لقطة سينمائية\')."'
                        f"}}"
                    )

                    response = client.generate_content(full_prompt_template)

                    generated_content = ""
                    if hasattr(response, 'text') and response.text:
                        generated_content = response.text
                    elif hasattr(response, 'candidates') and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        generated_content += part.text

                    generated_content = generated_content.strip()

                    if generated_content.startswith("```json"):
                        generated_content = generated_content[len("```json"):].strip()
                    if generated_content.endswith("```"):
                        generated_content = generated_content[:-len("```")].strip()

                    parsed_prompts = json.loads(generated_content)
                    if isinstance(parsed_prompts, list) and len(parsed_prompts) > 0:
                        parsed_prompts_data = parsed_prompts[0]
                    elif isinstance(parsed_prompts, dict):
                        parsed_prompts_data = parsed_prompts
                    else:
                        raise ValueError(f"Unexpected JSON format from Gemini: {generated_content}")

                    topic_obj["english_image_prompt"] = parsed_prompts_data.get("english_image_prompt", "")
                    topic_obj["arabic_post_prompt"] = parsed_prompts_data.get("arabic_post_prompt", "")
                    topic_obj["arabic_image_prompt"] = parsed_prompts_data.get("arabic_image_prompt", "")

                    generated_count += 1
                    _log_to_manage_topics_log(f"Successfully generated prompts for '{topic_name}'.")

                except (json.JSONDecodeError, ValueError) as e:
                    _log_to_manage_topics_log(
                        f"ERROR parsing Gemini response for '{topic_name}': {e}. Raw: {generated_content}")
                    errors_occurred = True
                except Exception as e:
                    _log_to_manage_topics_log(f"ERROR during Gemini API call for '{topic_name}': {e}")
                    errors_occurred = True

            ConfigLoader.save_app_config(app)  # Use 'app' here directly
            if not errors_occurred and generated_count == total_topics:
                _log_to_manage_topics_log("Gemini prompt generation complete and SAVED.")
                flash("Gemini prompt generation complete and SAVED.", "success")  # Flash on main context
            elif errors_occurred:
                _log_to_manage_topics_log(
                    f"Gemini prompt generation completed with errors, but changes were SAVED. Generated {generated_count}/{total_topics} successfully.")
                flash(
                    f"Gemini prompt generation completed with errors, but changes were SAVED. Generated {generated_count}/{total_topics} successfully.",
                    "warning")  # Flash on main context
            else:
                _log_to_manage_topics_log("Gemini prompt generation finished. No changes saved or unknown issue.")
                flash("Gemini prompt generation finished. No changes saved or unknown issue.",
                      "info")  # Flash on main context
        except:
            _log_to_manage_topics_log("Gemini prompt generation thread finished.")
