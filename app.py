from flask import Flask, render_template, session, redirect, url_for, abort, request
import os
import re

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_for_session'

PASSAGES_DIR = 'passages'

def passage_exists(grade, level):
    filename = os.path.join(PASSAGES_DIR, f'grade{grade}_level{level}.txt')
    return os.path.exists(filename)

def parse_passage_file(grade, level):
    filename = os.path.join(PASSAGES_DIR, f'grade{grade}_level{level}.txt')
    passage_text = ""
    questions = []

    if not passage_exists(grade, level): # Check before trying to open
        return None, [] # Indicates file not found

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        passage_part_raw, questions_part_raw = content.split('---QUESTIONS---', 1) if '---QUESTIONS---' in content else (content, "")
        passage_text = passage_part_raw.strip().replace('\n', '<br>')

        if not questions_part_raw: # No questions section
            return passage_text, questions

        questions_part = questions_part_raw.strip()

        question_blocks = []
        current_block = []
        for line in questions_part.splitlines():
            line = line.strip()
            if not line: # Skip empty lines
                continue
            if line.startswith('Q') and current_block: # New question starts
                question_blocks.append(current_block)
                current_block = []
            current_block.append(line)
        if current_block: # Append the last question block
            question_blocks.append(current_block)

        for i, block in enumerate(question_blocks):
            question_text_line = block[0]
            # Regex to capture question text after "Q<number>:"
            match = re.match(r'Q\d*:\s*(.*)', question_text_line)
            if not match:
                print(f"Warning: Malformed question line in {filename}: {question_text_line}")
                continue

            question_text = match.group(1)
            options = []
            correct_answer_char = None

            for item in block[1:]: # Process options and correct answer line
                # Check if the line looks like an option (e.g., "A) Text", "B. Text")
                option_match = re.match(r'([A-Da-d])[\.\)]\s*(.*)', item)
                if option_match:
                    options.append(item) # Store the full original option line
                elif item.startswith('Correct:'):
                    correct_answer_char = item.split(':', 1)[1].strip().upper()

            if question_text: # Ensure question text was found
                questions.append({
                    'id': i + 1,
                    'text': question_text,
                    'options': options,
                    'correct': correct_answer_char
                })

    except FileNotFoundError: # Should ideally be caught by passage_exists, but as a safeguard
        return None, []
    except Exception as e:
        print(f"Error parsing file {filename}: {e}")
        # Return a specific error message that can be shown to the user
        return f"An error occurred while reading or parsing the passage file: {os.path.basename(filename)}.", []

    return passage_text, questions


@app.route('/')
def index():
    session.pop('results', None)
    return render_template('index.html')

@app.route('/test/<int:grade>/<int:level>', methods=['GET', 'POST'])
def test_page(grade, level):
    passage_content, questions = parse_passage_file(grade, level)

    # Check for errors from parse_passage_file
    if passage_content is None: # Indicates file not found by parse_passage_file
        abort(404, description=f"Passage for Grade {grade}, Level {level} not found.")
    # isinstance check for our custom error message string from parse_passage_file
    if isinstance(passage_content, str) and passage_content.startswith("An error occurred"):
        abort(500, description=passage_content)


    if request.method == 'POST':
        score = 0
        results_summary = []

        for question in questions:
            question_id_str = str(question['id'])
            submitted_answer = request.form.get(f'question_{question_id_str}') # e.g., 'A', 'B'

            is_correct = False
            if submitted_answer and question['correct'] and submitted_answer.upper() == question['correct'].upper():
                score += 1
                is_correct = True

            results_summary.append({
                'question_id': question['id'],
                'question_text': question['text'],
                'submitted_answer': submitted_answer.upper() if submitted_answer else "Not Answered",
                'correct_answer': question['correct'], # The correct char e.g. 'A'
                'options': question['options'],
                'is_correct': is_correct
            })

        total_questions = len(questions)
        session['results'] = {
            'score': score,
            'total_questions': total_questions,
            'summary': results_summary,
            'grade': grade,
            'level': level
        }
        return redirect(url_for('test_page_results', grade=grade, level=level))

    # GET request
    return render_template('test.html',
                           grade=grade,
                           level=level,
                           passage=passage_content,
                           questions=questions,
                           results=None) # No results displayed on the test page itself

@app.route('/results/<int:grade>/<int:level>')
def test_page_results(grade, level):
    results_data = session.get('results', None) # Use .get() to keep results if user refreshes

    if not results_data or results_data['grade'] != grade or results_data['level'] != level:
        # If no results, or results for a different test, redirect to the current test page
        return redirect(url_for('test_page', grade=grade, level=level))

    # Determine if links to next level/grade should be shown
    show_next_level = passage_exists(grade, level + 1)
    show_next_grade = passage_exists(grade + 1, 1)


    return render_template('results.html',
                           grade=grade,
                           level=level,
                           results=results_data,
                           show_next_level_link=show_next_level,
                           show_next_grade_link=show_next_grade)

if __name__ == '__main__':
    app.run(debug=True)
