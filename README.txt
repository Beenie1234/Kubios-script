#README.txt

Python 3.13.3

1. Run bootstrap.bat as admin

2. Run command ".venv\Scripts\activate.bat"

3. Open Windows Powershell as admin 

4. Run this command to install Chocolatey: "Set-ExecutionPolicy Bypass -Scope Process -Force; `
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
"

5. Verify Install : "choco --version"

6. In the same prompt, now run this command "choco install -y tesseract" and verify installation with "tesseract --version"

