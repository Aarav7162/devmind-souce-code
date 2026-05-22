import base64
import sys
from ecdsa import SigningKey, SECP256k1

PRIVATE_KEY_PEM = """-----BEGIN EC PRIVATE KEY-----
MHQCAQEEIM84uGQHZPcpQaGXsghP+DVFiGepdZAA48KZbX/6LzG3oAcGBSuBBAAK
oUQDQgAENx/a993l5w0DuVGQGAAb/Nc/xlwyHszDcYwm0X539ZhoVaObWpj6/1cf
WhFEsXTMg6gyXNg+Fw75pdSuAuftZw==
-----END EC PRIVATE KEY-----"""

def generate_pro_license(machine_id):
    """Generates an offline Pro license key bound to the client's unique Machine ID."""
    try:
        sk = SigningKey.from_pem(PRIVATE_KEY_PEM)
        payload = f"PRO_LICENSE:{machine_id}"
        sig = sk.sign(payload.encode('utf-8'))
        sig_b64 = base64.b64encode(sig).decode('utf-8')
        return f"DM-PRO-{sig_b64}"
    except Exception as e:
        print(f"Error generating license: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python devmind_admin.py <MACHINE_ID>")
        sys.exit(1)
        
    machine_id = sys.argv[1].strip()
    license_key = generate_pro_license(machine_id)
    if license_key:
        print("\n  ==================================================")
        print(f"  DevMind Pro License Key Generated:")
        print(f"  {license_key}")
        print("  ==================================================\n")
