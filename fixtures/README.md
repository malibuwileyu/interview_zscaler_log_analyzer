# Fixtures (Zscaler-style CSV)

These CSVs are designed to work with the current backend parser/anomaly logic:

- Required headers: `datetime,clientip,url,action,sentbytes,app_risk_score`
- Timestamp format: `YYYY-MM-DD HH:MM:SS` (optionally with `.ffffff`)
- Anomaly rules:
  - `app_risk_score >= 4` => "High risk app"
  - `sentbytes > 5000000` => "Large data outbound"

Upload any of these files in the UI; each contains multiple rows that will be flagged as anomalies.


