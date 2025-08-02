from flask import Blueprint, render_template, request, flash
import ml_predictor # Correct module for ML logic

ml_routes = Blueprint('ml_routes', __name__)

@ml_routes.route('/ml_dashboard', methods=['GET', 'POST'])
def ml_dashboard_page():
    insights = {}
    
    # Initialize insight sections as empty lists
    insights['topic'] = {'high': [], 'low': [], 'message': "No data processed."}
    insights['language'] = {'high': [], 'low': [], 'message': "No data processed."}
    insights['text_prompt'] = {'high': [], 'low': [], 'message': "No data processed."}
    insights['image_prompt'] = {'high': [], 'low': [], 'message': "No data processed."}
    insights['generator_params'] = {'providers': [], 'models': [], 'temperatures': [], 'message': "No data processed."}
    insights['posting_times'] = {'hours': [], 'days': [], 'message': "No data processed."}


    # Trigger analysis on GET (initial load) or POST (explicit refresh)
    if request.method == 'POST' or request.args.get('run_analysis') == 'true':
        
        try:
            # Re-train model first to ensure latest data is used for insights
            train_success, train_message = ml_predictor.train_model()
            if not train_success:
                flash(f"ML model training failed: {train_message}. Insights might be incomplete.", "warning")
            else:
                flash(f"ML model re-trained successfully: {train_message}", "info")

            high_topics, low_topics, topic_msg = ml_predictor.get_topic_performance_insights()
            insights['topic'] = {'high': high_topics, 'low': low_topics, 'message': topic_msg}

            best_languages, lang_msg = ml_predictor.get_language_preference_insights()
            insights['language'] = {'high': best_languages, 'low': [], 'message': lang_msg}

            high_text_prompts, low_text_prompts, text_prompt_msg = ml_predictor.get_text_prompt_performance_insights()
            insights['text_prompt'] = {'high': high_text_prompts, 'low': low_text_prompts, 'message': text_prompt_msg}
            
            high_image_prompts, low_image_prompts, image_prompt_msg = ml_predictor.get_image_prompt_performance_insights()
            insights['image_prompt'] = {'high': high_image_prompts, 'low': low_image_prompts, 'message': image_prompt_msg}

            best_providers, best_models, best_temperatures, gen_param_msg = ml_predictor.get_generator_parameter_insights()
            insights['generator_params'] = {
                'providers': best_providers, 
                'models': best_models, 
                'temperatures': best_temperatures, 
                'message': gen_param_msg
            }

            optimal_hours, optimal_days, posting_times_msg = ml_predictor.get_optimal_posting_times_insights()
            insights['posting_times'] = {'hours': optimal_hours, 'days': optimal_days, 'message': posting_times_msg}
            
            flash("ML insights generated successfully.", "success")

        except Exception as e:
            flash(f"Error generating ML insights: {e}", "danger")
            print(f"ML Dashboard Error: {e}")

    return render_template('ml_dashboard.html', insights=insights)