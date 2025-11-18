#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

date_full_range = r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:0?[1-9]|1[0-2])/\d{4}|\d{4})\s*(?:[-–]|to)\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:0?[1-9]|1[0-2])/\d{4}|\d{4}|Present|Current|Now)'

test_strings = [
    "July 2011 to November 2012",
    "April 2010 to June 2011",
    "January 2007 - July 2009",
    "2015 to Present",
    "Company Name\nJuly 2011 to November 2012\nAccountant",
]

for test in test_strings:
    match = re.search(date_full_range, test, re.IGNORECASE)
    if match:
        print(f"✅ MATCH: '{test}' -> '{match.group(0)}'")
    else:
        print(f"❌ NO MATCH: '{test}'")
