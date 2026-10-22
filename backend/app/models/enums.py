import enum


class EditLevel(str, enum.Enum):
    LIGHT = "light"
    TARGETED = "targeted"
    FROM_SCRATCH = "from_scratch"


class ParseStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkModePreference(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    OFFICE = "office"


class ApplicationStatus(str, enum.Enum):
    SAVED = "saved"
    APPLIED = "applied"
    HR_INTERVIEW = "hr_interview"
    TECHNICAL_INTERVIEW = "technical_interview"
    OFFER = "offer"
    REJECTED = "rejected"
    AWAITING_RESPONSE = "awaiting_response"
