import pytest
from datetime import datetime, timezone
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.moodle_rss_service import get_moodle_events
import requests_mock

def test_moodle_rss_parsing(requests_mock):
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Moodle Calendar</title>
    <item>
      <title>Devoir de Math</title>
      <link>https://moodle.univ.ca/mod/assign/view.php?id=123</link>
      <pubDate>Mon, 01 Jan 2030 14:00:00 GMT</pubDate>
      <description>Devoir à rendre</description>
    </item>
  </channel>
</rss>
"""
    moodle_url = "https://moodle.univ.ca/calendar/export.php?test"
    requests_mock.get(moodle_url, text=rss_xml)

    events = get_moodle_events(moodle_url, days=3650) # Allow past dates if any, or future up to 10y
    
    assert len(events) == 1
    assert events[0]["title"] == "Devoir de Math"
    assert "2030-01-01" in events[0]["start"]
    assert events[0]["description"] == "Devoir à rendre"
    assert "Moodle" in events[0]["accounts"]

def test_moodle_ical_parsing(requests_mock):
    ical_data = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Moodle Pty Ltd//NONSGML Moodle Version 4.0//EN
BEGIN:VEVENT
UID:12345@moodle.univ.ca
SUMMARY:Examen Physique
DESCRIPTION:Examen final
DTSTART:20300102T090000Z
DTEND:20300102T120000Z
LOCATION:Salle 101
URL:https://moodle.univ.ca/mod/quiz/view.php?id=456
END:VEVENT
END:VCALENDAR
"""
    moodle_url = "https://moodle.univ.ca/calendar/export_execute.php"
    requests_mock.get(moodle_url, text=ical_data)

    events = get_moodle_events(moodle_url, days=3650)
    
    assert len(events) == 1
    assert events[0]["title"] == "Examen Physique"
    assert "2030-01-02T09:00:00+00:00" == events[0]["start"]
    assert "2030-01-02T12:00:00+00:00" == events[0]["end"]
    assert events[0]["location"] == "Salle 101"
    assert events[0]["source"] == "moodle"
