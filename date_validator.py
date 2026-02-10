"""
Date validation utilities for lease contracts
Handles validation of dates and date ranges in lease agreements
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import re
import calendar


class DateValidationError(Exception):
    """Custom exception for date validation errors"""
    pass


class DateValidator:
    """
    Validates dates and date ranges for lease contracts
    Ensures dates are valid, reasonable, and chronologically correct
    """
    
    # Common date formats to try parsing
    DATE_FORMATS = [
        "%d/%m/%Y",  # 23/02/2026
        "%d-%m-%Y",  # 23-02-2026
        "%Y/%m/%d",  # 2026/02/23
        "%Y-%m-%d",  # 2026-02-23
        "%d.%m.%Y",  # 23.02.2026
        "%-d/%-m/%Y",  # 2/2/2026 (single digit - Unix/Mac)
        "%#d/%#m/%Y",  # 2/2/2026 (single digit - Windows)
    ]
    
    # Arabic month names mapping
    ARABIC_MONTHS = {
        'يناير': 1, 'ينايר': 1,
        'فبراير': 2, 'شباط': 2,
        'مارس': 3, 'آذار': 3,
        'أبريل': 4, 'نيسان': 4, 'ابريل': 4,
        'مايو': 5, 'أيار': 5, 'ماي': 5,
        'يونيو': 6, 'حزيران': 6, 'يونيه': 6,
        'يوليو': 7, 'تموز': 7, 'يوليه': 7,
        'أغسطس': 8, 'آب': 8, 'اغسطس': 8,
        'سبتمبر': 9, 'أيلول': 9,
        'أكتوبر': 10, 'تشرين الأول': 10, 'اكتوبر': 10,
        'نوفمبر': 11, 'تشرين الثاني': 11,
        'ديسمبر': 12, 'كانون الأول': 12, 'دسمبر': 12
    }
    
    def __init__(self, reference_date: Optional[datetime] = None):
        """
        Initialize validator
        
        Args:
            reference_date: Reference date to use as "today" (default: actual today)
        """
        self.reference_date = reference_date or datetime.now()
    
    def is_leap_year(self, year: int) -> bool:
        """Check if a year is a leap year"""
        return calendar.isleap(year)
    
    def is_valid_date(self, day: int, month: int, year: int) -> bool:
        """
        Check if a date is valid (exists in calendar)
        
        Args:
            day: Day of month
            month: Month (1-12)
            year: Year
            
        Returns:
            True if date is valid
        """
        try:
            # Check basic ranges
            if not (1 <= month <= 12):
                return False
            
            # Get max days in month
            max_day = calendar.monthrange(year, month)[1]
            
            if not (1 <= day <= max_day):
                return False
            
            # Try to create the date to be absolutely sure
            datetime(year, month, day)
            return True
            
        except (ValueError, OverflowError):
            return False
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string in various formats (including Arabic)
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Datetime object or None if parsing fails
        """
        if not date_str or not isinstance(date_str, str):
            return None
        
        date_str = date_str.strip()
        
        # Try Arabic month name format (e.g., "23 فبراير 2026")
        arabic_pattern = r'(\d{1,2})\s+([أ-ي]+)\s+(\d{4})'
        match = re.search(arabic_pattern, date_str)
        if match:
            day, month_name, year = match.groups()
            month = self.ARABIC_MONTHS.get(month_name)
            if month:
                try:
                    return datetime(int(year), month, int(day))
                except ValueError:
                    pass
        
        # Try standard formats
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Manual parsing for formats like 2/2/2026 (fallback)
        try:
            # Try splitting by common separators
            for sep in ['/', '-', '.']:
                if sep in date_str:
                    parts = date_str.split(sep)
                    if len(parts) == 3:
                        # Try DD/MM/YYYY format
                        if len(parts[2]) == 4:  # Year is 4 digits
                            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                            return datetime(year, month, day)
                        # Try YYYY/MM/DD format
                        elif len(parts[0]) == 4:
                            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                            return datetime(year, month, day)
        except (ValueError, IndexError):
            pass
        
        return None
    
    def validate_date(self, date_str: str) -> Tuple[bool, str, Optional[datetime]]:
        """
        Validate a single date
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Tuple of (is_valid, error_message, parsed_date)
        """
        parsed = self.parse_date(date_str)
        
        if parsed is None:
            return False, f"Invalid date format: {date_str}", None
        
        # Check if date is valid
        if not self.is_valid_date(parsed.day, parsed.month, parsed.year):
            return False, f"Invalid date: {date_str} (this date does not exist in the calendar)", None
        
        # Check for reasonable year range (1900-2100)
        if not (1900 <= parsed.year <= 2100):
            return False, f"Year out of reasonable range: {parsed.year}", None
        
        return True, "", parsed
    
    def validate_date_range(
        self,
        start_date_str: str,
        end_date_str: str,
        allow_past_start: bool = False,
        min_duration_days: int = 1,
        max_duration_days: int = 36500  # ~100 years
    ) -> Tuple[bool, str]:
        """
        Validate a date range for lease contracts
        
        Args:
            start_date_str: Start date string
            end_date_str: End date string
            allow_past_start: Allow start date in the past
            min_duration_days: Minimum lease duration in days
            max_duration_days: Maximum lease duration in days
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate start date
        start_valid, start_error, start_date = self.validate_date(start_date_str)
        if not start_valid:
            return False, f"Start date error: {start_error}"
        
        # Validate end date
        end_valid, end_error, end_date = self.validate_date(end_date_str)
        if not end_valid:
            return False, f"End date error: {end_error}"
        
        # Check if start date is in the past (if not allowed)
        if not allow_past_start and start_date < self.reference_date:
            return False, (
                f"Start date {start_date_str} is in the past. "
                f"Lease contracts should start on or after today ({self.reference_date.strftime('%d/%m/%Y')})"
            )
        
        # Check if end date is before start date
        if end_date <= start_date:
            return False, (
                f"End date {end_date_str} must be after start date {start_date_str}. "
                f"The lease period goes backward in time."
            )
        
        # Check duration
        duration = (end_date - start_date).days
        
        if duration < min_duration_days:
            return False, (
                f"Lease duration too short: {duration} days. "
                f"Minimum duration is {min_duration_days} days."
            )
        
        if duration > max_duration_days:
            return False, (
                f"Lease duration too long: {duration} days ({duration // 365} years). "
                f"Maximum duration is {max_duration_days // 365} years."
            )
        
        return True, ""
    
    def extract_and_validate_dates(
        self,
        text: str,
        allow_past_start: bool = False
    ) -> Tuple[bool, str, list]:
        """
        Extract all dates from text and validate them
        
        Args:
            text: Text containing dates
            allow_past_start: Allow start dates in the past
            
        Returns:
            Tuple of (all_valid, error_message, list_of_found_dates)
        """
        # Pattern to find dates in various formats
        date_patterns = [
            r'\d{1,2}[/.-]\d{1,2}[/.-]\d{4}',  # DD/MM/YYYY or D/M/YYYY (1-2 digits)
            r'\d{4}[/.-]\d{1,2}[/.-]\d{1,2}',  # YYYY/MM/DD or YYYY/M/D
            r'\d{1,2}\s+[أ-ي]+\s+\d{4}',     # Arabic: DD Month YYYY
        ]
        
        found_dates = []
        errors = []
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                date_str = match.group()
                is_valid, error, parsed = self.validate_date(date_str)
                
                found_dates.append({
                    'text': date_str,
                    'parsed': parsed,
                    'valid': is_valid,
                    'error': error
                })
                
                if not is_valid:
                    errors.append(f"Invalid date '{date_str}': {error}")
        
        if errors:
            return False, "; ".join(errors), found_dates
        
        # Look for date ranges (start to end patterns)
        range_patterns = [
            r'من\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\s+(?:إلى|حتى|الى)\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})',
            r'from\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\s+to\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})',
            # Also catch patterns with "From X to Y" in header format
            r'From[:\s]+(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\s+to\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})',
            r'Term[:\s]+from\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\s+to\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})',
        ]
        
        for pattern in range_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start_str, end_str = match.groups()
                is_valid, error = self.validate_date_range(
                    start_str, end_str, allow_past_start
                )
                if not is_valid:
                    errors.append(error)
        
        if errors:
            return False, "; ".join(errors), found_dates
        
        return True, "", found_dates
    
    def get_validation_suggestions(self, date_str: str) -> list:
        """
        Get suggestions for fixing an invalid date
        
        Args:
            date_str: Invalid date string
            
        Returns:
            List of suggested corrections
        """
        suggestions = []
        
        # Try to parse the date
        parsed = self.parse_date(date_str)
        if parsed is None:
            suggestions.append("Use format DD/MM/YYYY (e.g., 23/02/2026)")
            return suggestions
        
        # Check for Feb 29 in non-leap year
        if parsed.month == 2 and parsed.day == 29 and not self.is_leap_year(parsed.year):
            suggestions.append(f"February 29 does not exist in {parsed.year} (not a leap year)")
            suggestions.append(f"Try: 28/02/{parsed.year} or 01/03/{parsed.year}")
            # Find next leap year
            next_leap = parsed.year + 1
            while not self.is_leap_year(next_leap) and next_leap < parsed.year + 10:
                next_leap += 1
            if next_leap < parsed.year + 10:
                suggestions.append(f"Or use a leap year: 29/02/{next_leap}")
        
        # Check for invalid day of month
        max_day = calendar.monthrange(parsed.year, parsed.month)[1]
        if parsed.day > max_day:
            suggestions.append(
                f"Day {parsed.day} is invalid for month {parsed.month}/{parsed.year}. "
                f"Maximum day is {max_day}"
            )
            suggestions.append(f"Try: {max_day}/{parsed.month:02d}/{parsed.year}")
        
        # Check if date is too far in past
        if parsed < self.reference_date - timedelta(days=365):
            suggestions.append(
                f"Date is in the past ({parsed.strftime('%d/%m/%Y')}). "
                f"Consider using a current or future date."
            )
        
        return suggestions


# Convenience functions for quick validation

def validate_lease_dates(
    start_date: str,
    end_date: str,
    allow_past_start: bool = False
) -> Tuple[bool, str]:
    """
    Quick validation of lease date range
    
    Args:
        start_date: Start date string
        end_date: End date string
        allow_past_start: Allow start date in the past
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = DateValidator()
    return validator.validate_date_range(start_date, end_date, allow_past_start)


def is_valid_date(date_str: str) -> bool:
    """
    Quick check if a date string is valid
    
    Args:
        date_str: Date string to check
        
    Returns:
        True if date is valid
    """
    validator = DateValidator()
    is_valid, _, _ = validator.validate_date(date_str)
    return is_valid