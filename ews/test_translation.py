
import frappe
from frappe import _

def tested():
    print(f"Translating 'Details' to ar: {_('Details', lang='ar')}")
    print(f"Translating 'Severity' to ar: {_('Severity', lang='ar')}")
    # Check if a dummy string not in system but maybe in DB works, or just check standard behavior
    # We can't easily check DB content without knowing what's there, but we can check if it returns Arabic.

tested()
