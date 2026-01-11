instalacja requirementsow: pip install -r requirements.txt

uruchomienie: uvicorn main:app --reload

Get-ChildItem -Recurse -File -Exclude "*.exe","*.jpg","*.png","*.pyc","*.git*","caly_projekt.txt" | Where-Object { $_.FullName -notmatch "venv|__pycache__|node_modules|.git" } | ForEach-Object { Add-Content -Path "caly_projekt.txt" -Value "`n====================`nPLIK: $($_.Name)`n===================="; Get-Content $_.FullName | Add-Content -Path "caly_projekt.txt" }
