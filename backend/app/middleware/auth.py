"""
Authentication and authorization middleware.
Integrates with Clerk for JWT validation.
"""

import jwt
import time
from typing import Optional, Dict, Any, Callable, List
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.config import get_settings


class AuthenticationError(HTTPException):
    """Raised when authentication fails"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": detail},
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Raised when authorization fails"""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": detail}
        )


class ClerkAuth:
    """
    Clerk authentication handler.
    Validates JWT tokens from Clerk.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._jwks: Optional[Dict] = None
        self._jwks_last_fetch: float = 0
    
    async def _get_jwks(self) -> Dict:
        """Fetch Clerk JWKS (caching)"""
        # Simple cache for 1 hour
        if self._jwks and (time.time() - self._jwks_last_fetch) < 3600:
            return self._jwks
        
        import httpx
        
        issuer = self._get_issuer()
        jwks_url = f"{issuer}/.well-known/jwks.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            self._jwks = response.json()
            self._jwks_last_fetch = time.time()
            return self._jwks
    
    def _get_issuer(self) -> str:
        """Get Clerk issuer URL"""
        # Extract from secret key or use configured URL
        if self.settings.clerk_secret_key:
            # Secret key format: sk_test_xxx or sk_live_xxx
            return f"https://clerk.{self.settings.clerk_secret_key.split('_')[2]}.com"
        return "https://clerk.your-domain.com"
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a Clerk JWT token.
        Returns decoded claims or raises AuthenticationError.
        """
        try:
            # Get unverified header to find key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise AuthenticationError("Invalid token format")
            
            # Get signing key
            jwks = await self._get_jwks()
            signing_key = None
            
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not signing_key:
                raise AuthenticationError("Invalid token signature")
            
            # Verify token
            issuer = self._get_issuer()
            decoded = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.settings.clerk_publishable_key or None,
                issuer=issuer
            )
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Authentication error: {str(e)}")


# Global auth instance
_auth_instance: Optional[ClerkAuth] = None


def get_auth() -> ClerkAuth:
    """Get or create auth instance"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = ClerkAuth()
    return _auth_instance


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to get current authenticated user.
    Returns None if no credentials provided.
    """
    if not credentials:
        return None
    
    auth = get_auth()
    return await auth.validate_token(credentials.credentials)


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> Dict[str, Any]:
    """
    FastAPI dependency to require authentication.
    Raises AuthenticationError if no valid credentials.
    """
    auth = get_auth()
    return await auth.validate_token(credentials.credentials)


class PermissionChecker:
    """
    Check user permissions.
    """
    
    def __init__(self, user: Dict[str, Any]):
        self.user = user
        self.user_id = user.get("sub")
        self.org_id = user.get("org_id")
        self.permissions = user.get("permissions", [])
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the permissions"""
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all permissions"""
        return all(p in self.permissions for p in permissions)
    
    def is_owner(self, resource_user_id: str) -> bool:
        """Check if user owns a resource"""
        return self.user_id == resource_user_id
    
    def check_permission(self, permission: str):
        """Raise error if permission not granted"""
        if not self.has_permission(permission):
            raise AuthorizationError(f"Missing permission: {permission}")


def require_permission(permission: str):
    """
    FastAPI dependency factory to require specific permission.
    Usage: @app.get("/admin", dependencies=[Depends(require_permission("admin"))])
    """
    async def checker(
        user: Dict[str, Any] = Depends(require_auth)
    ) -> Dict[str, Any]:
        checker_obj = PermissionChecker(user)
        checker_obj.check_permission(permission)
        return user
    return checker


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to authenticate requests and set user info on request state.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exempt_routes: Optional[List[str]] = None,
        require_auth_routes: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.exempt_routes = exempt_routes or [
            "/health", "/docs", "/openapi.json",
            "/api/public", "/webhooks"
        ]
        self.require_auth_routes = require_auth_routes or ["/api"]
        self.auth = get_auth()
    
    async def dispatch(self, request: Request, call_next):
        # Check if route is exempt
        is_exempt = any(
            request.url.path.startswith(route) 
            for route in self.exempt_routes
        )
        
        if is_exempt:
            return await call_next(request)
        
        # Skip auth if no Clerk key configured (dev/test mode)
        settings = get_settings()
        if not settings.clerk_secret_key or settings.clerk_secret_key == "sk_test_placeholder":
            # Set mock user for testing
            request.state.user = {"sub": "test-user", "org_id": "test-tenant"}
            request.state.user_id = "test-user"
            request.state.org_id = "test-tenant"
            return await call_next(request)
        
        # Check if route requires auth
        requires_auth = any(
            request.url.path.startswith(route) 
            for route in self.require_auth_routes
        )
        
        # Try to authenticate
        auth_header = request.headers.get("authorization", "")
        user = None
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                user = await self.auth.validate_token(token)
                request.state.user = user
                request.state.user_id = user.get("sub")
                request.state.org_id = user.get("org_id")
            except AuthenticationError:
                if requires_auth:
                    raise
        
        # Check if auth is required but not provided
        if requires_auth and user is None:
            raise AuthenticationError("Authentication required")
        
        response = await call_next(request)
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant ID.
    Ensures users can only access their tenant's data.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        tenant_header: str = "X-Tenant-ID",
        default_tenant: Optional[str] = None
    ):
        super().__init__(app)
        self.tenant_header = tenant_header
        self.default_tenant = default_tenant
    
    async def dispatch(self, request: Request, call_next):
        # Get tenant from header
        tenant_id = request.headers.get(self.tenant_header)
        
        # Fallback to default or user org
        if not tenant_id:
            tenant_id = getattr(request.state, 'org_id', None)
        
        if not tenant_id:
            tenant_id = self.default_tenant
        
        # Validate tenant access if user is authenticated
        user = getattr(request.state, 'user', None)
        if user and tenant_id:
            user_org = user.get("org_id")
            if user_org and user_org != tenant_id:
                # User trying to access different tenant
                # Check if they have cross-tenant permission
                permissions = user.get("permissions", [])
                if "cross_tenant_access" not in permissions:
                    raise AuthorizationError(
                        "Cannot access data from other tenants"
                    )
        
        request.state.tenant_id = tenant_id
        
        response = await call_next(request)
        return response
