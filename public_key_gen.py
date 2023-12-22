import requests
from jwcrypto import jwk
import json
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials

def initialize_jwks_cache(filename):
    jwks_uri = r'https://login.microsoftonline.com/common/discovery/v2.0/keys'
    response = requests.get(jwks_uri)
    if response.status_code == 200:
        jwks_data = response.json()
        with open(filename, 'w') as file:
            json.dump(jwks_data, file, indent=4)
        return jwks_data
    else:
        raise HTTPException(status_code=500, detail=f"Failed to fetch JWKS: HTTP {response.status_code}")

