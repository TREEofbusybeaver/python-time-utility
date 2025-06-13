# Desktop Time Utility

A minimalist, transparent, always-on-top desktop widget for Windows that provides a clock, stopwatch, and countdown timer. Built with Python and PyQt6.

<!-- 
    **ACTION REQUIRED:** Create a short screen recording or screenshot of your app in action!
    1.  Use a tool like ScreenToGif (free) or ShareX to record a GIF of you using the different modes.
    2.  Upload this GIF to your GitHub repository by dragging and dropping it into the issue comment box or file browser.
    3.  Copy the link to the uploaded GIF and replace the placeholder below. A visual makes a huge difference!
-->
![App Screenshot/GIF](placeholder.gif)

---

## Features

-   **Multiple Modes:** Easily switch between three essential modes:
    -   **Clock:** A clean, modern digital clock.
    -   **Stopwatch:** Measures elapsed time with millisecond precision.
    -   **Countdown Timer:** Set a duration and get a notification when time is up.
-   **Always-On-Top:** The widget floats above all other windows so you can always keep an eye on the time.
-   **Transparent & Frameless:** A clean, unobtrusive design that blends with your desktop.
-   **Fully Draggable:** Click and drag anywhere on the widget to move it around your screen.
-   **Persistent Location:** Remembers its last position on your screen when you restart it.
-   **System Tray Control:** Access all features and quit the application cleanly via a system tray icon.

## Installation

There are two ways to use this application.

### Option 1: The Easy Way (For Users)

<!-- 
    **ACTION REQUIRED:** You need to create a "Release" on GitHub and upload your .exe file.
    1.  On your GitHub repo page, click "Releases" on the right-hand side.
    2.  Click "Draft a new release".
    3.  Give it a tag version, like "v1.0".
    4.  Give it a title, like "Version 1.0".
    5.  Drag and drop the `TimeUtility.exe` file (from your `dist` folder) into the "Attach binaries" box.
    6.  Click "Publish release".
    Now, the link below will work!
-->

1.  Go to the [**Releases**](https://github.com/YourUsername/your-repo-name/releases) page of this repository.
2.  Download the `TimeUtility.exe` file from the latest release.
3.  Place it anywhere on your computer and double-click to run!

### Option 2: From Source (For Developers)

If you want to run the application from the source code:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YourUsername/your-repo-name.git
    cd your-repo-name
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python time_utility.py
    ```

<!-- 
    **ACTION REQUIRED:** You need to create the `requirements.txt` file. In your command prompt (with the virtual environment active), run this command in your project folder:
    `pip freeze > requirements.txt`
    This will list all the necessary packages (like PyQt6) in a file.
-->

## How to Use

-   **Move:** Left-click and drag the widget to position it.
-   **Access Menu:** Right-click anywhere on the widget to open the context menu.
-   **Switch Modes:** From the context menu, select `Switch Mode` to choose between `Clock`, `Stopwatch`, or `Timer`.
-   **Control Modes:** The context menu will show relevant controls (`Start`/`Pause`, `Reset`, `Set Duration...`) for the active mode.
-   **Quit:** Right-click and select `Quit`, or use the system tray icon menu.

## Technologies Used

-   **Python 3**
-   **PyQt6** for the GUI framework.
-   **PyInstaller** for packaging the application into a standalone executable.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

<!-- 
    **ACTION REQUIRED:** Create a file named `LICENSE` (no extension) in your project folder and paste the standard MIT License text into it. You can find the text here: https://opensource.org/licenses/MIT
-->