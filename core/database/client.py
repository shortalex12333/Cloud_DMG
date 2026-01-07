"""
Supabase database client initialization
"""
import os
from supabase import create_client, Client
from typing import Optional


class SupabaseClient:
    """Singleton Supabase client"""
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance.

        Reads credentials from environment variables:
        - SUPABASE_URL
        - SUPABASE_SERVICE_ROLE_KEY

        Returns:
            Configured Supabase client
        """
        if cls._instance is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if not url or not key:
                raise ValueError(
                    "Missing Supabase credentials. "
                    "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables."
                )

            cls._instance = create_client(url, key)

        return cls._instance


# Convenience function
def get_db() -> Client:
    """Get Supabase database client"""
    return SupabaseClient.get_client()
