from flask import Flask, render_template, session, redirect, url_for, abort, request
import os
import re # For splitting options

app = Flask(__name__)
app.secret_key = 'your_very_secret_key'  # Replace with a real secret key in production

PASSAGES_DIR = 'passages'

def parse_passage_file(grade, level):
    filename = os.path.join(PASSAGES_DIR, f'grade{grade}_level{level}.txt')
    passage_text = ""
    questions = []

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace newlines in passage text with <br> for HTML display
        passage_part_raw, questions_part_raw = content.split('---QUESTIONS---', 1) if '---QUESTIONS---' in content else (content, "")
        passage_text = passage_part_raw.strip().replace('\n', '<br>')

        if not questions_part_raw:
            return passage_text, questions

        questions_part = questions_part_raw.strip()

        current_question_data = []
        for line in questions_part.split('\n'):
            line = line.strip()
            if not line:
                continue
            current_question_data.append(line)

        # Group lines by question
        question_blocks = []
        current_block = []
        for line in current_question_data:
            if line.startswith('Q') and current_block:
                question_blocks.append(current_block)
                current_block = []
            current_block.append(line)
        if current_block:
            question_blocks.append(current_block)

        for block in question_blocks:
            question_text_line = block[0]
            # Ensure question_text_line is in 'Q#: Text' format
            match = re.match(r'Q\d+:\s*(.*)', question_text_line)
            if not match:
                continue # Skip malformed question lines

            question_text = match.group(1)
            options = []
            correct_answer_char = None

            for item in block[1:]:
                if item.startswith(('A)', 'B)', 'C)', 'D)')):
                    options.append(item)
                elif item.startswith('Correct:'):
                    correct_answer_char = item.split(':', 1)[1].strip()

            if question_text:
                questions.append({
                    'text': question_text,
                    'options': options, # Store full option text e.g. "A) Option One"
                    'correct': correct_answer_char
                })

    except FileNotFoundError:
        return None, []
    except Exception as e:
        print(f"Error parsing file {filename}: {e}") # Log error
        return f"Error reading or parsing passage file: {filename}", [] # User-friendly error

    return passage_text, questions

@app.route('/')
def index():
    # Now points to an actual index.html
    return render_template('index.html')

@app.route('/test/<int:grade>/<int:level>', methods=['GET', 'POST'])
def test_page(grade, level):
    if request.method == 'POST':
        # Process answers - for now, just re-display the page or redirect
        # We'll implement answer checking in a later step
        # For example, get selected answers:
        # answers = {}
        # for key in request.form:
        #    if key.startswith('question_'):
        #        answers[key] = request.form[key]
        # print("Submitted answers:", answers) # For debugging
        return redirect(url_for('test_page', grade=grade, level=level + 1)) # Go to next level on submit for now

    passage_content, questions = parse_passage_file(grade, level)

    if passage_content is None:
        abort(404, description=f"Passage for Grade {grade}, Level {level} not found.")

    return render_template('test.html',
                           grade=grade,
                           level=level,
                           passage=passage_content,
                           questions=questions)

if __name__ == '__main__':
    app.run(debug=True)
