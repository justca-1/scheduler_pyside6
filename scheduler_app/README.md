# CCNHS Scheduler App

A desktop application for managing school schedules, staff workloads, and conflict detection.

## Project Structure

*   **main.py**: The entry point of the application.
*   **src/**: Source code directory.
    *   **core/**: Backend logic (Database & Scheduling Engine).
    *   **ui/**: Frontend logic (Windows, Dialogs, Navigation).
    *   **assets/**: Stylesheets and resources.
*   **data/**: Stores the local SQLite database (`scheduler.db`).

## Prerequisites

*   Python 3.10+
*   PyQt6

## Installation

1.  Create a virtual environment:
    ```bash
    python -m venv .venv
    ```
2.  Activate the environment:
    *   Windows: `.venv\Scripts\activate`
    *   Mac/Linux: `source .venv/bin/activate`
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

Run the application from the root directory:
```bash
python main.py
```
