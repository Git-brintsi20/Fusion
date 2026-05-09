"""Compatibility shim.

Target architecture keeps serializers under hostel_management/api/serializers.py.
This module remains so older imports keep working.
"""

from .api.serializers import *  # noqa: F401,F403
