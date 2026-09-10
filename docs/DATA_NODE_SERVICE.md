# EasyXT Windows Data Node

Run the data node only on a trusted Windows machine. It serves local DuckDB
research data; it does not provide a trading API.

For Tailscale access, create a random token locally and use the same value in
the trusted Mac client's `.env`:

```powershell
$env:EASYXT_DATA_SERVICE_TOKEN = [guid]::NewGuid().ToString("N")
.\deploy\start_data_node_windows.ps1 -HostAddress "100.79.82.1" -Token $env:EASYXT_DATA_SERVICE_TOKEN
```

The service rejects non-localhost startup without a token. Clients send it as
`Authorization: Bearer <token>` through `EASYXT_DATA_SERVICE_TOKEN`.
