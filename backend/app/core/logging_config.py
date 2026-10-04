import sys, re, os
from loguru import logger
from app.core.config import settings

SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(password["\s:=]+)[^\s,"\}]+'), r'\1***MASKED***'),
    (re.compile(r'(?i)(token["\s:=]+)[^\s,"\}]{8,}'), r'\1***MASKED***'),
    (re.compile(r'(?i)(secret["\s:=]+)[^\s,"\}]+'), r'\1***MASKED***'),
    (re.compile(r'(?i)(authorization:\s*bearer\s+)[\w.-]+'), r'\1***MASKED***'),
]

def mask_sensitive(message: str) -> str:
    if not settings.log_mask_sensitive:
        return message
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message

class SensitiveMaskingFilter:
    def __call__(self, record):
        record["message"] = mask_sensitive(record["message"])
        if record.get("extra"):
            for key in list(record["extra"].keys()):
                if isinstance(record["extra"][key], str):
                    record["extra"][key] = mask_sensitive(record["extra"][key])
        return True

def setup_logging():
    logger.remove()
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
    logger.add(sys.stdout, format=log_format, level=settings.log_level, filter=SensitiveMaskingFilter(), colorize=True)
    os.makedirs("logs", exist_ok=True)
    logger.add(settings.log_file, format=log_format, level=settings.log_level, filter=SensitiveMaskingFilter(), rotation="10 MB", retention="30 days", compression="zip")
    logger.info("Logging initialized. Sensitive masking: {}", settings.log_mask_sensitive)
