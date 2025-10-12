#!/usr/bin/env python3
"""
Registrants Management UI - Flask Application

A comprehensive web interface for managing registrants for Chayannito 26.
Features CRUD operations, grouping by gender and group, and live verification links.
"""

import json
import os
import base64
import codecs
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = 'chayannito26-management-ui-secret-key'

# Configuration
REGISTRANTS_FILE = Path(__file__).parent.parent / 'verify' / 'registrants.json'
REVENUES_FILE = Path(__file__).parent.parent / 'income' / 'revenues.json'
VERIFICATION_BASE_URL = 'https://chayannito26.github.io/verify'

# Group and gender mappings
GROUP_INFO = {
    'AR': {'name': 'Arts', 'emoji': '🎨', 'color': 'blue'},
    'SC': {'name': 'Science', 'emoji': '🔬', 'color': 'red'},
    'CO': {'name': 'Commerce', 'emoji': '💼', 'color': 'green'}
}

GENDER_INFO = {
    'Male': {'short': 'B', 'color': 'blue', 'dot': '🔵'},
    'Female': {'short': 'G', 'color': 'pink', 'dot': '🟣'}
}

# T-shirt size options (keep consistent across UI)
TSHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

# Client mappings for revenue tracking
CLIENT_MAPPINGS = {
    'SC': {  # Science
        'Male': 'Arian Mollik Wasi',
        'Female': 'Marzia Mittika'
    },
    'AR': {  # Arts
        'Male': 'Sahariar Nafiz',
        'Female': 'Nafiza Tanzim Hafsa'
    },
    'CO': {  # Commerce
        'Male': 'Tanzid Jayid',
        'Female': 'Mehbuba'
    }
}

def load_registrants():
    """Load registrants from JSON file."""
    try:
        with open(REGISTRANTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        flash('Error reading registrants file. Using empty list.', 'error')
        return []

def save_registrants(registrants):
    """Save registrants to JSON file immediately."""
    try:
        with open(REGISTRANTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(registrants, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        flash(f'Error saving registrants: {str(e)}', 'error')
        return False

def load_revenues():
    """Load revenues from JSON file."""
    try:
        with open(REVENUES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print('Error reading revenues file. Using empty list.')
        return []

def save_revenues(revenues):
    """Save revenues to JSON file."""
    try:
        with open(REVENUES_FILE, 'w', encoding='utf-8') as f:
            json.dump(revenues, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f'Error saving revenues: {str(e)}')
        return False

def add_revenue_entry(name, group, gender, registration_date):
    """Add a revenue entry for a new registration."""
    try:
        revenues = load_revenues()
        
        # Get client name based on group and gender
        client_name = CLIENT_MAPPINGS.get(group, {}).get(gender, 'Unknown Client')
        
        # Create revenue entry
        revenue_entry = {
            "id": int(datetime.now().timestamp() * 1000),  # timestamp in milliseconds
            "source": "Registration Fee",
            "amount": 1200,
            "date": registration_date,
            "type": "Registration",
            "clients": [client_name],
            "comments": name
        }
        
        revenues.append(revenue_entry)
        
        if save_revenues(revenues):
            print(f'Revenue entry added for {name}')
            return True
        else:
            print(f'Failed to save revenue entry for {name}')
            return False
            
    except Exception as e:
        print(f'Error adding revenue entry: {str(e)}')
        return False

def push_income_repo():
    """Push changes to the income repository."""
    try:
        income_dir = Path(__file__).parent.parent / 'income'
        
        def run_cmd(cmd):
            try:
                if isinstance(cmd, str):
                    completed = subprocess.run(cmd, cwd=income_dir, shell=True, capture_output=True, text=True)
                else:
                    completed = subprocess.run(cmd, cwd=income_dir, capture_output=True, text=True)
                return {
                    'returncode': completed.returncode,
                    'stdout': completed.stdout.strip(),
                    'stderr': completed.stderr.strip()
                }
            except Exception as e:
                return {'returncode': 1, 'stdout': '', 'stderr': str(e)}
        
        # Initialize git if not already done
        init_res = run_cmd(['git', 'init'])
        
        # Add all files
        add_res = run_cmd(['git', 'add', '.'])
        
        # Commit
        commit_message = f"Add revenue entry @ {datetime.now().isoformat()}"
        commit_res = run_cmd(['git', 'commit', '-m', commit_message])
        
        # Push (assuming remote is set up)
        push_res = run_cmd(['git', 'push'])
        
        print(f'Git operations completed: add={add_res["returncode"]}, commit={commit_res["returncode"]}, push={push_res["returncode"]}')
        
        return commit_res['returncode'] == 0 or 'nothing to commit' in commit_res['stdout']
        
    except Exception as e:
        print(f'Error pushing to income repo: {str(e)}')
        return False

def id_to_filename(reg_id):
    """Convert registration ID to filename using the same logic as generate_verifications.py"""
    b64 = base64.urlsafe_b64encode(reg_id.encode('utf-8')).decode('utf-8')
    b64 = b64.rstrip("=")
    rot = codecs.encode(b64, "rot_13")
    return rot[::-1]

def get_verification_url(reg_id):
    """Get the verification URL for a registration ID."""
    filename = id_to_filename(reg_id)
    return f"{VERIFICATION_BASE_URL}/{filename}.html"

def get_next_registration_id(group, gender, ignore_ids=None):
    """Generate the next registration ID for a group and gender.

    This returns the lowest available sequence number (first gap) for the
    given group/gender prefix. Optionally, pass `ignore_ids` as an iterable of
    registration_id strings which should be treated as taken for this
    calculation (useful to reserve or exclude certain IDs even if vacant).
    """
    registrants = load_registrants()
    gender_short = GENDER_INFO[gender]['short']
    prefix = f"{group}-{gender_short}-"

    # Collect taken numbers from existing registrants
    taken = set()
    for reg in registrants:
        reg_id = reg.get('registration_id', '')
        if reg_id.startswith(prefix):
            try:
                number = int(reg_id.split('-')[-1])
                taken.add(number)
            except Exception:
                continue

    # Include ignore_ids (treat them as taken) if provided
    if ignore_ids:
        for iid in ignore_ids:
            if not isinstance(iid, str):
                continue
            if iid.startswith(prefix):
                try:
                    n = int(iid.split('-')[-1])
                    taken.add(n)
                except Exception:
                    continue

    # Find the smallest positive integer not in taken (first gap)
    next_number = 1
    while next_number in taken:
        next_number += 1

    return f"{prefix}{next_number:04d}"

def group_registrants(registrants):
    """Group registrants by group and gender."""
    grouped = {}
    
    for registrant in registrants:
        reg_id = registrant.get('registration_id', '')
        if not reg_id:
            continue
            
        # Extract group from registration ID
        parts = reg_id.split('-')
        if len(parts) >= 2:
            group = parts[0]
            gender_short = parts[1]
            
            # Convert gender short to full name
            gender = None
            for g, info in GENDER_INFO.items():
                if info['short'] == gender_short:
                    gender = g
                    break
            
            if group in GROUP_INFO and gender:
                if group not in grouped:
                    grouped[group] = {}
                if gender not in grouped[group]:
                    grouped[group][gender] = []
                
                grouped[group][gender].append(registrant)
    
    # Sort each group's gender list by registration_id (ascending).
    # registration_id is expected in the form 'GG-S-####' with zero-padded numbers,
    # so lexicographic sort works. Fall back to empty string for missing IDs.
    for grp in grouped.values():
        for gen, lst in grp.items():
            try:
                lst.sort(key=lambda r: r.get('registration_id', ''))
            except Exception:
                # If any unexpected data prevents sorting, leave list as-is
                pass

    return grouped

@app.route('/')
def index():
    """Display the main dashboard with registrants."""
    view_mode = request.args.get('view', 'cards')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    registrants = load_registrants()

    # Sorting logic
    reverse = sort_order == 'desc'
    if sort_by == 'roll':
        # Sort by the last 5 digits of the roll number, converting to int for proper numeric sorting
        all_registrants_sorted = sorted(registrants, key=lambda x: int(x['roll'][-5:]) if x['roll'] and x['roll'][-5:].isdigit() else 0, reverse=reverse)
    elif sort_by == 'registration_id':
        all_registrants_sorted = sorted(registrants, key=lambda x: x['registration_id'], reverse=reverse)
    else:  # Default to sorting by name
        all_registrants_sorted = sorted(registrants, key=lambda x: x['name'], reverse=reverse)

    grouped = {}
    if view_mode == 'cards':
        grouped = group_registrants(all_registrants_sorted)

    stats = {
        'total': len(registrants),
        'active': len([r for r in registrants if not r.get('revoked')]),
        'revoked': len([r for r in registrants if r.get('revoked')]),
        'total_payments': sum(r.get('paid', 0) for r in registrants if not r.get('revoked'))
    }

    return render_template(
        'index.html',
        grouped=grouped,
        all_registrants=all_registrants_sorted,
        stats=stats,
        GROUP_INFO=GROUP_INFO,
        GENDER_INFO=GENDER_INFO,
        view_mode=view_mode,
        get_verification_url=get_verification_url,
        sort_by=sort_by,
        sort_order=sort_order
    )

@app.route('/add', methods=['GET', 'POST'])
def add_registrant():
    """Add a new registrant."""
    if request.method == 'POST':
        registrants = load_registrants()
        
        # Extract form data
        name = request.form.get('name', '').strip()
        roll = request.form.get('roll', '').strip()
        gender = request.form.get('gender', '')
        group = request.form.get('group', '')
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        paid = request.form.get('paid', 0, type=int)
        referred_by = request.form.get('referred_by', '').strip()
        parts_available = request.form.getlist('parts_available')
        tshirt_size = request.form.get('tshirt_size', '').strip()
        
        # Validation
        if not name or not roll or not gender or not group:
            flash('Name, roll number, gender, and group are required.', 'error')
            return render_template('add_registrant.html', 
                                 GROUP_INFO=GROUP_INFO, 
                                 GENDER_INFO=GENDER_INFO,
                                 TSHIRT_SIZES=TSHIRT_SIZES,
                                 form_data=request.form)

        # T-shirt size validation when applicable
        if 'T-Shirt' in parts_available:
            if not tshirt_size:
                flash('Please select a T-shirt size when T-Shirt is selected.', 'error')
                return render_template('add_registrant.html', 
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     form_data=request.form)
            if tshirt_size not in TSHIRT_SIZES:
                flash('Invalid T-shirt size selected.', 'error')
                return render_template('add_registrant.html', 
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     form_data=request.form)
        
        # Use provided registration_id if the user edited it, otherwise generate one
        provided_id = request.form.get('registration_id', '').strip()
        if provided_id:
            # Check uniqueness
            if any(r.get('registration_id') == provided_id for r in registrants):
                flash(f'Registration ID {provided_id} is already in use. Please choose a different ID.', 'error')
                return render_template('add_registrant.html', 
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     form_data=request.form)
            registration_id = provided_id
        else:
            # Generate registration ID
            registration_id = get_next_registration_id(group, gender)
        
        # Sanitize tshirt size: only keep if T-Shirt is selected
        if 'T-Shirt' not in parts_available:
            tshirt_size = ''

        # Create new registrant
        registration_date_obj = datetime.now()
        registration_date_str = registration_date_obj.strftime('%d %B %Y')
        registration_date_iso = registration_date_obj.strftime('%Y-%m-%d')
        
        new_registrant = {
            'name': name,
            'roll': roll,
            'gender': gender,
            'group': group,  # Add group to registrant data
            'registration_date': registration_date_str,
            'registration_id': registration_id,
            'photo': '',
            'revoked': False,
            'referred_by': referred_by,
            'paid': paid,
            'email': email,
            'phone': phone,
            'parts_available': parts_available,
            'tshirt_size': tshirt_size
        }
        
        registrants.append(new_registrant)
        
        if save_registrants(registrants):
            # Add revenue entry
            add_revenue_entry(name, group, gender, registration_date_iso)
            
            # Push changes to income repository
            push_income_repo()
            
            flash(f'Successfully added {name} with ID {registration_id}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to save registrant. Please try again.', 'error')
    
    return render_template('add_registrant.html', 
                         GROUP_INFO=GROUP_INFO, 
                         GENDER_INFO=GENDER_INFO,
                         TSHIRT_SIZES=TSHIRT_SIZES)


@app.route('/api/next_registration_id')
def api_next_registration_id():
    """Return the next registration id for given group and gender.

    Query params: group, gender
    Response JSON: { "next_id": "AR-B-0001" }
    """
    group = request.args.get('group')
    gender = request.args.get('gender')
    if not group or not gender:
        return jsonify({'error': 'missing group or gender'}), 400
    # parse optional ignore_ids query param: comma-separated registration IDs
    ignore_param = request.args.get('ignore_ids', '')
    ignore_ids = [i.strip() for i in ignore_param.split(',') if i.strip()] if ignore_param else None

    try:
        next_id = get_next_registration_id(group, gender, ignore_ids=ignore_ids)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'next_id': next_id})

@app.route('/edit/<registration_id>', methods=['GET', 'POST'])
def edit_registrant(registration_id):
    """Edit an existing registrant."""
    registrants = load_registrants()
    
    # Find the registrant
    registrant = None
    registrant_index = None
    for i, r in enumerate(registrants):
        if r.get('registration_id') == registration_id:
            registrant = r
            registrant_index = i
            break
    
    if not registrant:
        flash(f'Registrant with ID {registration_id} not found.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Update registrant data
        # Handle potential registration_id change
        new_registration_id = request.form.get('registration_id', '').strip()
        old_registration_id = registrant.get('registration_id', '')
        registrants_all = registrants  # alias for clarity
        # Validate and ensure uniqueness if changed
        if new_registration_id and new_registration_id != old_registration_id:
            # Basic format check: should contain two hyphens e.g. 'AR-B-0001'
            parts = new_registration_id.split('-')
            if len(parts) < 3:
                flash('Invalid registration ID format. Expected like AR-B-0001.', 'error')
                return render_template('edit_registrant.html', 
                                     registrant=registrant,
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     get_verification_url=get_verification_url)
            # Check uniqueness across other registrants
            if any(r.get('registration_id') == new_registration_id for r in registrants_all if r is not registrant):
                flash(f'Registration ID {new_registration_id} is already in use. Please choose a different ID.', 'error')
                return render_template('edit_registrant.html', 
                                     registrant=registrant,
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     get_verification_url=get_verification_url)
            # Try to infer group and gender from the new ID and validate against submitted gender
            parsed_group = parts[0]
            parsed_gender_short = parts[1]
            parsed_gender_full = None
            for g, info in GENDER_INFO.items():
                if info.get('short') == parsed_gender_short:
                    parsed_gender_full = g
                    break

            submitted_gender = request.form.get('gender', '')
            # If both submitted gender and parsed gender exist and conflict, ask user to fix
            if submitted_gender and parsed_gender_full and submitted_gender != parsed_gender_full:
                flash('The gender encoded in the new Registration ID does not match the selected gender. Please make them consistent.', 'error')
                return render_template('edit_registrant.html', 
                                     registrant=registrant,
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     get_verification_url=get_verification_url)

            # Update group if valid
            if parsed_group in GROUP_INFO:
                registrant['group'] = parsed_group

            # Finally update the registration_id on the registrant
            registrant['registration_id'] = new_registration_id

        registrant['name'] = request.form.get('name', '').strip()
        registrant['roll'] = request.form.get('roll', '').strip()
        registrant['gender'] = request.form.get('gender', '')
        registrant['email'] = request.form.get('email', '').strip()
        registrant['phone'] = request.form.get('phone', '').strip()
        registrant['paid'] = request.form.get('paid', 0, type=int)
        registrant['referred_by'] = request.form.get('referred_by', '').strip()
        registrant['parts_available'] = request.form.getlist('parts_available')
        registrant['revoked'] = 'revoked' in request.form
        tshirt_size = request.form.get('tshirt_size', '').strip()
        # Sanitize tshirt size: only keep if T-Shirt is selected
        if 'T-Shirt' not in (registrant['parts_available'] or []):
            tshirt_size = ''
        else:
            # When T-Shirt selected, require a valid size
            if not tshirt_size:
                flash('Please select a T-shirt size when T-Shirt is selected.', 'error')
                return render_template('edit_registrant.html', 
                                     registrant=registrant,
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     get_verification_url=get_verification_url)
            if tshirt_size not in TSHIRT_SIZES:
                flash('Invalid T-shirt size selected.', 'error')
                return render_template('edit_registrant.html', 
                                     registrant=registrant,
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     get_verification_url=get_verification_url)
        registrant['tshirt_size'] = tshirt_size
        
        # Photo URL if provided
        photo_url = request.form.get('photo', '').strip()
        if photo_url:
            registrant['photo'] = photo_url
        
        # Update the list entry
        registrants[registrant_index] = registrant
        
        if save_registrants(registrants):
            flash(f'Successfully updated {registrant["name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to save changes. Please try again.', 'error')
    
    return render_template('edit_registrant.html', 
                         registrant=registrant,
                         GROUP_INFO=GROUP_INFO, 
                         GENDER_INFO=GENDER_INFO,
                         TSHIRT_SIZES=TSHIRT_SIZES,
                         get_verification_url=get_verification_url)

@app.route('/delete/<registration_id>', methods=['POST'])
def delete_registrant(registration_id):
    """Delete a registrant."""
    registrants = load_registrants()
    # Find the registrant to delete
    registrant_to_delete = None
    for r in registrants:
        if r.get('registration_id') == registration_id:
            registrant_to_delete = r
            break

    if not registrant_to_delete:
        flash(f'Registrant with ID {registration_id} not found.', 'error')
        return redirect(url_for('index'))

    # Remove from registrants list
    registrants = [r for r in registrants if r.get('registration_id') != registration_id]

    if not save_registrants(registrants):
        flash('Failed to delete registrant. Please try again.', 'error')
        return redirect(url_for('index'))

    # Check if the form requested deletion of the revenue entry as well
    try:
        delete_revenue_flag = False
        if request.method == 'POST':
            # form field 'delete_revenue' set to '1' when user confirmed
            delete_revenue_flag = request.form.get('delete_revenue', '0') in ('1', 'true', 'True')

        if delete_revenue_flag:
            # Load revenues and remove entries that match this registrant's name and look like registration revenue
            revenues = load_revenues()
            original_len = len(revenues)

            # Match by comments (name) and type/source to avoid accidental removals
            def matches_revenue_entry(entry):
                try:
                    if entry.get('comments') == registrant_to_delete.get('name') and entry.get('type') == 'Registration':
                        return True
                except Exception:
                    return False
                return False

            revenues = [e for e in revenues if not matches_revenue_entry(e)]

            if len(revenues) < original_len:
                if save_revenues(revenues):
                    # Attempt to push changes in income repo
                    push_income_repo()
                    flash(f'Successfully deleted registrant and associated revenue entries for {registrant_to_delete.get("name")}.', 'success')
                else:
                    flash('Registrant deleted but failed to update revenues file. Please check the server logs.', 'error')
            else:
                flash(f'Registrant deleted, but no matching revenue entries were found for {registrant_to_delete.get("name")}.', 'success')
        else:
            flash(f'Successfully deleted registrant with ID {registration_id}.', 'success')
    except Exception as e:
        print(f'Error while deleting revenue entry: {str(e)}')
        flash(f'Deleted registrant but encountered an error while handling revenue entries: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for getting statistics."""
    registrants = load_registrants()
    grouped = group_registrants(registrants)
    
    stats = {
        'total': len(registrants),
        'active': len([r for r in registrants if not r.get('revoked', False)]),
        'revoked': len([r for r in registrants if r.get('revoked', False)]),
        'total_payments': sum(r.get('paid', 0) for r in registrants),
        'groups': {}
    }
    
    for group, genders in grouped.items():
        stats['groups'][group] = {
            'total': sum(len(registrants) for registrants in genders.values()),
            'genders': {gender: len(registrants) for gender, registrants in genders.items()}
        }
    
    return jsonify(stats)


@app.route('/api/student/<roll>')
def api_get_student(roll):
    """API endpoint to fetch student data by roll number.
    
    Response JSON: {
        "found": true/false,
        "student": {
            "name": "STUDENT NAME",
            "gender": "Man/Woman",
            "group": "Science/Arts/Commerce", 
            "phone": "01XXXXXXXXX"
        },
        "image_url": "/api/student-image/1202425010276"
    }
    """
    # Path to the student data file (relative to parent directory)
    students_file = Path(__file__).parent.parent / 'college-students' / 'data' / 'students.json'

    try:
        if not students_file.exists():
            return jsonify({
                'found': False,
                'error': 'Student data file not found',
                'image_url': '/api/student-image/placeholder'
            })
            
        with open(students_file, 'r', encoding='utf-8') as f:
            students = json.load(f)
        
        # Find student by roll number
        student = None
        for s in students:
            if str(s.get('class_roll', '')).strip() == str(roll).strip():
                student = s
                break

        if student:
            # Map gender values to our format
            gender_mapping = {
                'Man': 'Male',
                'Woman': 'Female',
                'Unknown': 'Male'  # Default fallback
            }
            
            # Map group values to our format
            group_mapping = {
                'Science': 'SC',
                'Arts': 'AR', 
                'Commerce': 'CO'
            }
            
            student_data = {
                'name': student.get('student_name_en', '').title() if student.get('student_name_en', '') else '',
                'gender': gender_mapping.get(student.get('gender', ''), 'Male'),
                'group': group_mapping.get(student.get('group', ''), ''),
                'phone': student.get('student_phone', '')
            }
            
            return jsonify({
                'found': True,
                'student': student_data,
                'image_url': f'/api/student-image/{roll}'
            })
        else:
            return jsonify({
                'found': False,
                'error': 'Student not found',
                'image_url': '/api/student-image/placeholder'
            })
            
    except Exception as e:
        return jsonify({
            'found': False,
            'error': f'Error reading student data: {str(e)}',
            'image_url': '/api/student-image/placeholder'
        })


@app.route('/api/student-image/<roll>')
def api_student_image(roll):
    """API endpoint to serve student images.
    
    Serves images from ../college-students/images/{roll}.jpg
    Falls back to placeholder image if not found.
    """
    from flask import send_file, abort
    
    # Path to the images directory (relative to parent directory)
    images_dir = Path(__file__).parent.parent / 'college-students' / 'images'
    
    if roll == 'placeholder':
        image_path = images_dir / 'placeholder.jpg'
    else:
        image_path = images_dir / f'{roll}.jpg'
    
    # Fallback to placeholder if specific image doesn't exist
    if not image_path.exists():
        image_path = images_dir / 'placeholder.jpg'
    
    # If even placeholder doesn't exist, return 404
    if not image_path.exists():
        abort(404)
    
    return send_file(image_path, mimetype='image/jpeg')


@app.route('/push-github', methods=['POST'])
def push_github():
    """Trigger a git add/commit/push from the web UI.

    Security:
    - Requires environment variable ENABLE_GIT_PUSH=1 to be set on the server.
    - Optionally accepts a commit message in the request body as JSON or form field `message`.
    """
    # Feature toggle
    if not os.environ.get('DISABLE_GIT_PUSH', '0') != '1':
        return jsonify({'success': False, 'error': 'Git push via web is disabled on this server.'}), 403
    data = {}
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    # Fallback to form data
    if not data:
        data = request.form or {}

    commit_message = data.get('message') or f"Auto commit via web UI @ {datetime.now().isoformat()}"

    repo_dir = Path(__file__).parent.parent / 'verify'
    def run_cmd(cmd):
        try:
            if isinstance(cmd, str):
                completed = subprocess.run(cmd, cwd=repo_dir, shell=True, capture_output=True, text=True)
            else:
                completed = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
            return {
                'returncode': completed.returncode,
                'stdout': completed.stdout.strip(),
                'stderr': completed.stderr.strip()
            }
        except FileNotFoundError as e:
            return {'returncode': 127, 'stdout': '', 'stderr': str(e)}
        except Exception as e:
            return {'returncode': 1, 'stdout': '', 'stderr': str(e)}

    # Stage everything
    add_res = run_cmd(['git', 'add', '-A'])

    # Commit
    commit_res = run_cmd(['git', 'commit', '-m', commit_message])
    # If there's nothing to commit, git returns non-zero and mentions 'nothing to commit'
    commit_done = False
    if commit_res['returncode'] == 0:
        commit_done = True

    # Push
    push_res = run_cmd(['git', 'push'])

    success = (push_res.get('returncode', 1) == 0)

    response = {
        'success': success,
        'commit_done': commit_done,
        'add': add_res,
        'commit': commit_res,
        'push': push_res
    }

    status_code = 200 if success or commit_done else 500
    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)