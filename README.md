# IP-Verse: A Python-based IPv4/IPv6 Address Lookup and Network Information Tool

IP-Verse is a Python command-line application designed to retrieve and analyze public IPv4 and IPv6 addresses. Built with aspiring network and security professionals in mind, it provides essential network information in one organized, color-coded report, including ISP details, Autonomous System Numbers (ASN), network ranges, and geolocation data.

This project is developed as part of Project Activity 3: Social Coding for our course IT 26210. This project explores the fundamentals of IP addressing, API integration, modular programming, and collaborative software development.


## Getting Started
### Prerequisites

Make sure you have the following installed:
- Python 3.8 or later
- Git
- Internet connection

### Installation
**1. Clone the repository**
```bash
git clone https://github.com/cahelonu/IP-Verse.git
cd IP-Verse
```

**2. Create a virtual environment**
```bash
python -m venv .venv
```

**3. Activate the virtual environment**
```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Launch IP-Verse**
```bash
python main.py
```

## Command Center: Usage

IP-Verse supports several command-line options depending on what you want to investigate.

| Command | Description |
|---|---|
| `python main.py` | Retrieves your current public IPv4 and IPv6 information |
| `python main.py -4` | Checks IPv4 information only |
| `python main.py -6` | Checks IPv6 information only |
| `python main.py --ip 8.8.8.8` | Looks up a specific IPv4 or IPv6 address |
| `python main.py --json` | Displays results in JSON format |
| `python main.py --save report.json` | Saves the generated report as a JSON file |
| `python main.py --no-color` | Disables terminal colors |

### Exit Codes
| Code | Meaning |
|---|---|
| `0` | Successful execution |
| `1` | No information retrieved or report could not be saved |
| `2` | Invalid input |


### Project Components

| File | Description |
|---|---|
| `main.py` | Application entry point |
| `IP-Verse/api_client.py` | Communicates with ipify and ipapi.co, retrieves network information, and handles API-related errors |
| `IP-Verse/report.py` | Combines API results into a structured report through `build_report()` |
| `IP-Verse/formatter.py` | Generates terminal tables and JSON output |
| `IP-Verse/cli.py` | Processes command-line arguments, displays results, and manages exit codes |
| `tests/test_app.py` | Contains unit tests using mocked API calls for offline testing |


### APIs Behind the Application
IP-Verse integrates two publicly accessible APIs:

| API | Purpose |
|---|---|
| [ipify](https://www.ipify.org/) | Retrieves public IPv4 and IPv6 addresses |
| [ipapi.co](https://ipapi.co/) | Retrieves ISP, ASN, network, and geolocation details |

**Technical note:** The application uses separate ipify endpoints for IPv4 and IPv6 detection. Retrieved addresses are then passed to ipapi.co for additional network information. Both services offer free access without requiring an API key, although ipapi.co applies rate limits to its free tier.


## 🧪 Testing and Quality Assurance

A reliable network utility should be able to handle more than just a successful API response. All external API calls are mocked during testing, allowing the test suite to run without an active internet connection.

To run the tests:

```bash
python -m unittest discover -v
```

## 🛠️ Keeping the Project Alive

IP-Verse is designed with modularity and maintainability in mind. Future contributors can extend the application without having to rewrite its entire structure.

A few pointers for working with the codebase:

- **Adding new network fields:** Update `normalize_details()` in `api_client.py` and `build_rows()` in `formatter.py`.
- **Changing API providers:** Modify `api_client.py` while preserving the expected output keys from `normalize_details()`.
- **Maintaining application stability:** Run the unit tests before submitting changes.
- **Extending functionality:** Follow the existing modular structure when introducing new features.


**Repository:** [github.com/cahelonu/IP-Verse](https://github.com/cahelonu/IP-Verse)