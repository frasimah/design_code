"""
JWT/JWE Authentication middleware for FastAPI.
Verifies NextAuth.js encrypted JWT tokens (JWE) and extracts user information.

NextAuth v4+ uses JWE with:
- Algorithm: dir (direct encryption)
- Encryption: A256GCM
- Key derivation: HKDF with SHA256
"""

from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os
import json

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from jwcrypto import jwe
from jwcrypto.common import base64url_decode
from config.settings import NEXTAUTH_SECRET

security = HTTPBearer(auto_error=False)


def _derive_encryption_key(secret: str) -> bytes:
    """
    Derive the encryption key from NEXTAUTH_SECRET using HKDF.
    This replicates what NextAuth.js does internally.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for A256GCM
        salt=b"",
        info=b"NextAuth.js Generated Encryption Key",
    )
    return hkdf.derive(secret.encode("utf-8"))


def _decrypt_nextauth_token(token: str) -> Optional[dict]:
    """
    Decrypt a NextAuth.js JWE token and return the payload.
    """
    try:
        import base64
        # Derive the key
        if NEXTAUTH_SECRET == "development-secret-please-change-in-production":
            print("[JWT DEBUG] WARNING: Using default NEXTAUTH_SECRET. Decryption will fail if production token is used.")
            
        key_bytes = _derive_encryption_key(NEXTAUTH_SECRET)
        
        # Create JWK from the derived key - proper base64url encoding
        from jwcrypto.jwk import JWK
        k_encoded = base64.urlsafe_b64encode(key_bytes).rstrip(b'=').decode('ascii')
        key = JWK(kty="oct", k=k_encoded)
        
        # Decrypt the JWE
        jwetoken = jwe.JWE()
        jwetoken.deserialize(token)
        jwetoken.decrypt(key)
        
        # Parse the payload
        payload = json.loads(jwetoken.payload.decode('utf-8'))
        return payload
    except Exception as e:
        # Don't print the token itself for security, but print the error
        print(f"[JWT DEBUG] JWE decryption failed. Error: {str(e)}")
        if "Invalid JWK" in str(e):
             print("[JWT DEBUG] Possible cause: Incorrect NEXTAUTH_SECRET or key derivation failure.")
        return None


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[dict]:
    """
    Extract user from NextAuth JWT token (actually JWE).
    Returns None if no valid token present (allows unauthenticated access for some endpoints).
    """
    token = None
    
    # Debug log for investigation
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        print(f"[JWT DEBUG] No Authorization header in request to {request.url.path}. Headers: {dict(request.headers)}")
    
    # Try to get token from either source
    if credentials:
        token = credentials.credentials
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    
    # NEW: Try to get token from NextAuth cookies if header is missing
    # This is useful when the frontend is on the same domain and headers might be stripped
    if not token:
        # Check both secure and non-secure cookie names
        token = request.cookies.get("__Secure-next-auth.session-token") or \
                request.cookies.get("next-auth.session-token")
        if token:
            print(f"[JWT DEBUG] Found token in cookie for {request.url.path}")
    
    if not token:
        # Don't print "No token" for common GET requests to avoid log noise, 
        # but keep it for POST/PUT/DELETE which usually require auth
        if request.method != "GET":
            print(f"[JWT DEBUG] No token found in {request.method} request to {request.url.path}")
        return None
    
    # Decrypt the JWE token
    payload = _decrypt_nextauth_token(token)
    
    if not payload:
        return None
        
    user_info = {
        "id": payload.get("sub") or payload.get("userId"),
        "email": payload.get("email"),
        "name": payload.get("name"),
    }
    print(f"[JWT DEBUG] Token validated OK, user: {user_info}")
    return user_info


async def require_auth(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """
    Require authenticated user. Raises 401 if not authenticated.
    """
    if not user or not user.get("id"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def optional_auth(user: Optional[dict] = Depends(get_current_user)) -> Optional[dict]:
    """
    Optional authentication. Returns user if authenticated, None otherwise.
    """
    return user
