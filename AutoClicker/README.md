# Click Assist

A small Windows auto-clicker with a desktop UI, global hotkeys, fixed-position clicking, and an emergency stop.

## Requirements

- Windows 10 or later
- Python 3 with Tkinter available

## Install and run

1. Install Python from [python.org](https://www.python.org/downloads/) if it is not already installed. Ensure the Python launcher (`py`) is available.
2. Open PowerShell in the project folder and install the dependency:

   ```powershell
   py -m pip install -r requirements.txt
   ```

3. Start the app by double-clicking `start_click_assist.bat`, or run:

   ```powershell
   py autoclicker.py
   ```

To get the project from GitHub, choose **Code > Download ZIP** and extract it, or clone the repository:

```powershell
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
```

Replace `OWNER/REPOSITORY` with the GitHub repository address.

## Publish to GitHub

1. Create an empty **public** repository on GitHub. Do not initialize it with a README, license, or `.gitignore`, since this project already has those files.
2. Install [Git for Windows](https://git-scm.com/download/win), then open PowerShell in this project folder and run:

   ```powershell
   git init
   git add .
   git status --short
   ```

   Review the listed files before continuing. The entire local `scripts` folder is ignored and should not appear.
3. Commit and push the project, replacing `OWNER/REPOSITORY` with your GitHub account and repository name:

   ```powershell
   git commit -m "Share Click Assist"
   git branch -M main
   git remote add origin https://github.com/OWNER/REPOSITORY.git
   git push -u origin main
   ```

## Controls

- `F6`: start or pause clicking
- `F7`: stop immediately
- Choose `Find Growtopia` before starting; clicks are sent only while that exact Growtopia window handle is active
- Enable `Background clicks` to keep the worker running and send clicks to Growtopia while another window is focused
- `Capture cursor`: stores the current mouse position for fixed-position clicking
- Enter a name and choose `Pick and add`, then left-click the target on screen to save its location
- Choose `Saved spots in order` to click each saved location repeatedly in sequence
- Select a saved spot and choose `Repick location` to left-click a replacement location without losing its other settings
- Select a saved spot and choose `Edit settings` to change its name, coordinates, delay before clicking, or click duration
- The spot table shows coordinates, delay, and click duration in separate columns; use its scrollbar for longer sequences, or double-click a row to edit it
- Choose `Open large editor` below the spot list for a larger window to review, repick, edit, or remove spots
- Selecting a spot shows a click-through marker at its screen location; the marker follows the active target while the sequence runs
- Use `Show crosshair while running` to toggle that marker on or off; changing the setting takes effect immediately
- The edit dialog also supports click duration, which holds the mouse button down for the specified number of seconds
- A spot delay replaces the normal interval for that spot; the first click with no delay happens immediately
- Optional `Timing variation` adds a random extra delay from 0 up to the configured milliseconds value for testing or accessibility workflows
- Choose a script from the `SAVED SCRIPTS` dropdown and select `Load` to restore its settings and click spots
- Select `Save` to update the selected script, or `Save as...` to create another named script
- Select a saved spot and choose `Remove selected` to delete it

## Saved scripts and privacy

Saved click scripts are stored as JSON files in the local `scripts` folder. These files contain screen coordinates and click sequences that are specific to your display and setup, so the repository ignores the entire `scripts` folder by default. Your local profiles are preserved on your computer and are not included when you publish or update the project. Create new scripts in the app after installing it.

## Usage

Use auto-clicking only where it is permitted. Some applications and games prohibit automation.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
