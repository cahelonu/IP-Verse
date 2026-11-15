"""IPv4/IPv6 Address Application.

A small command-line prototype that shows a computer's current public IPv4
and IPv6 addresses together with ISP, ASN and geolocation details.

Modules
-------
api_client : talks to the public REST APIs and normalises their answers.
report     : combines the API calls into one report dictionary.
formatter  : turns a report into a coloured table or JSON text.
cli        : command-line arguments, program flow and exit codes.
"""

__version__ = "1.0.0"
