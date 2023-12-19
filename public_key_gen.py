import requests
from jwcrypto import jwk
import json

# Ask the user for the JWKS URI
jwks_uri = input("Enter the JWKS URI: ")

# Fetch the JWKS from the provided URI
response = requests.get(jwks_uri)
if response.status_code == 200:
    jwks_json = response.json()
else:
    print(f"Failed to fetch JWKS: HTTP {response.status_code}")
    exit(1)

# Ask for the Key ID (kid) to match
desired_kid = input("Enter the 'kid' of the key to find: ")

# Find the key with the matching 'kid'
matching_key_data = next((key for key in jwks_json['keys'] if key['kid'] == desired_kid), None)

if matching_key_data:
    # Convert the matching JWK to a JWK object
    key = jwk.JWK(**matching_key_data)

    # Get the public key in PEM format
    public_key_pem = key.export_to_pem()

    # Write the PEM key to a file, overwriting the existing file
    with open('public_key.pem', 'wb') as pem_file:
        pem_file.write(public_key_pem)

    print("Public key updated in public_key.pem for 'kid':", desired_kid)
else:
    print(f"No key found with 'kid': {desired_kid}")
