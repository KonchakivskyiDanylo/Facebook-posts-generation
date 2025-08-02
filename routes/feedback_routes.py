from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import database_manager
from .config_loader import FACEBOOK_PAGES # For accessing page details

feedback_routes = Blueprint('feedback_routes', __name__)

@feedback_routes.route('/user_feedback', methods=['GET', 'POST'])
def user_feedback_page():
    page_names = [page["page_name"] for page in FACEBOOK_PAGES]
    selected_page_name = request.args.get('selected_page')
    selected_page_id = None # Actual Facebook page ID from config
    feedback_entries = []
    selected_feedback = None # Currently selected feedback entry for editing

    # Determine selected page for GET and initial load
    if not selected_page_name and FACEBOOK_PAGES:
        selected_page_name = FACEBOOK_PAGES[0]["page_name"]

    if selected_page_name:
        page_obj = next((p for p in FACEBOOK_PAGES if p["page_name"] == selected_page_name), None)
        if page_obj:
            selected_page_id = page_obj.get("facebook_page_id")
            if selected_page_id:
                feedback_entries = database_manager.get_feedback_by_page_id(selected_page_id)
            else:
                flash(f"Page '{selected_page_name}' has no Facebook Page ID configured. Cannot load/add feedback.", "warning")
        else:
            flash(f"Page '{selected_page_name}' not found in configuration.", "danger")

    # Handle selected feedback for editing/display
    selected_feedback_id = request.args.get('selected_feedback_id', type=int)
    if selected_feedback_id and selected_page_id:
        selected_feedback = next((fb for fb in feedback_entries if fb['id'] == selected_feedback_id), None)
        if not selected_feedback:
            flash(f"Feedback ID {selected_feedback_id} not found.", "warning")


    if request.method == 'POST':
        action = request.form.get('action')
        page_name_from_form = request.form.get('selected_page_name_from_form') # Get from hidden field
        
        if not page_name_from_form:
            flash("No page selected for feedback action.", "danger")
            return redirect(url_for('feedback_routes.user_feedback_page'))
        
        page_obj_for_action = next((p for p in FACEBOOK_PAGES if p["page_name"] == page_name_from_form), None)
        if not page_obj_for_action:
            flash(f"Page '{page_name_from_form}' not found for feedback action.", "danger")
            return redirect(url_for('feedback_routes.user_feedback_page'))

        current_fb_page_id_for_action = page_obj_for_action.get("facebook_page_id")
        if not current_fb_page_id_for_action:
            flash(f"Page '{page_name_from_form}' has no Facebook Page ID configured. Cannot perform feedback action.", "danger")
            return redirect(url_for('feedback_routes.user_feedback_page', selected_page=page_name_from_form))


        if action == 'add_feedback':
            feedback_text = request.form.get('feedback_text_area', '').strip()
            if not feedback_text:
                flash("Please enter feedback text.", "danger")
            else:
                success = database_manager.add_feedback(current_fb_page_id_for_action, feedback_text)
                if success:
                    flash("Feedback added successfully.", "success")
                else:
                    flash("Failed to add feedback.", "danger")
            return redirect(url_for('feedback_routes.user_feedback_page', selected_page=page_name_from_form))

        elif action == 'update_feedback':
            feedback_id = request.form.get('feedback_id_to_update', type=int)
            new_feedback_text = request.form.get('feedback_text_area', '').strip()

            if not feedback_id:
                flash("No feedback entry selected to update.", "danger")
            elif not new_feedback_text:
                flash("Feedback text cannot be empty.", "danger")
            else:
                success = database_manager.update_feedback(feedback_id, new_feedback_text)
                if success:
                    flash("Feedback updated successfully.", "success")
                else:
                    flash("Failed to update feedback.", "danger")
            return redirect(url_for('feedback_routes.user_feedback_page', selected_page=page_name_from_form, selected_feedback_id=feedback_id))

        elif action == 'delete_feedback':
            feedback_id = request.form.get('feedback_id_to_delete', type=int)
            if not feedback_id:
                flash("No feedback entry selected to delete.", "danger")
            else:
                success = database_manager.delete_feedback(feedback_id)
                if success:
                    flash("Feedback deleted successfully.", "success")
                else:
                    flash("Failed to delete feedback.", "danger")
            return redirect(url_for('feedback_routes.user_feedback_page', selected_page=page_name_from_form))
    
    return render_template('user_feedback.html',
                           page_names=page_names,
                           selected_page_name=selected_page_name,
                           feedback_entries=feedback_entries,
                           selected_feedback=selected_feedback)

# This route is now mostly redundant as user_feedback_page handles POST actions
# @feedback_routes.route('/submit_feedback', methods=['POST'])
# def submit_feedback():
#     return redirect(url_for('feedback_routes.user_feedback_page'))