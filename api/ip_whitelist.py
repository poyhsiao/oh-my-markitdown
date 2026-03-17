"""
IP Whitelist Middleware for Admin Endpoints

Provides CIDR-based IP whitelist functionality for restricting access to admin endpoints.
Supports both IPv4 and IPv6 CIDR notation.
"""

import os
import ipaddress
import logging
from typing import List, Optional, Set
from fastapi import Request, HTTPException, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict access to admin endpoints based on IP whitelist.
    
    Features:
    - Supports CIDR notation (e.g., 192.168.1.0/24, 10.0.0.0/8)
    - Supports both IPv4 and IPv6
    - Configurable via environment variables
    - Logs blocked requests for security monitoring
    - Disabled by default (all IPs allowed)
    
    Environment Variables:
    - ADMIN_IP_RESTRICTION_ENABLED: Enable/disable IP restriction (default: false)
    - ADMIN_ALLOWED_IPS: Comma-separated list of allowed IPs/CIDRs (default: empty)
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = self._parse_bool_env("ADMIN_IP_RESTRICTION_ENABLED", False)
        self.allowed_networks: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = set()
        
        if self.enabled:
            self._load_allowed_ips()
            logger.info(f"IP whitelist enabled with {len(self.allowed_networks)} network(s)")
        else:
            logger.info("IP whitelist disabled (all IPs allowed)")
    
    def _parse_bool_env(self, key: str, default: bool) -> bool:
        """Parse boolean environment variable."""
        value = os.getenv(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off", ""):
            return False
        return default
    
    def _load_allowed_ips(self) -> None:
        """Load and parse allowed IPs from environment variable."""
        ips_str = os.getenv("ADMIN_ALLOWED_IPS", "").strip()
        
        if not ips_str:
            logger.warning("ADMIN_IP_RESTRICTION_ENABLED is true but ADMIN_ALLOWED_IPS is empty")
            return
        
        # Parse comma-separated IPs/CIDRs
        for ip_str in ips_str.split(','):
            ip_str = ip_str.strip()
            if not ip_str:
                continue
            
            try:
                # Parse as network (supports both single IPs and CIDR)
                network = ipaddress.ip_network(ip_str, strict=False)
                self.allowed_networks.add(network)
                logger.debug(f"Added allowed network: {network}")
            except ValueError as e:
                logger.error(f"Invalid IP/CIDR '{ip_str}': {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.
        
        Priority:
        1. X-Forwarded-For header (first IP, for reverse proxy setups)
        2. client.host (direct connection)
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address as string
        """
        # Check X-Forwarded-For header (reverse proxy scenario)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
            # We use the first IP (original client)
            client_ip = forwarded_for.split(',')[0].strip()
            logger.debug(f"Client IP from X-Forwarded-For: {client_ip}")
            return client_ip
        
        # Fallback to direct connection
        client_ip = request.client.host if request.client else "unknown"
        logger.debug(f"Client IP from direct connection: {client_ip}")
        return client_ip
    
    def _is_ip_allowed(self, ip_str: str) -> bool:
        """
        Check if IP is in the allowed whitelist.
        
        Args:
            ip_str: IP address as string
            
        Returns:
            True if IP is allowed, False otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            
            # Check against all allowed networks
            for network in self.allowed_networks:
                if ip in network:
                    logger.debug(f"IP {ip} allowed by network {network}")
                    return True
            
            logger.debug(f"IP {ip} not in whitelist")
            return False
            
        except ValueError as e:
            logger.error(f"Invalid IP address '{ip_str}': {e}")
            return False
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and check IP whitelist for admin endpoints.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler
            
        Returns:
            Response from next handler or 403 if IP not allowed
        """
        # Only check admin endpoints
        if not request.url.path.startswith("/api/v1/admin/"):
            return await call_next(request)
        
        # If IP restriction is disabled, allow all
        if not self.enabled:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check if IP is allowed
        if self._is_ip_allowed(client_ip):
            return await call_next(request)
        
        # IP not allowed - log and return 403
        logger.warning(
            f"Blocked request from IP {client_ip} to {request.url.path} "
            f"({request.method} {request.url.path})"
        )
        
        # Import here to avoid circular dependency
        from .response import error_response, ErrorCodes
        
        return Response(
            content=str(error_response(
                code=ErrorCodes.IP_NOT_ALLOWED,
                message="Access denied: IP address not in whitelist"
            )),
            status_code=403,
            media_type="application/json"
        )
