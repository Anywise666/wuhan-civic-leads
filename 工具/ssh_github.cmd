@echo off
"C:\Windows\System32\OpenSSH\ssh.exe" -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=%TEMP%\kh_win %*
