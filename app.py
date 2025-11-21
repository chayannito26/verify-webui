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

# Ticket book structures: list of (start, end) inclusive ranges per (group, gender)
# These define logical books of registration IDs; a book is "started" once any
# ID within its range is assigned. For each started book that still has vacancy
# we expose the first gap (lowest unused number) within that book as a quick-select
# option. Additionally, if no books have started yet, we expose the first gap of
# the first book (normally its first number).
BOOK_STRUCTURES = {
    ('SC', 'Male'): [(1, 50), (51, 100), (101, 150)],
    ('SC', 'Female'): [(1, 50)],
    ('AR', 'Male'): [(1, 50), (51, 100), (101, 150)],
    ('AR', 'Female'): [(1, 50), (51, 100)],
    ('CO', 'Male'): [(1, 50), (51, 100), (101, 150)],
    ('CO', 'Female'): [(1, 35), (36, 50)],
}

# IDs that should be treated as unavailable/missing and therefore skipped
# when suggesting the next registration id. Use uppercase values for
# case-insensitive matching.
MISSING_COUPONS = {
    'SC-B-0051'
}

# T-shirt size options (keep consistent across UI)
TSHIRT_SIZES = ['M','L','XL','XXL','3XL','4XL']

# Client mappings for revenue tracking
CLIENT_MAPPINGS = {
    'SC': {  # Science
        'Male': 'Arian Mollik Wasi',
        'Female': 'Marzia Mittika'
    },
    'AR': {  # Arts
        'Male': 'Sahariar Nafiz',
        'Female': 'S Shanta'
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

def get_default_clients(group: str, gender: str):
    """Return default client list for a given group and gender."""
    try:
        client_name = CLIENT_MAPPINGS.get(group, {}).get(gender)
        return [client_name] if client_name else []
    except Exception:
        return []

def add_revenue_entry(name, group, gender, registration_date, amount=None, clients=None):
    """Add a revenue entry for a new registration.

    Args:
        name (str): Registrant name.
        group (str): Group code (e.g., AR/SC/CO).
        gender (str): Gender label (Male/Female).
        registration_date (str): ISO date string (YYYY-MM-DD).
        amount (int|None): Collected amount. If None, defaults to 1200.
        clients (list[str]|None): List of client names to attribute revenue to. If None/empty, defaults by mapping.
    """
    try:
        revenues = load_revenues()
        
        # Determine clients list
        clients_list = []
        if clients:
            try:
                # normalize provided clients list (strip empties)
                clients_list = [c.strip() for c in clients if isinstance(c, str) and c.strip()]
            except Exception:
                clients_list = []
        if not clients_list:
            # fall back to default mapping
            default_clients = get_default_clients(group, gender)
            clients_list = default_clients if default_clients else ['Unknown Client']
        
        # Create revenue entry
        revenue_entry = {
            "id": int(datetime.now().timestamp() * 1000),  # timestamp in milliseconds
            "source": "Registration Fee",
            # Use provided amount if given; fall back to 1200 as a default
            "amount": int(amount) if amount is not None else 1200,
            "date": registration_date,
            "type": "Registration",
            "clients": clients_list,
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

def find_latest_registration_revenue_by_name(name: str):
    """Find the most recent registration revenue entry by matching comments==name.

    Returns the entry dict and its index in the list, or (None, None) if not found.
    """
    try:
        revenues = load_revenues()
        candidates = []
        for idx, entry in enumerate(revenues):
            try:
                if entry.get('type') == 'Registration' and entry.get('comments') == name:
                    candidates.append((idx, entry))
            except Exception:
                continue
        if not candidates:
            return None, None
        # choose by max id if present, else latest by date string
        try:
            picked = max(candidates, key=lambda p: p[1].get('id', 0))
        except Exception:
            try:
                picked = max(candidates, key=lambda p: p[1].get('date', ''))
            except Exception:
                picked = candidates[-1]
        return picked[1], picked[0]
    except Exception:
        return None, None

def update_revenue_clients_for_name(current_name: str, new_name: str, clients: list[str]):
    """Update clients (and optionally comments/name) for the latest registration revenue entry.

    Returns True if an entry was updated and saved, False otherwise.
    """
    try:
        revenues = load_revenues()
        entry, idx = find_latest_registration_revenue_by_name(current_name)
        if entry is None or idx is None:
            # Try matching by new_name if current_name not found
            entry, idx = find_latest_registration_revenue_by_name(new_name)
        if entry is None or idx is None:
            return False
        # Normalize clients list
        clean_clients = [c.strip() for c in (clients or []) if isinstance(c, str) and c.strip()]
        if not clean_clients:
            return False
        entry['clients'] = clean_clients
        # Keep comments aligned with current registrant name if changed
        if new_name and entry.get('comments') != new_name:
            entry['comments'] = new_name
        revenues[idx] = entry
        return save_revenues(revenues)
    except Exception as e:
        print(f'Error updating revenue clients: {str(e)}')
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
            try:
                iid_up = iid.upper()
                pref_up = prefix.upper()
                if iid_up.startswith(pref_up):
                    n = int(iid_up.split('-')[-1])
                    taken.add(n)
            except Exception:
                continue

    # Also treat any globally configured missing coupons as taken so they
    # are not suggested as next IDs. This allows skipping IDs like SC-B-0051
    # which correspond to missing/non-existent coupons.
    try:
        for missing in MISSING_COUPONS:
            if not isinstance(missing, str):
                continue
            m_up = missing.upper()
            pref_up = prefix.upper()
            if m_up.startswith(pref_up):
                try:
                    n = int(m_up.split('-')[-1])
                    taken.add(n)
                except Exception:
                    continue
    except Exception:
        # Defensive: if MISSING_COUPONS is malformed, ignore and proceed
        pass

    # Find the smallest positive integer not in taken (first gap)
    next_number = 1
    while next_number in taken:
        next_number += 1

    return f"{prefix}{next_number:04d}"

def compute_vacant_registration_ids(group: str, gender: str):
    """Compute quick-select vacant registration IDs across ticket books.

    Logic:
      - For each defined book (start-end) for (group, gender):
          * Determine which numbers in that range are already taken.
          * If any number in the range is taken (book started) and there is vacancy,
            expose the first gap (lowest unused number in that range) as an option.
      - If no book has started yet (no taken numbers across all ranges), expose the
        first gap of the first book only (normally start number).
      - next_id is the first option (numerically smallest) if options exist, else
        falls back to global next gap using existing logic.

    Returns dict:
      {
        'next_id': 'SC-B-0001',
        'options': ['SC-B-0004','SC-B-0052'],
        'books': [
           {'range': [1,50], 'started': True, 'vacancy': True, 'first_gap': 4},
           {'range': [51,100], 'started': True, 'vacancy': True, 'first_gap': 52},
           ...
        ]
      }
    """
    if (group, gender) not in BOOK_STRUCTURES:
        # Fallback: single option based on global next gap
        fallback = get_next_registration_id(group, gender)
        return {'next_id': fallback, 'options': [fallback], 'books': []}

    registrants = load_registrants()
    gender_short = GENDER_INFO[gender]['short']
    prefix = f"{group}-{gender_short}-"

    # Collect taken numeric portions for this prefix
    taken_numbers = set()
    for reg in registrants:
        reg_id = reg.get('registration_id', '')
        if reg_id.startswith(prefix):
            try:
                num = int(reg_id.split('-')[-1])
                taken_numbers.add(num)
            except Exception:
                continue

    # Treat globally missing coupons as taken for this prefix as well
    try:
        for missing in MISSING_COUPONS:
            if not isinstance(missing, str):
                continue
            m_up = missing.upper()
            pref_up = prefix.upper()
            if m_up.startswith(pref_up):
                try:
                    num = int(m_up.split('-')[-1])
                    taken_numbers.add(num)
                except Exception:
                    continue
    except Exception:
        # If MISSING_COUPONS is malformed, ignore and continue
        pass

    book_defs = BOOK_STRUCTURES[(group, gender)]
    books_meta = []
    options = []
    any_started = False

    for (start, end) in book_defs:
        # Numbers in this book
        nums_in_book = {n for n in taken_numbers if start <= n <= end}
        started = len(nums_in_book) > 0
        first_gap = None
        vacancy = False
        if started:
            any_started = True
            # Find lowest number in range not taken
            for candidate in range(start, end + 1):
                if candidate not in nums_in_book:
                    first_gap = candidate
                    vacancy = True
                    break
            # If vacancy add option
            if vacancy and first_gap is not None:
                options.append(f"{prefix}{first_gap:04d}")
        books_meta.append({
            'range': [start, end],
            'started': started,
            'vacancy': vacancy,
            'first_gap': first_gap
        })

    # If no books started yet, surface first gap for the first book only
    if not any_started:
        start, end = book_defs[0]
        # compute first gap in first book (lowest unused number globally inside range)
        for candidate in range(start, end + 1):
            if candidate not in taken_numbers:
                options = [f"{prefix}{candidate:04d}"]
                # update meta for first book
                if books_meta:
                    books_meta[0]['started'] = False
                    books_meta[0]['vacancy'] = True
                    books_meta[0]['first_gap'] = candidate
                break

    # Determine next_id precedence
    next_id = None
    if options:
        # Choose numerically smallest option
        try:
            next_id = min(options, key=lambda rid: int(rid.split('-')[-1]))
        except Exception:
            next_id = options[0]
    else:
        next_id = get_next_registration_id(group, gender)

    # Sort options numerically for presentation consistency
    try:
        options.sort(key=lambda rid: int(rid.split('-')[-1]))
    except Exception:
        pass

    return {
        'next_id': next_id,
        'options': options,
        'books': books_meta
    }

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

        # Ensure roll number uniqueness (prevent duplicate people)
        if roll:
            if any(r.get('roll') == roll for r in registrants):
                roll_error = f'Roll {roll} is already registered. Please check before adding.'
                flash(roll_error, 'error')
                return render_template('add_registrant.html',
                                     GROUP_INFO=GROUP_INFO,
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     form_data=request.form,
                                     roll_error=roll_error)

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
                # Return the form with a field-specific error so the template can show an inline warning
                registration_id_error = f'Registration ID {provided_id} is already in use. Please choose a different ID.'
                flash(registration_id_error, 'error')
                return render_template('add_registrant.html', 
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     TSHIRT_SIZES=TSHIRT_SIZES,
                                     form_data=request.form,
                                     registration_id_error=registration_id_error)
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
            # Determine clients override from form (comma-separated)
            clients_raw = request.form.get('revenue_clients', '')
            clients_list = [c.strip() for c in clients_raw.split(',')] if clients_raw else []
            # Add revenue entry with the actual paid amount and chosen clients (save to disk immediately).
            # Do NOT auto-push here; pushing should only happen when the user clicks the Push-to-GitHub button.
            add_revenue_entry(name, group, gender, registration_date_iso, amount=paid, clients=clients_list)
            
            flash(f'Successfully added {name} with ID {registration_id}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to save registrant. Please try again.', 'error')
    
    return render_template('add_registrant.html', 
                         GROUP_INFO=GROUP_INFO, 
                         GENDER_INFO=GENDER_INFO,
                         TSHIRT_SIZES=TSHIRT_SIZES,
                         CLIENT_MAPPINGS=CLIENT_MAPPINGS)


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


@app.route('/api/check_registration_id')
def api_check_registration_id():
    """Check if a given registration_id already exists.

    Query params: registration_id
    Response JSON: { "exists": true|false }
    """
    reg_id = request.args.get('registration_id', '').strip()
    if not reg_id:
        return jsonify({'error': 'missing registration_id'}), 400
    registrants = load_registrants()
    exists = any(r.get('registration_id') == reg_id for r in registrants)
    return jsonify({'exists': bool(exists)})


@app.route('/api/check_roll')
def api_check_roll():
    """Check if a given roll is already registered.

    Query params: roll
    Response JSON: { "exists": true|false }
    """
    roll = request.args.get('roll', '').strip()
    if not roll:
        return jsonify({'error': 'missing roll'}), 400
    registrants = load_registrants()
    exists = any(r.get('roll') == roll for r in registrants)
    return jsonify({'exists': bool(exists)})

@app.route('/api/vacant_registration_ids')
def api_vacant_registration_ids():
        """Return quick-select vacant registration IDs across ticket books.

        Query params: group, gender
        Response JSON:
            {
                "next_id": "SC-B-0004",           # preferred autofill suggestion
                "options": ["SC-B-0004", "SC-B-0052"],  # list of selectable vacant IDs
                "books": [
                     {"range": [1,50], "started": true, "vacancy": true, "first_gap": 4},
                     {"range": [51,100], "started": true, "vacancy": true, "first_gap": 52}
                ]
            }
        """
        group = request.args.get('group')
        gender = request.args.get('gender')
        if not group or not gender:
                return jsonify({'error': 'missing group or gender'}), 400
        try:
                result = compute_vacant_registration_ids(group, gender)
        except Exception as e:
                return jsonify({'error': str(e)}), 400
        return jsonify(result)

@app.route('/api/referrals')
def api_referrals():
    """Autocomplete data source for the "Referred By" field.

    Query params:
      - q: search string; can be part of registration_id or name (case-insensitive)
      - limit: optional int, max number of results (default 20, capped at 50)

    Response JSON:
      {
        "items": [
          {
            "registration_id": "AR-B-0001",
            "name": "John Doe",
            "group": "AR",
            "gender": "Male",
            "label": "AR-B-0001 — John Doe 🎨 🔵"
          }
        ]
      }
    """
    q = (request.args.get('q') or '').strip()
    try:
        limit = int(request.args.get('limit', '20'))
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 50))

    registrants = load_registrants()

    # If empty query, return most recent up to limit (by registration_date if present)
    if not q:
        # Try to sort by registration_id (lexicographic) as an approximation of recency
        try:
            sorted_regs = sorted(
                registrants,
                key=lambda r: r.get('registration_id', '') or ''
            )
        except Exception:
            sorted_regs = registrants
        matched = list(reversed(sorted_regs))[:limit]
    else:
        q_lower = q.lower()
        def matches(r):
            try:
                rid = (r.get('registration_id') or '').lower()
                name = (r.get('name') or '').lower()
                return q_lower in rid or q_lower in name
            except Exception:
                return False
        filtered = [r for r in registrants if matches(r)]
        # Return up to limit; prefer items where reg_id startswith query, then name contains
        def sort_key(r):
            rid = (r.get('registration_id') or '').lower()
            name = (r.get('name') or '').lower()
            return (
                0 if rid.startswith(q_lower) else 1,
                rid,
                name
            )
        try:
            filtered.sort(key=sort_key)
        except Exception:
            pass
        matched = filtered[:limit]

    items = []
    for r in matched:
        rid = r.get('registration_id') or ''
        name = r.get('name') or ''
        group = r.get('group') or ''
        gender = r.get('gender') or ''
        grp_emoji = GROUP_INFO.get(group, {}).get('emoji', '')
        gen_dot = GENDER_INFO.get(gender, {}).get('dot', '')
        label = f"{rid} — {name} {grp_emoji} {gen_dot}".strip()
        items.append({
            'registration_id': rid,
            'name': name,
            'group': group,
            'gender': gender,
            'label': label
        })

    return jsonify({'items': items})

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
        old_name = registrant.get('name', '')
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
            # Update revenue clients if provided
            try:
                clients_raw = request.form.get('revenue_clients', '')
                clients_list = [c.strip() for c in clients_raw.split(',')] if clients_raw else []
                if clients_list:
                    update_revenue_clients_for_name(old_name, registrant['name'], clients_list)
            except Exception as e:
                print(f"Warning: couldn't update revenue clients: {e}")
            flash(f'Successfully updated {registrant["name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to save changes. Please try again.', 'error')
    
    # Prefill revenue clients from revenues.json if present, else default mapping
    prefill_clients = []
    try:
        entry, _ = find_latest_registration_revenue_by_name(registrant.get('name', ''))
        if entry and isinstance(entry.get('clients'), list):
            prefill_clients = [c for c in entry.get('clients') if isinstance(c, str)]
    except Exception:
        prefill_clients = []
    if not prefill_clients:
        prefill_clients = get_default_clients(registrant.get('group'), registrant.get('gender'))

    return render_template('edit_registrant.html', 
                         registrant=registrant,
                         GROUP_INFO=GROUP_INFO, 
                         GENDER_INFO=GENDER_INFO,
                         TSHIRT_SIZES=TSHIRT_SIZES,
                         CLIENT_MAPPINGS=CLIENT_MAPPINGS,
                         revenue_clients=", ".join(prefill_clients),
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
                    # Revenues file saved to disk. Do NOT auto-push here; leave pushing
                    # to the manual "Push to GitHub" action.
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


@app.route('/statistics')
def statistics():
    """Display comprehensive statistics page."""
    from collections import Counter
    
    registrants = load_registrants()
    grouped = group_registrants(registrants)
    
    # Basic statistics
    total = len(registrants)
    active = len([r for r in registrants if not r.get('revoked', False)])
    revoked = len([r for r in registrants if r.get('revoked', False)])
    
    # Payment statistics
    payments = [r.get('paid', 0) for r in registrants if not r.get('revoked', False)]
    total_payments = sum(payments)
    average_payment = total_payments / active if active > 0 else 0
    min_payment = min(payments) if payments else 0
    max_payment = max(payments) if payments else 0
    
    # Payment by group
    payment_by_group = {}
    for group in GROUP_INFO.keys():
        group_payments = sum(r.get('paid', 0) for r in registrants 
                            if r.get('group') == group and not r.get('revoked', False))
        payment_by_group[group] = group_payments
    
    # Payment distribution (how many people paid each amount)
    payment_distribution = Counter()
    for r in registrants:
        if not r.get('revoked', False):
            amount = r.get('paid', 0)
            if amount > 0:
                payment_distribution[amount] += 1
    
    # Sort payment distribution by amount
    payment_distribution = dict(sorted(payment_distribution.items()))
    
    # Group statistics
    groups_stats = {}
    for group, genders in grouped.items():
        groups_stats[group] = {
            'total': sum(len(regs) for regs in genders.values()),
            'genders': {gender: len(regs) for gender, regs in genders.items()}
        }
    
    # Gender distribution
    gender_distribution = Counter(r.get('gender') for r in registrants)
    
    # T-shirt size distribution
    tshirt_sizes = Counter()
    total_with_tshirt = 0
    for r in registrants:
        if 'T-Shirt' in r.get('parts_available', []) and r.get('tshirt_size'):
            tshirt_sizes[r['tshirt_size']] += 1
            total_with_tshirt += 1
    
    # Sort t-shirt sizes in standard order
    size_order = ['S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL']
    tshirt_sizes_ordered = {size: tshirt_sizes[size] for size in size_order if size in tshirt_sizes}
    
    # Parts availability distribution
    parts_distribution = Counter()
    for r in registrants:
        for part in r.get('parts_available', []):
            parts_distribution[part] += 1
    
    # Registration timeline
    from datetime import datetime
    registration_timeline = Counter()
    date_objects = {}  # Map date string to datetime object for sorting
    
    for r in registrants:
        date_str = r.get('registration_date', 'Unknown')
        registration_timeline[date_str] += 1
        
        # Try to parse the date for proper sorting
        if date_str != 'Unknown':
            try:
                # Parse dates like "17 August 2025"
                date_obj = datetime.strptime(date_str, '%d %B %Y')
                date_objects[date_str] = date_obj
            except ValueError:
                try:
                    # Try alternative formats
                    date_obj = datetime.strptime(date_str, '%d %b %Y')
                    date_objects[date_str] = date_obj
                except ValueError:
                    # If parsing fails, use a default old date
                    date_objects[date_str] = datetime(1900, 1, 1)
    
    # Sort timeline by actual date objects (chronologically)
    registration_timeline = dict(sorted(
        registration_timeline.items(),
        key=lambda x: date_objects.get(x[0], datetime(1900, 1, 1))
    ))
    max_registrations_per_day = max(registration_timeline.values()) if registration_timeline else 1
    
    # Group timeline by month for better visualization
    monthly_timeline = Counter()
    for date_str, count in registration_timeline.items():
        if date_str in date_objects:
            month_year = date_objects[date_str].strftime('%B %Y')
            monthly_timeline[month_year] += count
    
    # Sort monthly timeline chronologically
    monthly_timeline = dict(sorted(
        monthly_timeline.items(),
        key=lambda x: datetime.strptime(x[0], '%B %Y')
    ))
    
    # Generate calendar data for calendar view
    import calendar
    calendar_data = []
    
    # Set first day of week to Sunday (6 = Sunday in Python's calendar module)
    calendar.setfirstweekday(calendar.SUNDAY)
    
    if date_objects:
        # Get the range of dates
        all_dates = [d for d in date_objects.values() if d.year > 1900]
        if all_dates:
            min_date = min(all_dates)
            max_date = max(all_dates)
            
            # Generate calendar for each month in the range
            current_date = datetime(min_date.year, min_date.month, 1)
            end_date = datetime(max_date.year, max_date.month, 1)
            
            while current_date <= end_date:
                month_name = current_date.strftime('%B %Y')
                year = current_date.year
                month = current_date.month
                
                # Get calendar matrix for the month (weeks x days)
                cal = calendar.monthcalendar(year, month)
                
                # Build the calendar data with registration counts
                month_calendar = {
                    'month_year': month_name,
                    'year': year,
                    'month': month,
                    'weeks': []
                }
                
                for week in cal:
                    week_data = []
                    for day in week:
                        if day == 0:
                            week_data.append({'day': 0, 'count': 0})
                        else:
                            # Check if there are registrations on this day
                            # Try both with and without leading zero for single-digit days
                            day_date = datetime(year, month, day)
                            
                            # Format without leading zero (portable way)
                            day_str_no_zero = f"{day} {day_date.strftime('%B %Y')}"
                            # Format with leading zero
                            day_str_with_zero = day_date.strftime('%d %B %Y')
                            
                            # Try to find count with either format
                            count = registration_timeline.get(day_str_no_zero, 0)
                            if count == 0 and day_str_with_zero != day_str_no_zero:
                                count = registration_timeline.get(day_str_with_zero, 0)
                            
                            week_data.append({'day': day, 'count': count})
                    month_calendar['weeks'].append(week_data)
                
                calendar_data.append(month_calendar)
                
                # Move to next month
                if month == 12:
                    current_date = datetime(year + 1, 1, 1)
                else:
                    current_date = datetime(year, month + 1, 1)
    
    # Referral statistics
    total_referred = sum(1 for r in registrants if r.get('referred_by'))
    self_registrations = total - total_referred
    
    # Top referrers
    referral_counts = Counter()
    referrer_map = {r.get('registration_id'): r for r in registrants}
    
    for r in registrants:
        referred_by = r.get('referred_by', '').strip()
        if referred_by:
            referral_counts[referred_by] += 1
    
    top_referrers = []
    for ref_id, count in referral_counts.most_common(10):
        referrer = referrer_map.get(ref_id)
        if referrer:
            top_referrers.append({
                'registration_id': ref_id,
                'name': referrer.get('name', 'Unknown'),
                'count': count
            })
    
    # Key insights
    most_popular_group = max(groups_stats.items(), key=lambda x: x[1]['total'])[0] if groups_stats else 'N/A'
    most_popular_group_name = GROUP_INFO[most_popular_group]['name'] if most_popular_group in GROUP_INFO else 'N/A'
    
    most_popular_tshirt_size = tshirt_sizes.most_common(1)[0][0] if tshirt_sizes else None
    
    peak_registration_day = max(registration_timeline.items(), key=lambda x: x[1])[0] if registration_timeline else None
    
    stats = {
        'total': total,
        'active': active,
        'revoked': revoked,
        'total_payments': total_payments,
        'average_payment': average_payment,
        'min_payment': min_payment,
        'max_payment': max_payment,
        'payment_by_group': payment_by_group,
        'payment_distribution': payment_distribution,
        'groups': groups_stats,
        'gender_distribution': dict(gender_distribution),
        'tshirt_sizes': tshirt_sizes_ordered,
        'total_with_tshirt': total_with_tshirt,
        'parts_distribution': dict(parts_distribution),
        'registration_timeline': registration_timeline,
        'monthly_timeline': monthly_timeline,
        'calendar_data': calendar_data,
        'max_registrations_per_day': max_registrations_per_day,
        'total_referred': total_referred,
        'self_registrations': self_registrations,
        'top_referrers': top_referrers,
        'most_popular_group': most_popular_group_name,
        'most_popular_tshirt_size': most_popular_tshirt_size,
        'peak_registration_day': peak_registration_day
    }
    
    return render_template(
        'statistics.html',
        stats=stats,
        GROUP_INFO=GROUP_INFO,
        GENDER_INFO=GENDER_INFO
    )


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

    # Helper to run git operations in a repo directory
    def run_git_ops(repo_dir: Path, message: str):
        repo_dir = Path(repo_dir)
        result = {
            'repo': str(repo_dir),
            'add': None,
            'commit': None,
            'push': None,
            'success': False
        }

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

        # Ensure directory exists
        if not repo_dir.exists():
            result['add'] = {'returncode': 127, 'stdout': '', 'stderr': 'repo directory not found'}
            return result

        result['add'] = run_cmd(['git', 'add', '-A'])
        result['commit'] = run_cmd(['git', 'commit', '-m', message])
        result['push'] = run_cmd(['git', 'push'])

        # Consider success when push returncode is 0, or commit was done (0) even if push failed
        result['success'] = (result['push'].get('returncode', 1) == 0) or (result['commit'].get('returncode', 1) == 0)
        return result

    # Repos to push: verify (main site data) and income (revenues file)
    base_dir = Path(__file__).parent.parent
    verify_repo = base_dir / 'verify'
    income_repo = base_dir / 'income'

    verify_res = run_git_ops(verify_repo, commit_message)
    income_res = run_git_ops(income_repo, commit_message)

    overall_success = verify_res.get('success', False) or income_res.get('success', False)

    response = {
        'success': overall_success,
        'verify': verify_res,
        'income': income_res
    }

    status_code = 200 if overall_success else 500
    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)