from .reference.medical_reference import MedicalKB

# Module-level singleton — import this across the app
kb = MedicalKB()

__all__ = ["kb", "MedicalKB"]
