# routes/page_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os
import json
from .config_loader import FACEBOOK_PAGES, ConfigLoader # Import FACEBOOK_PAGES and ConfigLoader

# Define the blueprint
page_routes = Blueprint('page_routes', __name__)

# Helper to get default prompts for a page or return an empty dict
def _get_page_default_prompts(page_data):
    return page_data.get("prompts", {
        "default_prompt_en": "",
        "default_prompt_ar": "",
        "default_image_prompt_en": "",
        "default_image_prompt_ar": ""
    })

@page_routes.route('/page_details', methods=['GET', 'POST'])
def page_details_page():
    page_names = [page["page_name"] for page in FACEBOOK_PAGES]
    selected_page = None
    page_default_prompts = {}
    
    selected_page_name = request.args.get('selected_page')

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_page':
            new_page_name = request.form.get('new_page_name', '').strip()
            if not new_page_name:
                flash("Page name cannot be empty.", "danger")
            elif any(p["page_name"].lower() == new_page_name.lower() for p in FACEBOOK_PAGES):
                flash(f"A page with the name '{new_page_name}' already exists.", "warning")
            else:
                new_page_data = {
                    "page_name": new_page_name,
                    "facebook_page_id": "YOUR_FACEBOOK_PAGE_ID",
                    "facebook_access_token": "YOUR_LONG_LIVED_PAGE_ACCESS_TOKEN",
                    "english_contact_info": "Website: \nTax ID: \nAddress: \nPostal Code : \nLocation: ",
                    "arabic_contact_info": "الموقع الاكترونى: \nتسجيل ضريبى: \nالعنوان: \nاللوكيشن: ",
                    "topics": [], # Initialize with an empty topics list
                    "prompts": { # Initialize with empty default prompts
                        "default_prompt_en": "",
                        "default_prompt_ar": "",
                        "default_image_prompt_en": "",
                        "default_image_prompt_ar": ""
                    }
                }
                FACEBOOK_PAGES.append(new_page_data)
                ConfigLoader.save_app_config(current_app)
                flash(f"Page '{new_page_name}' added. Please fill in details and save.", "success")
                selected_page_name = new_page_name # Select the newly added page
            
            return redirect(url_for('page_routes.page_details_page', selected_page=selected_page_name))

        page_name_from_form = request.form.get('page_name') or request.form.get('original_page_name')
        
        if page_name_from_form:
            page_index = next((i for i, p in enumerate(FACEBOOK_PAGES) if p["page_name"] == page_name_from_form), -1)

            if page_index != -1:
                selected_page = FACEBOOK_PAGES[page_index]
            else:
                flash(f"Selected page '{page_name_from_form}' not found for action.", "danger")
                return redirect(url_for('page_routes.page_details_page'))
        else:
            flash("No page selected for action.", "danger")
            return redirect(url_for('page_routes.page_details_page'))


        if action == 'update_page':
            new_page_name = request.form.get('page_name', '').strip()
            facebook_page_id = request.form.get('facebook_page_id', '').strip()
            facebook_access_token = request.form.get('facebook_access_token', '').strip()
            english_contact_info = request.form.get('english_contact_info', '').strip()
            arabic_contact_info = request.form.get('arabic_contact_info', '').strip()

            if new_page_name != selected_page["page_name"]:
                if any(p["page_name"].lower() == new_page_name.lower() for p in FACEBOOK_PAGES if p["page_name"] != selected_page["page_name"]):
                    flash(f"A page with the name '{new_page_name}' already exists. Please choose a different name.", "warning")
                    page_default_prompts = _get_page_default_prompts(selected_page)
                    return render_template('page_details.html', page_names=page_names, selected_page=selected_page, page_default_prompts=page_default_prompts)
            
            selected_page["page_name"] = new_page_name
            selected_page["facebook_page_id"] = facebook_page_id
            selected_page["facebook_access_token"] = facebook_access_token
            selected_page["english_contact_info"] = english_contact_info
            selected_page["arabic_contact_info"] = arabic_contact_info

            ConfigLoader.save_app_config(current_app)
            flash(f"Page '{new_page_name}' details updated and saved.", "success")
            return redirect(url_for('page_routes.page_details_page', selected_page=new_page_name))

        elif action == 'delete_page':
            FACEBOOK_PAGES[:] = [p for p in FACEBOOK_PAGES if p["page_name"] != selected_page["page_name"]]
            ConfigLoader.save_app_config(current_app)
            flash(f"Page '{selected_page['page_name']}' deleted.", "success")
            return redirect(url_for('page_routes.page_details_page'))

        elif action == 'update_default_prompts':
            if "prompts" not in selected_page:
                selected_page["prompts"] = {}
            
            selected_page["prompts"]["default_prompt_en"] = request.form.get('default_prompt_en', '').strip()
            selected_page["prompts"]["default_prompt_ar"] = request.form.get('default_prompt_ar', '').strip()
            selected_page["prompts"]["default_image_prompt_en"] = request.form.get('default_image_prompt_en', '').strip()
            selected_page["prompts"]["default_image_prompt_ar"] = request.form.get('default_image_prompt_ar', '').strip()

            ConfigLoader.save_app_config(current_app)
            flash(f"Default prompts for '{selected_page['page_name']}' updated and saved.", "success")
            return redirect(url_for('page_routes.page_details_page', selected_page=selected_page['page_name']))

    # If it's a GET request or after a POST that redirects, re-fetch selected_page
    if selected_page_name:
        selected_page = next((p for p in FACEBOOK_PAGES if p["page_name"] == selected_page_name), None)
    
    # If no page is selected (e.g., first load or after deletion), try to select the first available
    if not selected_page and FACEBOOK_PAGES:
        selected_page = FACEBOOK_PAGES[0]
        selected_page_name = selected_page["page_name"]

    if selected_page:
        page_default_prompts = _get_page_default_prompts(selected_page)

    return render_template('page_details.html', 
                           page_names=page_names, 
                           selected_page=selected_page,
                           page_default_prompts=page_default_prompts)