
import logging
from datetime import datetime, timezone


class CustomFormatter(logging.Formatter):
	"""Custom formatter for timestamp format: 20251206_17382200+09"""
	
	def formatTime(self, record, datefmt=None):
		# Get current time with timezone info
		ct = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone()
		
		# Format: YYYYMMDD_HHMMSSms+TZ
		timestamp = ct.strftime('%Y%m%d_%H%M%S')
		milliseconds = f"{int(record.msecs):02d}"  # Get centiseconds (00-99)
		tz_offset = ct.strftime('%z')  # Format: +0900 or -0500
		tz_offset = tz_offset[:3]  # Convert +0900 to +09
		
		return f"{timestamp}{milliseconds}{tz_offset}"
	
	def format(self, record):
		record.custom_time = self.formatTime(record)
		return super().format(record)


def setup_logging(level=logging.INFO):
	"""
	Configure logging with custom timestamp format.
	
	Args:
		level: Logging level (default: logging.INFO)
	"""
	handler = logging.StreamHandler()
	handler.setFormatter(CustomFormatter('%(custom_time)s - %(name)s - %(levelname)s - %(message)s'))
	logging.root.addHandler(handler)
	logging.root.setLevel(level)

